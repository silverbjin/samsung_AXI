#!/usr/bin/env bash
# A-13 L3/L2: isolated lab. Default GUI, choose explicit --headless for CI.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TASK=batch
MODE=--gui
if [[ $# -gt 0 ]]; then TASK="$1"; shift; fi
if [[ $# -gt 0 ]]; then MODE="$1"; shift; fi
[[ $# -eq 0 ]] || { echo SMARTDISH_A_TRAY_INVALID_ARGS; exit 2; }
case "$TASK:$MODE" in
 demo:--gui|single:--gui|batch:--gui|smoke:--gui|qualify:--gui|demo:--headless|single:--headless|batch:--headless|smoke:--headless) ;;
 *) echo SMARTDISH_A_TRAY_INVALID_MODE; exit 2 ;;
esac
SHA="$(git -C "$ROOT" rev-parse HEAD)"
PIN="$(printenv SMARTDISH_A_TRAY_SOURCE_SHA || :)"
[[ "$SHA" == "$PIN" ]] || { echo SMARTDISH_A_TRAY_PIN_MISMATCH; exit 2; }
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] ||
  { echo SMARTDISH_A_TRAY_DIRTY_TRACKED_WORKTREE; exit 2; }
case "$ROOT" in /mnt/*) echo SMARTDISH_A_TRAY_NOT_WSL_EXT4; exit 2;; esac
if [[ -z "$(printenv CI || :)" ]]; then
  [[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] || { echo SMARTDISH_A_TRAY_WSL2_REQUIRED; exit 2; }
  grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || exit 2
fi
if [[ "$MODE" == --gui && -z "$(printenv DISPLAY || :)$(printenv WAYLAND_DISPLAY || :)" ]]; then
  echo SMARTDISH_A_TRAY_GUI_DISPLAY_MISSING; exit 2
fi
[[ -r /opt/ros/jazzy/setup.bash ]] || { echo SMARTDISH_A_TRAY_ROS_JAZZY_MISSING; exit 2; }
for cmd in git gz ros2 colcon python3 tar; do
  command -v "$cmd" >/dev/null || { echo "SMARTDISH_A_TRAY_MISSING_COMMAND=$cmd"; exit 2; }
done
set +u
source /opt/ros/jazzy/setup.bash
set -u
for pkg in ros_gz_bridge ros_gz_sim; do
  ros2 pkg prefix "$pkg" >/dev/null 2>&1 ||
    { echo "SMARTDISH_A_TRAY_ROS_PACKAGE_MISSING=$pkg"; exit 2; }
done
python3 -c 'import PIL; import yaml; import rclpy; import sensor_msgs.msg; import tf2_msgs.msg' ||
  { echo SMARTDISH_A_TRAY_PYTHON_DEPENDENCY_MISSING; exit 2; }
cd "$ROOT"
# This is packaging readiness, NOT existing Nav2 real-run reacceptance.
colcon build --symlink-install --event-handlers console_direct+ \
  --packages-select smartdish_robot >"/tmp/smartdish_a_tray_build_$$.log" 2>&1 ||
  { tail -n 50 "/tmp/smartdish_a_tray_build_$$.log"; echo SMARTDISH_A_TRAY_COLCON_FAILED; exit 2; }
set +u
source "$ROOT/install/setup.bash"
set -u
echo "SMARTDISH_A_TRAY_SOURCE_SHA=$SHA"
echo "SMARTDISH_A_TRAY_MODE=$TASK GUI=$MODE"
echo SMARTDISH_A_TRAY_BUILD_PASS_NO_NAV2_GOAL
if [[ "$TASK" == qualify ]]; then
  [[ "$MODE" == --gui ]] || { echo A13_WSLG_QUALIFY_REQUIRES_GUI; exit 2; }
  GATE="$ROOT/generated/smartdish_tray/qualification_$SHA-$$.json"
  mkdir -p "$(dirname "$GATE")"
  python3 -u scripts/smartdish_a_tray_release_gate.py preflight \
    --sha "$SHA" --root "$ROOT" --manifest "$GATE"
  SMOKE_LOG="$(mktemp "$HOME/smartdish_a_tray_smoke.XXXXXXXX.log")"
  python3 -u scripts/smartdish_a_tray_live.py smoke --expected-sha "$SHA" "$MODE" \
    2>&1 | tee "$SMOKE_LOG"
  SMOKE_TAR="$(sed -n 's/^SMARTDISH_A_TRAY_EVIDENCE_BUNDLE=//p' "$SMOKE_LOG" | tail -1)"
  [[ -n "$SMOKE_TAR" && -s "$SMOKE_TAR" ]] || { echo A13_WSLG_SMOKE_EVIDENCE_MISSING; exit 2; }
  python3 -u scripts/smartdish_a_tray_release_gate.py smoke \
    --sha "$SHA" --manifest "$GATE" --archive "$SMOKE_TAR"
  export SMARTDISH_A_TRAY_GATE_MANIFEST="$GATE"
  BATCH_LOG="$(mktemp "$HOME/smartdish_a_tray_batch.XXXXXXXX.log")"
  python3 -u scripts/smartdish_a_tray_live.py batch --expected-sha "$SHA" "$MODE" \
    2>&1 | tee "$BATCH_LOG"
  BATCH_TAR="$(sed -n 's/^SMARTDISH_A_TRAY_EVIDENCE_BUNDLE=//p' "$BATCH_LOG" | tail -1)"
  [[ -n "$BATCH_TAR" && -s "$BATCH_TAR" ]] || { echo A13_WSLG_BATCH_EVIDENCE_MISSING; exit 2; }
  python3 -u scripts/smartdish_a_tray_release_gate.py finalize \
    --sha "$SHA" --manifest "$GATE" --archive "$BATCH_TAR"
  echo "SMARTDISH_A_TRAY_WSLG_QUALIFICATION_COMPLETE_OWNER_REVIEW_REQUIRED"
else
  exec python3 -u scripts/smartdish_a_tray_live.py "$TASK" --expected-sha "$SHA" "$MODE"
fi
