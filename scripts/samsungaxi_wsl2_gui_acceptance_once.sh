#!/usr/bin/env bash
# SmartDish GUI acceptance: pinned WSL2, Gazebo + RViz, NO GOAL/NO MAPPING.
set -Eeuo pipefail
PIN="${SAMSUNG_AXI_GUI_PIN:-f39dc1757588b9f7cde1a56f73659f629c57e703}"
[[ "$PIN" =~ ^[a-f0-9]{40}$ ]] || { echo BLOCKED_INVALID_SOURCE_PIN; exit 2; }
if [[ "$*" == "--self-test" ]]; then echo SAMSUNGAXI_GUI_STATIC_PASS_NO_GOAL; exit 0; fi
if [[ "$*" != "" && "$*" != "--install-deps" ]]; then echo 'Usage: bash script.sh [--install-deps|--self-test]'; exit 2; fi
INSTALL=0; [[ "$*" == "--install-deps" ]] && INSTALL=1
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HOME/samsungaxi_gui_evidence"
mkdir -p "$OUT"
TMP="$(mktemp -d -p "$OUT" .gui-XXXXXXXX)"
ZIP="$OUT/samsungaxi_gui_$STAMP-$$.zip"
RUN="$TMP/run.log"
RC=99; CHILD=''; PROBER=''
export ROS_DOMAIN_ID=58 GZ_PARTITION="samsungaxi_gui_$$"
WORKSPACE="$HOME/samsung_AXI"
finish() {
  local original=$?
  trap - EXIT INT TERM
  if [[ -n "$PROBER" ]]; then kill "$PROBER" 2>/dev/null || :; wait "$PROBER" 2>/dev/null || :; fi
  if [[ -n "$CHILD" ]] && kill -0 "$CHILD" 2>/dev/null; then
    kill -INT -- "-$CHILD" 2>/dev/null || :
    sleep 2
    kill -TERM -- "-$CHILD" 2>/dev/null || :
    wait "$CHILD" 2>/dev/null || :
  fi
  {
    echo "PIN=$PIN"
    echo "RUN_RC=$RC SHELL_RC=$original"
    echo 'WSL2_GUI_ACCEPTED=NOT_RUN_UNTIL_HUMAN_VISUAL_CHECK'
    if [[ "$RC" == 0 || "$RC" == 130 || "$RC" == 143 ]]; then
      echo VERDICT=GUI_VISUAL_REVIEW_REQUIRED
    else
      echo VERDICT=HOLD
    fi
  } > "$TMP/status.txt"
  grep -Ei 'fail|error|warn|timeout|exception|fatal|renderer|rviz|gazebo' "$RUN" | tail -n 150 > "$TMP/error_clues.txt" || :
  tail -n 350 "$RUN" > "$TMP/log_tail.txt" || :
  if [[ -d "$WORKSPACE/logs" ]]; then
    find "$WORKSPACE/logs" -maxdepth 1 -type f -mmin -45 | sort | tail -n 8 | while read -r f; do
      echo "==== $f ====" >> "$TMP/owner_tails.txt"
      tail -n 120 "$f" >> "$TMP/owner_tails.txt" 2>/dev/null || :
    done
  fi
  export EVIDENCE_DIR="$TMP" EVIDENCE_ZIP="$ZIP"
  python3 - <<'PY' || :
import os,zipfile,pathlib
p=pathlib.Path(os.environ['EVIDENCE_DIR'])
with zipfile.ZipFile(os.environ['EVIDENCE_ZIP'],'w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(p.iterdir()):
  if f.is_file(): z.write(f,arcname=f.name)
PY
  rm -rf -- "$TMP"
  printf '\nSAMSUNGAXI_DIAGNOSTIC_ZIP=%s\nSAMSUNGAXI_RUN_RC=%s\n' "$ZIP" "$RC"
}
trap finish EXIT
trap 'RC=130; exit 130' INT
trap 'RC=143; exit 143' TERM
exec > >(tee -a "$RUN") 2>&1
{
  date -u
  uname -a
  cat /etc/os-release
  echo "DISPLAY=$DISPLAY WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
  free -h
  df -h "$HOME"
  if command -v glxinfo >/dev/null; then timeout 8 glxinfo -B 2>&1 | grep -E 'OpenGL vendor|OpenGL renderer|Accelerated|Device:' || :; fi
  if command -v nvidia-smi >/dev/null; then timeout 6 nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || :; fi
} > "$TMP/environment.txt" 2>&1 || :
if ! grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease; then echo BLOCKED_NOT_WSL2; RC=2; exit 2; fi
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then echo BLOCKED_ROS_JAZZY; RC=2; exit 2; fi
if [[ -z "$DISPLAY" && -z "$WAYLAND_DISPLAY" ]]; then echo BLOCKED_WSLG; RC=2; exit 2; fi
for cmd in curl git python3 setsid timeout; do command -v "$cmd" >/dev/null || { echo "BLOCKED_TOOL=$cmd"; RC=2; exit 2; }; done
# WSLg GPU: prefer previously verified D3D12 NVIDIA only if the live
# renderer reports accelerated=yes. Process-scoped; no global system edits.
if command -v glxinfo >/dev/null 2>&1; then
  GPU_PROBE="$(env -u LIBGL_ALWAYS_SOFTWARE GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA timeout 10 glxinfo -B 2>&1)" || GPU_PROBE=""
  printf '%s\n' "$GPU_PROBE" | grep -E 'OpenGL renderer|Accelerated|Device:' > "$TMP/gpu_probe.txt" || :
  if [[ "$GPU_PROBE" == *D3D12* && "$GPU_PROBE" == *NVIDIA* && "$GPU_PROBE" == *"Accelerated: yes"* ]]; then
    unset LIBGL_ALWAYS_SOFTWARE
    export GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
    echo 'SAMSUNGAXI_WSLG_GPU_ROUTE=D3D12_NVIDIA_ACCELERATED'
  else
    echo 'SAMSUNGAXI_WSLG_GPU_ROUTE=UNVERIFIED_NO_AUTO_OVERRIDE'
  fi
else
  echo 'SAMSUNGAXI_WSLG_GPU_ROUTE=GLXINFO_UNAVAILABLE'
fi
OWNER="$TMP/owner_wsl2_once.sh"
URL="https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/owner_wsl2_once.sh"
if ! curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 "$URL" -o "$OWNER"; then echo BLOCKED_DOWNLOAD; RC=3; exit 3; fi
bash -n "$OWNER"
bash "$OWNER" world --self-test --ref "$PIN"
(
  sleep 40
  set +u
  source /opt/ros/jazzy/setup.bash
  if [[ -r "$WORKSPACE/install/setup.bash" ]]; then source "$WORKSPACE/install/setup.bash"; fi
  set -u
  # Real Gazebo Stats in the SAME live GUI session; no fabricated RTF.
  timeout 28s gz topic -e -t /world/restaurant/stats 2>/dev/null |
    awk '/real_time_factor:/ {print $2; if(++n>=100)exit}' > "$TMP/rtf_samples.txt" || :
  export RTF_SAMPLE_PATH="$TMP/rtf_samples.txt" RTF_REPORT_PATH="$TMP/rtf_report.txt"
  python3 - <<'PY'
import os,statistics
from pathlib import Path
samples=[]
for line in Path(os.environ['RTF_SAMPLE_PATH']).read_text().splitlines():
    try:
        v=float(line)
        if 0 <= v <= 10:samples.append(v)
    except ValueError:pass
if len(samples)<5:
    result='RTF_MEASUREMENT=INSUFFICIENT_SAMPLES'
else:
    ordered=sorted(samples)
    result=('RTF_SAMPLE_COUNT=%d\nRTF_MEDIAN=%.4f\nRTF_P10=%.4f\nRTF_AT_LEAST_90PCT=%s'
            %(len(samples),statistics.median(samples),
              ordered[int((len(samples)-1)*.1)],
              str(statistics.median(samples)>=.9).upper()))
Path(os.environ['RTF_REPORT_PATH']).write_text(result+'\n')
PY
  for cmd in 'ros2 node list' 'ros2 topic list -t' 'ros2 action list' 'ros2 topic echo /scan --once' 'ros2 topic echo /odom --once' 'ros2 lifecycle get /amcl' 'ros2 lifecycle get /collision_monitor'; do
    echo "== $cmd ==" >> "$TMP/ros_diagnostics.txt"
    timeout 8 bash -c "$cmd" >> "$TMP/ros_diagnostics.txt" 2>&1 || echo PROBE_NONZERO >> "$TMP/ros_diagnostics.txt"
  done
) & PROBER=$!
echo START_GUI_NO_GOAL
if ((INSTALL)); then
  setsid bash "$OWNER" navigation NORMAL --ref "$PIN" --workspace "$WORKSPACE" &
else
  setsid bash "$OWNER" navigation NORMAL --ref "$PIN" --workspace "$WORKSPACE" --no-install-deps &
fi
CHILD=$!
set +e
wait "$CHILD"; RC=$?
set -e
exit "$RC"
