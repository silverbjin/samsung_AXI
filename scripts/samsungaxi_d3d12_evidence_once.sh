#!/usr/bin/env bash
# Wrap the already verified D3D12 world runner; capture a compact ZIP on exit.
# It changes no Gazebo physics, no source repo, no host settings, no ROS goal.
set -Eeuo pipefail
MODE="${1:-world}"
if [[ "$MODE" != world && "$MODE" != doctor ]]; then
  echo 'Usage: bash samsungaxi_d3d12_evidence_once.sh [world|doctor]' >&2
  exit 2
fi
ROOT="${SAMSUNG_AXI_ROOT:-$HOME/samsung_AXI}"
CORE="${SAMSUNG_AXI_CORE_SCRIPT:-$ROOT/scripts/samsungaxi_d3d12_world_once.sh}"
BUNDLER="${SAMSUNG_AXI_BUNDLER_SCRIPT:-$ROOT/scripts/samsungaxi_evidence_bundle.py}"
# A reviewed one-shot may be downloaded into /tmp while the WSL2 project tree
# remains pinned to its previously accepted commit. Fetch only immutable SHAs.
TMP_DEP=""
if [[ ! -r "$CORE" || ! -r "$BUNDLER" ]]; then
  REF="${SAMSUNG_AXI_EVIDENCE_REF:-}"
  if [[ ! "$REF" =~ ^[0-9a-f]{40}$ ]]; then
    echo 'BLOCKED: missing dependency; set SAMSUNG_AXI_EVIDENCE_REF to reviewed 40-char SHA' >&2
    exit 2
  fi
  command -v curl >/dev/null || { echo 'BLOCKED: curl missing' >&2; exit 2; }
  TMP_DEP="$(mktemp -d)"
  if [[ ! -r "$CORE" ]]; then
    curl -fLsS --retry 3 --connect-timeout 10 \
      "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$REF/scripts/samsungaxi_d3d12_world_once.sh" \
      -o "$TMP_DEP/core.sh" || { rm -rf -- "$TMP_DEP"; exit 2; }
    CORE="$TMP_DEP/core.sh"
  fi
  if [[ ! -r "$BUNDLER" ]]; then
    curl -fLsS --retry 3 --connect-timeout 10 \
      "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$REF/scripts/samsungaxi_evidence_bundle.py" \
      -o "$TMP_DEP/bundler.py" || { rm -rf -- "$TMP_DEP"; exit 2; }
    BUNDLER="$TMP_DEP/bundler.py"
  fi
fi
[[ -r "$CORE" ]] || { echo "BLOCKED: missing D3D12 runner $CORE" >&2; exit 2; }
[[ -r "$BUNDLER" ]] || { echo "BLOCKED: missing evidence bundler $BUNDLER" >&2; exit 2; }
if [[ "$MODE" == doctor ]]; then
  set +e
  bash "$CORE" doctor
  rc="$?"
  set -e
  [[ -z "$TMP_DEP" ]] || rm -rf -- "$TMP_DEP"
  exit "$rc"
fi
mkdir -p "$ROOT/logs/evidence"
START="$(date -u +%s)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SESSION="$ROOT/logs/evidence/d3d12_world_$STAMP.log"
ZIP="$ROOT/logs/evidence/samsungaxi_d3d12_world_$STAMP.zip"
# Release stdout/exit status, including Ctrl+C, while guaranteeing evidence.
collect() {
  local rc="$?"
  trap - EXIT INT TERM
  if ! python3 "$BUNDLER" --root "$ROOT" --session-log "$SESSION" --since-unix "$START" --output "$ZIP"; then
    echo 'SAMSUNGAXI_EVIDENCE_COLLECTION_FAILED_RAW_LOGS_PRESERVED' >&2
  fi
  [[ -z "$TMP_DEP" ]] || rm -rf -- "$TMP_DEP"
  echo "SAMSUNGAXI_RUN_EXIT_CODE=$rc"
  exit "$rc"
}
trap collect EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# Original proven world launch and its Ctrl+C lifecycle are unchanged.
set +e
bash "$CORE" world 2>&1 | tee "$SESSION"
RC="${PIPESTATUS[0]}"
set -e
exit "$RC"
