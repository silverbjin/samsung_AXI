#!/usr/bin/env bash
# B-10/B-11 A13 evidence read-only offline import. No ROS, no Goals, no automatic label approval.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
ARCHIVE=""; SHA=""; WORKDIR=""; MODE=review
while (($#)); do
  case "$1" in
    --archive) ARCHIVE="${2:?}"; shift 2;;
    --sha) SHA="${2:?}"; shift 2;;
    --workdir) WORKDIR="${2:?}"; shift 2;;
    --mode) MODE="${2:?}"; shift 2;;
    *) echo "B_INVALID_ARGS $1" >&2; exit 2;;
  esac
done
[[ "$MODE" == review ]] || { echo B_AUTO_APPROVAL_FORBIDDEN >&2; exit 2; }
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo B_GIT_SHA_REQUIRED >&2; exit 2; }
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$SHA" ]] || { echo B_CODE_SHA_PIN_MISMATCH >&2; exit 2; }
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || { echo B_DIRTY_TRACKED_WORKTREE >&2; exit 2; }
[[ -n "$ARCHIVE" && -f "$ARCHIVE" && -r "$ARCHIVE" ]] || {
  echo A13_SOURCE_REFERENCE_CONFIRMED
  echo A13_ARCHIVE_BYTES_NOT_AVAILABLE
  echo B_EVIDENCE_IMPORT_BLOCKED
  exit 3
}
if [[ -z "$WORKDIR" ]]; then
  WORKDIR="$ROOT/ai/data/private/b_a13_review_$(date -u +%Y%m%dT%H%M%SZ)_$$"
fi
[[ "$WORKDIR" == /* ]] || { echo B_WORKDIR_MUST_BE_ABSOLUTE >&2; exit 2; }
[[ ! -e "$WORKDIR" ]] || { echo B_NO_OVERWRITE_WORKDIR >&2; exit 2; }
[[ "$WORKDIR" != "$ROOT" && "$WORKDIR" != "$ARCHIVE" ]] || exit 2
# workspace is a dedicated root, never mutate source archive, main dataset, or an existing directory
mkdir -p "$WORKDIR"
python3 "$ROOT/ai/scripts/import_a13_evidence.py" --archive "$ARCHIVE" --output "$WORKDIR/raw"
python3 "$ROOT/ai/scripts/extract_a13_candidates.py" --raw "$WORKDIR/raw" \
  --out "$WORKDIR/review" \
  --archive-sha256 bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e
printf 'SMARTDISH_B_LABEL_REVIEW_PACKAGE_READY %s\n' "$WORKDIR/review/review.html"
printf 'B_LABEL_APPROVAL_PENDING approved=0\n'
