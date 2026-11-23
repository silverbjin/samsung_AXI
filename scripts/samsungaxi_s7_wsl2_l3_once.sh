#!/usr/bin/env bash
# S7 startup-dishes acceptance with a SINGLE immutable SHA for entry and ROS.
set -Eeuo pipefail
SOURCE_SHA="$(printenv SAMSUNGAXI_S7_SOURCE_SHA 2>/dev/null || true)"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo S7_BLOCKED_MISSING_IMMUTABLE_SHA_NO_GOAL >&2; exit 2; }
WRAPPER='scripts/samsungaxi_wsl2_gui_acceptance_once.sh'
if [[ $# == 1 && "$1" == '--self-test' ]]; then
  echo "S7_OWNER_SELF_TEST_PASS_NO_GOAL SOURCE_SHA=$SOURCE_SHA"
  exit 0
fi
[[ $# == 0 ]] || { echo S7_BLOCKED_UNKNOWN_ARGUMENTS_NO_GOAL >&2; exit 2; }
[[ -t 0 ]] || { echo S7_BLOCKED_REAL_TTY_REQUIRED_NO_GOAL >&2; exit 2; }
for c in curl bash; do command -v "$c" >/dev/null || { echo "S7_BLOCKED_MISSING_CMD=$c" >&2; exit 2; }; done
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$SOURCE_SHA/$WRAPPER" \
  -o "$WORK/s7_owner.sh"
test -s "$WORK/s7_owner.sh"
bash -n "$WORK/s7_owner.sh"
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" bash "$WORK/s7_owner.sh" --self-test
echo "S7_EXACT_RUNTIME_AND_ENTRY_SHA=$SOURCE_SHA"
export SAMSUNGAXI_S7_SCENARIO=stacked SAMSUNGAXI_S6_VISION=1
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" bash "$WORK/s7_owner.sh" --s5-live --preflight-only
echo S7_OWNER_PREFLIGHT_PASS_NO_GOAL
echo 'S7: dishes are loaded at WORLD START; Vision subscribes only after arrival.'
echo 'The live Goal requires an independent human TTY YES-S5-LIVE-GOALS.'
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" bash "$WORK/s7_owner.sh" \
  --s5-live --perf-rgbd2 --approve-goals
