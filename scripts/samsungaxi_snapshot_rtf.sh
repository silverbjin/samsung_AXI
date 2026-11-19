#!/usr/bin/env bash
# Optional, read-only RTF evidence while Gazebo is still running. No goals.
set -Eeuo pipefail
ROOT="${SAMSUNG_AXI_ROOT:-$HOME/samsung_AXI}"
mkdir -p "$ROOT/logs/evidence"
export GZ_PARTITION="${GZ_PARTITION:-restaurant_mvp}"
OUT="$ROOT/logs/evidence/gazebo_stats_$(date -u +%Y%m%dT%H%M%SZ).txt"
command -v gz >/dev/null || { echo 'SAMSUNGAXI_STATS_BLOCKED=gz_not_installed' >&2; exit 2; }
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
set +e
timeout 7s gz topic -e -t /world/restaurant/stats >"$TMP" 2>&1
RC="$?"
set -e
if ! grep -q 'real_time_factor:' "$TMP"; then
  echo 'SAMSUNGAXI_STATS_NOT_CAPTURED: check Gazebo running and GZ_PARTITION' >&2
  sed -n '1,12p' "$TMP" >&2
  exit 2
fi
{
  echo 'SAMSUNGAXI_GAZEBO_RTF_OBSERVATION_NOT_ACCEPTANCE=1'
  date -u '+UTC=%Y-%m-%dT%H:%M:%SZ'
  echo "GZ_PARTITION=$GZ_PARTITION"
  grep 'real_time_factor:' "$TMP" | head -n 20 || true
  echo "RECORDING_COMMAND_EXIT=$RC (124 can mean the 7s sample window ended)"
} >"$OUT"
echo "SAMSUNGAXI_RTF_STATS_FILE=$OUT"
