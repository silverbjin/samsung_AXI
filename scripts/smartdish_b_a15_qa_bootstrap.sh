#!/usr/bin/env bash
# Immutable, isolated WSL2/CI checkout of B-QA03. Not sourced into parent shell.
set -Eeuo pipefail
if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
  echo 'Usage: SMARTDISH_B_QA03_SOURCE_SHA=<40hex> SMARTDISH_B_QA03_OWNER_ARCHIVE=/abs/a15_pilot_evidence.tar.gz bash smartdish_b_a15_qa_bootstrap.sh'
  echo 'Optional CI only: SMARTDISH_QA03_CLONE_URL=/path/to/test/repo SMARTDISH_QA03_WORK_ROOT=/private/root'
  exit 0
fi
PIN="${SMARTDISH_B_QA03_SOURCE_SHA:-}"
OWNER="${SMARTDISH_B_QA03_OWNER_ARCHIVE:-}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo B_A15_QA03_PIN_REQUIRED >&2; exit 2; }
[[ "$OWNER" = /* ]] || { echo B_A15_QA03_OWNER_ABSOLUTE_PATH_REQUIRED >&2; exit 2; }
[[ -f "$OWNER" && -f "$OWNER.sha256" && ! -L "$OWNER" && ! -L "$OWNER.sha256" ]] || { echo B_A15_QA03_OWNER_AND_SHA256_MISSING >&2; exit 2; }
ROOT="${SMARTDISH_QA03_WORK_ROOT:-$HOME}"
mkdir -p -- "$ROOT"
RUN="$ROOT/smartdish_b_qa03_${PIN:0:12}_$(date -u +%Y%m%dT%H%M%SZ)_$$"
[[ ! -e "$RUN" ]] || { echo B_A15_QA03_ISOLATED_RUN_EXISTS >&2; exit 2; }
mkdir -p -- "$RUN"
REPO="$RUN/repo";OUT="$RUN/private_audit"
URL="${SMARTDISH_QA03_CLONE_URL:-https://github.com/silverbjin/samsung_AXI.git}"
git clone --no-checkout --filter=blob:none -- "$URL" "$REPO"
git -C "$REPO" -c safe.directory="$REPO" checkout --detach "$PIN"
[[ "$(git -C "$REPO" -c safe.directory="$REPO" rev-parse HEAD)" == "$PIN" ]] || { echo B_A15_QA03_CHECKOUT_PIN_DRIFT >&2; exit 2; }
echo "B_A15_QA03_ISOLATED_SHA=$PIN"
echo "B_A15_QA03_ISOLATED_WORKSPACE=$RUN"
SMARTDISH_B_QA03_SOURCE_SHA="$PIN" bash "$REPO/scripts/smartdish_b_a15_qa_one_shot.sh" \
    --owner "$OWNER" --sha256-file "$OWNER.sha256" --out-dir "$OUT"
