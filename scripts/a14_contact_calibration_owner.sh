#!/usr/bin/env bash
# A14-07: only independent positive Contact controls; no tray scenario replay.
set -Eeuo pipefail
MODE=--gui
if [[ $# -gt 0 ]]; then MODE="$1"; shift; fi
[[ $# -eq 0 && ( "$MODE" == --gui || "$MODE" == --headless ) ]] || {
  echo A14_CAL_INVALID_MODE; exit 2;
}
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PIN="$(printenv SMARTDISH_A14_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo A14_CAL_PIN_REQUIRED; exit 2; }
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] || {
  echo A14_CAL_SOURCE_SHA_MISMATCH; exit 2;
}
[[ "$(git -C "$ROOT" branch --show-current)" == "feat/smartdish-a14-physics-evidence" ]] || {
  echo A14_CAL_BRANCH_MISMATCH; exit 2;
}
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || {
  echo A14_CAL_UNCOMMITTED_SOURCE_EDITS; exit 2;
}
case "$ROOT" in /mnt/*) echo A14_CAL_EXT4_REQUIRED; exit 2;; esac
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || {
  echo A14_CAL_REAL_WSL2_REQUIRED; exit 2;
}
[[ -r /opt/ros/jazzy/setup.bash ]] || { echo A14_CAL_ROS_JAZZY_MISSING; exit 2; }
for item in gz ros2 python3 timeout sha256sum; do
  command -v "$item" >/dev/null || { echo "A14_CAL_COMMAND_MISSING=$item"; exit 2; }
done
set +u
source /opt/ros/jazzy/setup.bash
set -u
ros2 pkg prefix ros_gz_bridge >/dev/null
ros2 interface show ros_gz_interfaces/msg/Contacts >/dev/null
cd "$ROOT"
if [[ "$MODE" == --gui ]]; then
  [[ -n "$(printenv DISPLAY || :)" ]] || { echo A14_CAL_XCB_DISPLAY_REQUIRED; exit 2; }
  export SMARTDISH_A_TRAY_GUI_PROFILE="$(printenv SMARTDISH_A_TRAY_GUI_PROFILE || echo xcb)"
  # The preflight is the only GUI check; the calibration runs headless.
  timeout --signal=INT --kill-after=8s 65s \
    python3 -u scripts/smartdish_a_tray_gui_preflight.py \
      --sha "$PIN" --profile "$SMARTDISH_A_TRAY_GUI_PROFILE" || {
        echo A14_CAL_WSLG_GUI_PREFLIGHT_HOLD
        exit 2
      }
fi
echo "A14_CAL_IMMUTABLE_SOURCE_SHA_PASS=$PIN"
echo "A14_CAL_INDEPENDENT_POSITIVE_CONTROL_ONLY=true"
set +e
timeout --signal=INT --kill-after=10s 115s \
  python3 -u scripts/a14_contact_calibration.py --sha "$PIN" \
    --max-wall-seconds 95
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
  echo "A14_CAL_POSITIVE_CONTROL_HOLD exit=$RC"
  echo "A14_CAL_NOTE=attach calibration evidence TAR from generated/smartdish_a14/contact_calibration_*"
  exit 2
fi
echo A14_CAL_POSITIVE_CONTROL_PASS_PRODUCTION_GT_STILL_HOLD
