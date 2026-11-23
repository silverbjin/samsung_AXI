#!/usr/bin/env bash
# SmartDish / SAMSUNGAXI S5 RGB-D 2Hz: GitHub-managed WSL2 final acceptance.
# Only bootstrap sources from the exact source SHA verified in real Gazebo CI.
# Does not bypass the existing NO_GOAL preflight or human TTY approval.
set -Eeuo pipefail

SOURCE_SHA='655677571aa907f0624640c3b71cc8edc43a1f53'
REPO='silverbjin/samsung_AXI'
WRAPPER='scripts/samsungaxi_wsl2_gui_acceptance_once.sh'

if [[ "$#" -eq 1 ]] && [[ "$1" == '--self-test' ]]; then
  [[ "$SOURCE_SHA" =~ ^[a-f0-9]{40}$ ]] || exit 2
  [[ "$WRAPPER" == 'scripts/samsungaxi_wsl2_gui_acceptance_once.sh' ]] || exit 2
  echo "S5_RGBD2_RELEASE_BOOTSTRAP_SELF_TEST_PASS_NO_GOAL SOURCE_SHA=$SOURCE_SHA"
  exit 0
fi
if (( $# != 0 )); then
  echo 'S5_RGBD2_BLOCKED_INVALID_ARGS (usage: bash script.sh [--self-test])' >&2
  exit 2
fi
if [[ ! -t 0 ]]; then
  echo 'S5_RGBD2_BLOCKED_REQUIRES_INTERACTIVE_TTY_NO_GOAL' >&2
  exit 2
fi

INNER="$(mktemp --suffix=.sh)"
trap 'rm -f "$INNER"' EXIT
curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 \
  "https://raw.githubusercontent.com/$REPO/$SOURCE_SHA/$WRAPPER" \
  -o "$INNER"
bash -n "$INNER"
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" bash "$INNER" --self-test
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" bash "$INNER" --s5-live --preflight-only

printf '%s\n' 'S5_RGBD2_PREFLIGHT_PASS_NO_GOAL. Starting actual Gazebo/RViz GUI.'
printf '%s\n' 'Inspect route/table safety. Only then type YES-S5-LIVE-GOALS when prompted.'
printf '%s\n' 'After delivery, return and STOP evidence, press Ctrl+C to save the diagnostic ZIP.'
SAMSUNG_AXI_GUI_PIN="$SOURCE_SHA" bash "$INNER" \
  --s5-live --perf-rgbd2 --approve-goals
