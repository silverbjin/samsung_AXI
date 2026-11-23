#!/usr/bin/env bash
# S6 WSL2 L3 operator entry: exact real Gazebo L2 SHA, real TTY approval.
set -Eeuo pipefail
SOURCE_SHA='937fbf025cefec01489c40bc5104c39e3d4709be'
REPO='silverbjin/samsung_AXI'
WRAPPER='scripts/samsungaxi_wsl2_gui_acceptance_once.sh'
if [[ $# == 1 && "$1" == '--self-test' ]]; then
  [[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
  echo "S6_L3_RELEASE_SELF_TEST_PASS_NO_GOAL SHA=$SOURCE_SHA"
  exit 0
fi
if (( $# != 0 )); then
  echo S6_L3_BLOCKED_INVALID_ARGUMENTS_NO_GOAL >&2; exit 2
fi
if [[ ! -t 0 ]]; then
  echo S6_L3_BLOCKED_INTERACTIVE_TTY_REQUIRED_NO_GOAL >&2; exit 2
fi
command -v curl >/dev/null || { echo S6_L3_BLOCKED_CURL_MISSING >&2; exit 2; }
ENTRY="$(mktemp --suffix=.sh)"
trap 'rm -f "$ENTRY"' EXIT
curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 \
  "https://raw.githubusercontent.com/$REPO/$SOURCE_SHA/$WRAPPER" -o "$ENTRY"
bash -n "$ENTRY"
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" bash "$ENTRY" --self-test
echo "S6_L3_PINNED_SOURCE=$SOURCE_SHA"
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" SAMSUNGAXI_S6_VISION=1 \
  bash "$ENTRY" --s5-live --preflight-only
echo S6_L3_PREFLIGHT_PASS_NO_GOAL
echo 'Inspect Gazebo/RViz route and table. Type YES-S5-LIVE-GOALS only after visual approval.'
echo 'After TABLE_3 → RGB STACKED → PICKUP_RETURN → STOP, press Ctrl+C for evidence ZIP.'
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" SAMSUNGAXI_S6_VISION=1 \
  bash "$ENTRY" --s5-live --perf-rgbd2 --approve-goals
