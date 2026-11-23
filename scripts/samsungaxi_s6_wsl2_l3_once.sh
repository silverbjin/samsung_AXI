#!/usr/bin/env bash
# HISTORICAL S6 INITIAL RUNNER - retired after G09 and exact-SHA WSL2 G11 PASS.
# Fail closed: NEVER start an old ROS/Gazebo runtime via this obsolete path.
set -Eeuo pipefail
if [[ $# -eq 1 && "${1:-}" == '--self-test' ]]; then
  echo 'S6_LEGACY_ENTRY_RETIRED_SELF_TEST_PASS_NO_GOAL'
  exit 0
fi
echo 'S6_LEGACY_ENTRY_RETIRED_NO_GOAL' >&2
echo 'Use the one officially supported G09 entry documented at:' >&2
echo 'https://github.com/silverbjin/samsung_AXI/blob/main/docs/S6_OFFICIAL_OWNER_ENTRY_KO.md' >&2
exit 2
