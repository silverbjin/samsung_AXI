#!/usr/bin/env bash
# SmartDish GUI acceptance: pinned WSL2, Gazebo + RViz, NO GOAL/NO MAPPING.
set -Eeuo pipefail
PIN="${SAMSUNG_AXI_GUI_PIN:-f39dc1757588b9f7cde1a56f73659f629c57e703}"
[[ "$PIN" =~ ^[a-f0-9]{40}$ ]] || { echo BLOCKED_INVALID_SOURCE_PIN; exit 2; }
if [[ "$*" == "--self-test" ]]; then echo SAMSUNGAXI_GUI_STATIC_PASS_NO_GOAL; exit 0; fi
S5_MODE=0; INSTALL=0; S5_APPROVED=0; PREFLIGHT=0; PERF_MODE=none
for arg in "$@"; do
  case "$arg" in
    --install-deps) INSTALL=1 ;;
    --s5-live) S5_MODE=1 ;;
    --approve-goals) S5_APPROVED=1 ;;
    --preflight-only) PREFLIGHT=1 ;;
    --perf-baseline) PERF_MODE=baseline ;;
    --perf-rgbd2) PERF_MODE=rgbd2 ;;
    *) echo "BLOCKED_INVALID_ARG=$arg" >&2; exit 2 ;;
  esac
done
if (( S5_MODE )); then
  [[ -n "${SAMSUNG_AXI_GUI_PIN:-}" ]] || {
    echo 'S5_BLOCKED_REQUIRES_EXPLICIT_PIN_AND_APPROVE_GOALS'; exit 2;
  }
  if (( PREFLIGHT )); then
    (( S5_APPROVED == 0 )) || { echo 'S5_BLOCKED_PREFLIGHT_MUST_BE_NO_GOAL'; exit 2; }
  else
    (( S5_APPROVED == 1 )) || {
      echo 'S5_BLOCKED_REQUIRES_EXPLICIT_PIN_AND_APPROVE_GOALS'; exit 2;
    }
  fi
elif (( S5_APPROVED || PREFLIGHT )) || [[ "$PERF_MODE" != none ]]; then
  echo 'S5_BLOCKED_LIVE_FLAG_REQUIRED'; exit 2
fi
if (( PREFLIGHT )) && [[ "$PERF_MODE" != none ]]; then
  echo 'S5_PERF_BLOCKED_PROFILE_WITH_NO_GOAL_PREFLIGHT'; exit 2
fi
if (( S5_MODE )); then
  # No auto-optimization. Profile and candidate sensor rate are explicit.
  export SAMSUNGAXI_S5_PERF_MODE="$PERF_MODE"
fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$HOME/samsungaxi_gui_evidence"
mkdir -p "$OUT"
TMP="$(mktemp -d -p "$OUT" .gui-XXXXXXXX)"
ZIP="$OUT/samsungaxi_gui_$STAMP-$$.zip"
RUN="$TMP/run.log"
RC=99; CHILD=''; PROBER=''; PERF_PID=''
export ROS_DOMAIN_ID=58 GZ_PARTITION="samsungaxi_gui_$$"
WORKSPACE="$HOME/samsung_AXI"
finish() {
  local original=$?
  trap - EXIT INT TERM
  if [[ -n "$PROBER" ]]; then kill "$PROBER" 2>/dev/null || :; wait "$PROBER" 2>/dev/null || :; fi
  # Preserve one CSV+summary per live profile; stop only the child we started.
  if [[ -n "$PERF_PID" ]]; then
    kill -INT "$PERF_PID" 2>/dev/null || :
    for _ in $(seq 1 12); do
      kill -0 "$PERF_PID" 2>/dev/null || break
      sleep 0.25
    done
    if kill -0 "$PERF_PID" 2>/dev/null; then kill -TERM "$PERF_PID" 2>/dev/null || :; fi
    wait "$PERF_PID" 2>/dev/null || :
  fi
  if [[ -n "$CHILD" ]] && kill -0 "$CHILD" 2>/dev/null; then
    kill -INT -- "-$CHILD" 2>/dev/null || :
    sleep 2
    kill -TERM -- "-$CHILD" 2>/dev/null || :
    wait "$CHILD" 2>/dev/null || :
  fi
  # The first failure marker is more useful than a later shutdown warning.
  sleep 0.15
  local first phase run_id owner_sha authorized sent
  first="$(grep -Eo 'S5_BLOCKED_[A-Z0-9_]+|RESTAURANT_OWNER_BLOCKED_[A-Z0-9_]+|BLOCKED_[A-Z0-9_]+' "$RUN" | head -n 1 || :)"
  [[ -n "$first" ]] || { if [[ "$RC" == 0 || "$RC" == 130 || "$RC" == 143 ]]; then first=NONE; else first=OWNER_NONZERO_EXIT; fi; }
  phase=NONE
  if [[ "$first" != NONE ]]; then
    if [[ "$first" == S5_BLOCKED_* || "$first" == RESTAURANT_OWNER_BLOCKED_* || "$first" == BLOCKED_* ]]; then
      phase=OWNER_PRELAUNCH
    else
      phase=OWNER_RUNTIME
    fi
  fi
  run_id="${SAMSUNGAXI_S5_RUN_ID:-NOT_SET}"
  [[ "$run_id" =~ ^[A-Za-z0-9_-]+$ ]] || run_id=INVALID
  owner_sha="$(sed -n 's/^RESTAURANT_OWNER_PINNED_SHA=//p' "$RUN" | head -n 1 || :)"
  [[ -n "$owner_sha" ]] || owner_sha=NOT_RUN
  authorized=FALSE
  grep -q '^S5_OWNER_GOALS_AUTHORIZED' "$RUN" && authorized=TRUE
  sent=UNKNOWN
  if grep -q '^S3_NAV02_REAL_GOAL_ACCEPTED=' "$RUN"; then
    sent=TRUE
  elif (( PREFLIGHT )) || [[ "$phase" == OWNER_PRELAUNCH ]]; then
    sent=FALSE
  fi
  {
    echo "PIN=$PIN"
    echo "PUBLIC_SOURCE_SHA=$PIN"
    echo "OWNER_SOURCE_SHA=$owner_sha"
    echo "S5_RUN_ID=$run_id"
    echo "FIRST_FAILED_PHASE=$phase"
    echo "FIRST_FAILED_MARKER=$first"
    echo "RUN_RC=$RC"
    echo "SHELL_RC=$original"
    echo "GOAL_AUTHORIZED=$authorized"
    echo "GOAL_SENT=$sent"
    echo "DIAGNOSTIC_ZIP=$ZIP"
    echo "S5_PERF_MODE=$PERF_MODE"
    if [[ -s "$TMP/s5_perf_summary.json" ]]; then
      echo 'S5_PERF_PROFILE_PRESENT=TRUE'
    elif [[ "$PERF_MODE" != none ]]; then
      echo 'S5_PERF_PROFILE_PRESENT=FALSE'
    fi
    echo 'WSL2_GUI_ACCEPTED=NOT_RUN_UNTIL_HUMAN_VISUAL_CHECK'
    if (( PREFLIGHT )) && [[ "$RC" == 0 ]]; then
      echo VERDICT=PREFLIGHT_PASS_NO_GOAL
    elif [[ "$RC" == 0 || "$RC" == 130 || "$RC" == 143 ]]; then
      echo VERDICT=GUI_VISUAL_REVIEW_REQUIRED
    else
      echo VERDICT=HOLD
    fi
  } > "$TMP/status.txt"

  grep -Ei 'BLOCKED|S5_|RESTAURANT_OWNER_|fail|error|warn|timeout|exception|fatal|renderer|rviz|gazebo' "$RUN" | tail -n 150 > "$TMP/error_clues.txt" || :
  tail -n 350 "$RUN" > "$TMP/log_tail.txt" || :
  if (( S5_MODE )) && [[ -n "${SAMSUNGAXI_S5_RUN_ID:-}" ]]; then
    for source in "$WORKSPACE/generated/s5/$SAMSUNGAXI_S5_RUN_ID/s5_live_evidence.json" "$WORKSPACE/generated/s5/$SAMSUNGAXI_S5_RUN_ID/ci-s3-summary.txt"; do
      if [[ -s "$source" ]]; then
        cp "$source" "$TMP/$(basename "$source")" || :
      fi
    done
  fi
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
if (( S5_MODE )); then
  # On a real live run, reject non-interactive stdin before ROS/apt/network.
  if (( ! PREFLIGHT )) && [[ ! -t 0 ]]; then
    echo 'S5_BLOCKED_OWNER_TERMINAL_REQUIRED'; RC=2; exit 2
  fi
  SRC=""
  if (( PREFLIGHT )); then
    # CI can provide its checkout. Deployed pinned one-shot downloads the exact
    # same three source files; neither path executes ROS or Goal.
    if [[ -n "${SAMSUNGAXI_S5_PREFLIGHT_REPO:-}" ]]; then
      SRC="$SAMSUNGAXI_S5_PREFLIGHT_REPO"
    else
      SRC="$TMP/preflight_source"
      mkdir -p "$SRC/scripts"
      for file in s5_run_id_contract.sh owner_wsl2_once.sh restaurant_demo.sh; do
        if ! curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 \
          "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/$file" \
          -o "$SRC/scripts/$file"; then
          echo 'S5_BLOCKED_PREFLIGHT_SOURCE_FETCH'; RC=3; exit 3
        fi
      done
    fi
    for file in s5_run_id_contract.sh owner_wsl2_once.sh restaurant_demo.sh; do
      if [[ ! -f "$SRC/scripts/$file" ]] || ! bash -n "$SRC/scripts/$file"; then
        echo 'S5_BLOCKED_PREFLIGHT_SOURCE_INVALID'; RC=3; exit 3
      fi
    done
    source "$SRC/scripts/s5_run_id_contract.sh"
  else
    LIB="$TMP/s5_run_id_contract.sh"
    if ! curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 \
      "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/s5_run_id_contract.sh" \
      -o "$LIB"; then
      echo 'S5_BLOCKED_RUN_ID_CONTRACT_FETCH'; RC=3; exit 3
    fi
    if ! bash -n "$LIB"; then
      echo 'S5_BLOCKED_RUN_ID_CONTRACT_SYNTAX'; RC=3; exit 3
    fi
    source "$LIB"
  fi
  if ! s5_run_id_commit; then RC=2; exit 2; fi
  if (( PREFLIGHT )); then
    if bash "$SRC/scripts/owner_wsl2_once.sh" live NORMAL \
        --preflight-only --ref "$PIN" --workspace "$SRC"; then
      RC=0
      echo 'S5_OWNER_PREFLIGHT_PASS_NO_GOAL'
      exit 0
    else
      RC=$?
      exit "$RC"
    fi
  fi
fi
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
if (( S5_MODE )) && [[ "$PERF_MODE" != none ]]; then
  PERF_SCRIPT="$TMP/s5_perf_profile.py"
  if ! curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/s5_perf_profile.py" \
    -o "$PERF_SCRIPT"; then
    echo 'S5_PERF_BLOCKED_PROFILE_SCRIPT_FETCH'; RC=3; exit 3
  fi
  if ! python3 - "$PERF_SCRIPT" <<'PY'
import ast,sys
ast.parse(open(sys.argv[1],encoding='utf-8').read())
PY
  then
    echo 'S5_PERF_BLOCKED_PROFILE_SCRIPT_SYNTAX'; RC=3; exit 3
  fi
  echo "S5_PERF_PROFILE_MODE=$PERF_MODE"
  python3 "$PERF_SCRIPT" \
    --run-log "$RUN" \
    --csv-out "$TMP/s5_perf_timeline.csv" \
    --summary-out "$TMP/s5_perf_summary.json" \
    --mode "$PERF_MODE" >"$TMP/s5_perf_collector.log" 2>&1 &
  PERF_PID=$!
fi
OWNER_ARGS=(navigation NORMAL --ref "$PIN" --workspace "$WORKSPACE")
if (( S5_MODE )); then
  OWNER_ARGS=(live NORMAL --ref "$PIN" --workspace "$WORKSPACE" --goals-approved)
  echo 'S5_LIVE_MODE=ARMED_WITH_EXPLICIT_CLI_BUT_NO_GOAL_UNTIL_TERMINAL_CONFIRMATION'
else
  echo START_GUI_NO_GOAL
fi
if (( ! INSTALL )); then OWNER_ARGS+=(--no-install-deps); fi
# Bash non-interactive background jobs otherwise receive stdin=/dev/null.
# Pass the live operator TTY explicitly: no goal without a real typed YES.
if (( S5_MODE )); then
  [[ -t 0 ]] || { echo 'S5_BLOCKED_OWNER_TERMINAL_REQUIRED'; RC=2; exit 2; }
  setsid bash "$OWNER" "${OWNER_ARGS[@]}" </dev/tty &
else
  setsid bash "$OWNER" "${OWNER_ARGS[@]}" &
fi
CHILD=$!
set +e
wait "$CHILD"; RC=$?
set -e
exit "$RC"
