#!/usr/bin/env bash
# A14 WSL2 immutable-SHA bootstrap; clean fast-forward only, original files safe.
set -Eeuo pipefail
MODE=--gui
if [[ $# -gt 0 ]]; then MODE="$1"; shift; fi
[[ $# -eq 0 && ( "$MODE" == --gui || "$MODE" == --headless ) ]] ||
  { echo A14_INVALID_MODE; exit 2; }
PIN="$(printenv SMARTDISH_A14_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo A14_SHA_PIN_REQUIRED; exit 2; }
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] &&
  grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease ||
  { echo A14_BOOTSTRAP_WSL2_REQUIRED; exit 2; }
[[ -t 0 ]] || { echo A14_INTERACTIVE_TERMINAL_REQUIRED; exit 2; }
TARGET="$HOME/samsung_AXI_A14_PHYSICS"
case "$TARGET" in /mnt/*) echo A14_EXT4_REQUIRED; exit 2;; esac
REPO=https://github.com/silverbjin/samsung_AXI.git
BRANCH=feat/smartdish-a14-physics-evidence
if [[ -e "$TARGET" && ! -d "$TARGET/.git" ]]; then
  echo A14_NON_GIT_WORKSPACE_PRESERVED; exit 2
fi
if [[ ! -d "$TARGET/.git" ]]; then
  git clone -q --single-branch --branch "$BRANCH" "$REPO" "$TARGET" ||
    { echo A14_CLONE_FAILED; exit 2; }
else
  [[ "$(git -C "$TARGET" remote get-url origin)" == "$REPO" ]] ||
    { echo A14_ORIGIN_MISMATCH; exit 2; }
  [[ "$(git -C "$TARGET" branch --show-current)" == "$BRANCH" ]] ||
    { echo A14_BRANCH_MISMATCH; exit 2; }
  [[ -z "$(git -C "$TARGET" status --porcelain --untracked-files=no)" ]] ||
    { echo A14_TRACKED_EDITS_PRESERVED; exit 2; }
  git -C "$TARGET" fetch -q origin "$BRANCH"
  git -C "$TARGET" merge --ff-only FETCH_HEAD ||
    { echo A14_BRANCH_DIVERGENCE_PRESERVED; exit 2; }
fi
HEAD="$(git -C "$TARGET" rev-parse HEAD)"
[[ "$HEAD" == "$PIN" ]] || { echo "A14_EXEC_SHA_DRIFT requested=$PIN got=$HEAD"; exit 2; }
echo "A14_BOOTSTRAP_PIN_OK=$HEAD"
cd "$TARGET"
exec bash scripts/smartdish_a14_one_shot.sh "$MODE"
