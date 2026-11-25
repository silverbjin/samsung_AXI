#!/usr/bin/env bash
# SmartDish B A-13: offline read-only import + candidate review only.
# The actual A-13 archive is never pulled from GitHub or re-generated.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
EXPECTED_ARCHIVE_SHA="bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e"
ARCHIVE=""; SHA=""; WORKDIR=""; MODE=review
usage() {
  printf '%s\n' \
    'Usage: bash scripts/smartdish_b_real_data_one_shot.sh --sha <40-character-git-sha> [--archive <existing-a13-tar.gz>] [--workdir <new-absolute-path>] [--mode review]' \
    'If --archive is omitted, search A_TRAY generated runs and Downloads for an archive with the exact approved SHA256.'
}
while (($#)); do
  case "$1" in
    --archive|--sha|--workdir|--mode)
      [[ $# -ge 2 && -n "$2" ]] || { echo B_ARGUMENT_VALUE_MISSING >&2; exit 2; }
      case "$1" in
        --archive) ARCHIVE="$2";;
        --sha) SHA="$2";;
        --workdir) WORKDIR="$2";;
        --mode) MODE="$2";;
      esac
      shift 2;;
    --help|-h) usage; exit 0;;
    *) echo "B_INVALID_ARGS $1" >&2; usage >&2; exit 2;;
  esac
done
[[ "$MODE" == review ]] || { echo B_AUTO_APPROVAL_FORBIDDEN >&2; exit 2; }
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo B_GIT_SHA_REQUIRED >&2; exit 2; }
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$SHA" ]] || { echo B_CODE_SHA_PIN_MISMATCH >&2; exit 2; }
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || {
  echo B_DIRTY_TRACKED_WORKTREE >&2; exit 2;
}

hash_archive() { sha256sum -- "$1" | cut -d ' ' -f1; }

if [[ -n "$ARCHIVE" ]]; then
  # Human-readable error for documentation placeholder copied verbatim.
  case "$ARCHIVE" in
    /path/to/*|/path/to|/path/to/*/*)
      echo B_A13_ARCHIVE_PLACEHOLDER_PATH >&2; exit 3;;
  esac
  [[ -f "$ARCHIVE" ]] || { echo "B_A13_ARCHIVE_FILE_MISSING path=$ARCHIVE" >&2; exit 3; }
  [[ -r "$ARCHIVE" ]] || { echo "B_A13_ARCHIVE_NOT_READABLE path=$ARCHIVE" >&2; exit 3; }
else
  # Scan only known, bounded local roots. Never download or execute archives.
  # All candidates must match the pinned SHA, not merely match a filename.
  SEARCH_ROOTS=("$HOME/samsung_AXI_A_TRAY/generated/smartdish_tray" "$HOME/Downloads")
  MISMATCH_COUNT=0; FIRST_MISMATCH=""
  for root in /mnt/c/Users/*/Downloads; do
    [[ -d "$root" ]] && SEARCH_ROOTS+=("$root")
  done
  for root in "${SEARCH_ROOTS[@]}"; do
    [[ -d "$root" ]] || continue
    while IFS= read -r -d '' candidate; do
      [[ -r "$candidate" ]] || continue
      current_hash="$(hash_archive "$candidate")" || continue
      if [[ "$current_hash" == "$EXPECTED_ARCHIVE_SHA" ]]; then
        ARCHIVE="$candidate"
        break
      fi
      MISMATCH_COUNT=$((MISMATCH_COUNT + 1))
      [[ -n "$FIRST_MISMATCH" ]] || FIRST_MISMATCH="$candidate observed_sha256=$current_hash"
    done < <(find "$root" -maxdepth 6 -type f \
      -name 'smartdish_a_tray_evidence*.gz' -print0 2>/dev/null)
    [[ -n "$ARCHIVE" ]] && break
  done
  if [[ -z "$ARCHIVE" ]]; then
    if ((MISMATCH_COUNT)); then
      echo "B10_ARCHIVE_SHA_MISMATCH candidates=$MISMATCH_COUNT expected_sha256=$EXPECTED_ARCHIVE_SHA first=$FIRST_MISMATCH" >&2
      echo B_EVIDENCE_IMPORT_BLOCKED >&2
      exit 2
    fi
    echo "B_A13_ORIGINAL_ARCHIVE_NOT_FOUND expected_sha256=$EXPECTED_ARCHIVE_SHA" >&2
    echo 'Copy the previously accepted A-13 TAR into ~/samsung_AXI_A_TRAY/generated/smartdish_tray or pass --archive /actual/file/path.' >&2
    echo B_EVIDENCE_IMPORT_BLOCKED >&2
    exit 3
  fi
  echo "B_A13_ARCHIVE_AUTO_DISCOVERED path=$ARCHIVE"
fi

ACTUAL_ARCHIVE_SHA="$(hash_archive "$ARCHIVE")" || {
  echo B_A13_ARCHIVE_READ_FAILED >&2; exit 3;
}
if [[ "$ACTUAL_ARCHIVE_SHA" != "$EXPECTED_ARCHIVE_SHA" ]]; then
  echo "B10_ARCHIVE_SHA_MISMATCH expected=$EXPECTED_ARCHIVE_SHA observed=$ACTUAL_ARCHIVE_SHA" >&2
  echo B_EVIDENCE_IMPORT_BLOCKED >&2
  exit 2
fi
echo "SMARTDISH_B_A13_ARCHIVE_SHA_PASS sha256=$ACTUAL_ARCHIVE_SHA"
if [[ -z "$WORKDIR" ]]; then
  WORKDIR="$ROOT/ai/data/private/b_a13_review_$(date -u +%Y%m%dT%H%M%SZ)_$$"
fi
[[ "$WORKDIR" == /* ]] || { echo B_WORKDIR_MUST_BE_ABSOLUTE >&2; exit 2; }
[[ ! -e "$WORKDIR" ]] || { echo B_NO_OVERWRITE_WORKDIR >&2; exit 2; }
[[ "$WORKDIR" != "$ROOT" && "$WORKDIR" != "$ARCHIVE" ]] || {
  echo B_WORKDIR_UNSAFE >&2; exit 2;
}
if [[ "$WORKDIR" == "$ROOT/"* && "$WORKDIR" != "$ROOT/ai/data/private/"* ]]; then
  echo B_WORKDIR_MUST_BE_IN_PRIVATE_DATA_AREA >&2; exit 2;
fi
# No ROS/Gazebo execution; source archive is read-only.
mkdir -p "$WORKDIR"
python3 "$ROOT/ai/scripts/import_a13_evidence.py" \
  --archive "$ARCHIVE" --output "$WORKDIR/raw"
python3 "$ROOT/ai/scripts/extract_a13_candidates.py" \
  --raw "$WORKDIR/raw" --out "$WORKDIR/review" \
  --archive-sha256 "$ACTUAL_ARCHIVE_SHA"
printf 'SMARTDISH_B_LABEL_REVIEW_PACKAGE_READY %s\n' "$WORKDIR/review/review.html"
printf 'B_LABEL_APPROVAL_PENDING approved=0\n'
