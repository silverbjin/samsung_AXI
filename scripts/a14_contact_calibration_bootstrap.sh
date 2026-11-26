#!/usr/bin/env bash
# Immutable A14-07 WSL2 calibration bootstrap, separate from A13/A14 L3 batches.
set -Eeuo pipefail
MODE=--gui
if [[ $# -gt 0 ]]; then MODE="$1"; shift; fi
[[ $# -eq 0 && ( "$MODE" == --gui || "$MODE" == --headless ) ]] || {
  echo A14_CAL_BOOTSTRAP_INVALID_MODE; exit 2;
}
PIN="$(printenv SMARTDISH_A14_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo A14_CAL_BOOTSTRAP_SHA_PIN_REQUIRED; exit 2; }
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] || {
  echo A14_CAL_BOOTSTRAP_WSL2_REQUIRED; exit 2;
}
TARGET="$HOME/samsung_AXI_A14_PHYSICS"
BRANCH=feat/smartdish-a14-physics-evidence
URL=https://github.com/silverbjin/samsung_AXI.git
case "$TARGET" in /mnt/*) echo A14_CAL_BOOTSTRAP_EXT4_REQUIRED; exit 2;; esac
if [[ -e "$TARGET" && ! -d "$TARGET/.git" ]]; then
  echo A14_CAL_BOOTSTRAP_USER_FILES_PRESERVED; exit 2;
fi
if [[ ! -d "$TARGET/.git" ]]; then
  git clone -q --single-branch --branch "$BRANCH" "$URL" "$TARGET"
else
  [[ "$(git -C "$TARGET" remote get-url origin)" == "$URL" ]] || {
    echo A14_CAL_BOOTSTRAP_ORIGIN_MISMATCH; exit 2;
  }
  [[ "$(git -C "$TARGET" branch --show-current)" == "$BRANCH" ]] || {
    echo A14_CAL_BOOTSTRAP_BRANCH_MISMATCH; exit 2;
  }
  [[ -z "$(git -C "$TARGET" status --porcelain --untracked-files=no)" ]] || {
    echo A14_CAL_BOOTSTRAP_LOCAL_CHANGES_PRESERVED; exit 2;
  }
  git -C "$TARGET" fetch -q origin "$BRANCH"
  git -C "$TARGET" merge --ff-only FETCH_HEAD
fi
HEAD="$(git -C "$TARGET" rev-parse HEAD)"
[[ "$HEAD" == "$PIN" ]] || {
  echo "A14_CAL_BOOTSTRAP_SHA_DRIFT requested=$PIN actual=$HEAD"; exit 2;
}
echo "A14_CAL_BOOTSTRAP_SHA_PASS=$PIN"
cd "$TARGET"
exec bash scripts/a14_contact_calibration_owner.sh "$MODE"
