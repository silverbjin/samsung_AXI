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
 demo:--gui|single:--gui|batch:--gui|demo:--headless|single:--headless|batch:--headless) ;;
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
exec python3 -u scripts/smartdish_a_tray_live.py "$TASK" --expected-sha "$SHA" "$MODE"
