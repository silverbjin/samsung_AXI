#!/usr/bin/env bash
# SmartDish A-08: WSL2 owner ONE COMMAND clone/update → real three-leg Gazebo.
# No automatic goal approval: operator types on /dev/tty.
set -Eeuo pipefail
usage() {
  cat <<'HELP'
SmartDish A WSL2 one-shot bootstrap
Usage: bash smartdish_a_wsl2_bootstrap.sh [--headless|--gui|--help]
--headless  Default: actual Gazebo/Nav2, no GUI.
--gui       Optional WSLg Gazebo/RViz.
--help      Show help without changing any local files.
Preserves existing edits, rejects wrong origin/divergence, never resets.
Goals need explicit YES-SMARTDISH-A-GOALS input at /dev/tty.
HELP
}
MODE=--headless
if [[ $# -gt 1 ]]; then usage >&2; exit 2; fi
if [[ $# -eq 1 ]]; then MODE="$1"; fi
case "$MODE" in
  --help|-h) usage; exit 0 ;;
  --headless|--gui) ;;
  *) echo "SMARTDISH_A_BOOTSTRAP_INVALID_MODE=$MODE" >&2; usage >&2; exit 2 ;;
esac
block() { echo "SMARTDISH_A_BOOTSTRAP_BLOCKED_NO_GOAL: $*" >&2; exit 2; }
[[ -n "$(printenv WSL_DISTRO_NAME)" ]] || block 'Run in Ubuntu 24.04 WSL2 terminal.'
grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || block 'Not WSL2 kernel.'
[[ -t 0 && -r /dev/tty && -w /dev/tty ]] || block 'Interactive terminal required.'
[[ -d "$HOME" ]] || block 'HOME directory missing.'
case "$HOME" in /mnt/*) block 'Use WSL2 ext4 HOME, not /mnt/c.';; esac
for cmd in git bash; do command -v "$cmd" >/dev/null || block "Missing command: $cmd"; done

REPO='https://github.com/silverbjin/samsung_AXI.git'
BRANCH=feat/smartdish-a-robot
TARGET="$HOME/samsung_AXI_A"
if [[ -e "$TARGET" && ! -d "$TARGET/.git" ]]; then
  block "Target exists and is not a Git checkout: $TARGET (left untouched)."
fi
if [[ ! -d "$TARGET/.git" ]]; then
  echo "SMARTDISH_A_BOOTSTRAP_CLONE=$TARGET"
  git clone -q --single-branch -b "$BRANCH" "$REPO" "$TARGET" ||
    block 'Clone failed. No navigation goal sent.'
else
  origin="$(git -C "$TARGET" remote get-url origin)" || block 'Cannot read origin remote.'
  [[ "$origin" == "$REPO" ]] || block 'Origin mismatch: existing checkout preserved.'
  [[ "$(git -C "$TARGET" branch --show-current)" == "$BRANCH" ]] ||
    block 'Checkout is on another branch: existing checkout preserved.'
  [[ -z "$(git -C "$TARGET" status --porcelain --untracked-files=no)" ]] ||
    block 'Local tracked edits present: commit/stash first.'
  echo "SMARTDISH_A_BOOTSTRAP_FAST_FORWARD=$TARGET"
  git -C "$TARGET" fetch -q origin "$BRANCH" || block 'Git fetch failed.'
  git -C "$TARGET" merge --ff-only FETCH_HEAD || block 'Branches diverged: no reset.'
fi
[[ -f "$TARGET/scripts/smartdish_a_wsl2_one_shot.sh" ]] || block 'Runner not found.'
[[ "$(git -C "$TARGET" branch --show-current)" == "$BRANCH" ]] || block 'Wrong branch.'
SHA="$(git -C "$TARGET" rev-parse HEAD)"
echo "SMARTDISH_A_BOOTSTRAP_SOURCE_SHA=$SHA"
echo "SMARTDISH_A_BOOTSTRAP_MODE=$MODE"
echo 'SMARTDISH_A_BOOTSTRAP_HUMAN_TTY_APPROVAL_REQUIRED'
cd "$TARGET"
exec bash scripts/smartdish_a_wsl2_one_shot.sh "$MODE"
