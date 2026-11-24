#!/usr/bin/env bash
# A-13 fixed-SHA WSL2 source bootstrap; no Git hard reset/force, no ROS Goals.
set -Eeuo pipefail
MODE=--gui
SCENE_MODE=batch
if [[ $# -gt 0 ]]; then
  case "$1" in
    --gui|--headless) MODE="$1"; shift ;;
    --help|-h)
      echo 'Usage: SMARTDISH_A_TRAY_SOURCE_SHA=<40hex> bash scripts/smartdish_a_tray_bootstrap.sh [--gui|--headless] [demo|single|batch]'
      echo 'Default GUI + batch(4 scenarios); isolated ~/samsung_AXI_A_TRAY directory.'
      exit 0 ;;
  esac
fi
if [[ $# -gt 0 ]]; then SCENE_MODE="$1"; shift; fi
[[ $# -eq 0 ]] || { echo A_TRAY_INVALID_ARGS; exit 2; }
case "$MODE:$SCENE_MODE" in
  --gui:demo|--gui:single|--gui:batch|--headless:demo|--headless:single|--headless:batch) ;;
  *) echo A_TRAY_INVALID_MODE; exit 2 ;;
esac
block() { echo "SMARTDISH_A_TRAY_BOOTSTRAP_BLOCKED: $*" >&2; exit 2; }
[[ -n "$(printenv WSL_DISTRO_NAME)" ]] || block 'WSL2 Ubuntu required.'
grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || block 'WSL2 kernel missing.'
[[ -t 0 ]] || block 'Use an interactive terminal.'
PIN="$(printenv SMARTDISH_A_TRAY_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || block 'Set exact verified SMARTDISH_A_TRAY_SOURCE_SHA.'
for command in git bash; do type "$command" >/dev/null 2>&1 || block "Missing $command"; done
TARGET="$HOME/samsung_AXI_A_TRAY"
case "$TARGET" in /mnt/*) block 'WSL2 ext4 HOME required.';; esac
REPO=https://github.com/silverbjin/samsung_AXI.git
BRANCH=feat/smartdish-a-tray-camera
if [[ -e "$TARGET" && ! -d "$TARGET/.git" ]]; then block 'Non-Git target preserved.'; fi
if [[ ! -d "$TARGET/.git" ]]; then
  git clone -q --single-branch --branch "$BRANCH" "$REPO" "$TARGET" || block 'Clone failed.'
else
  [[ "$(git -C "$TARGET" remote get-url origin)" == "$REPO" ]] || block 'Origin mismatch.'
  [[ "$(git -C "$TARGET" branch --show-current)" == "$BRANCH" ]] || block 'Branch mismatch.'
  [[ -z "$(git -C "$TARGET" status --porcelain --untracked-files=no)" ]] || block 'Tracked edits; preserve first.'
  git -C "$TARGET" fetch -q origin "$BRANCH" || block 'Fetch failed.'
  git -C "$TARGET" merge --ff-only FETCH_HEAD || block 'Diverged branch preserved, no reset.'
fi
GOT="$(git -C "$TARGET" rev-parse HEAD)"
[[ "$GOT" == "$PIN" ]] || block "Source SHA drift: requested=$PIN got=$GOT; no run."
[[ -f "$TARGET/scripts/smartdish_a_tray_one_shot.sh" ]] || block 'Runner missing.'
echo "SMARTDISH_A_TRAY_BOOTSTRAP_PIN_OK=$GOT"
cd "$TARGET"
exec bash scripts/smartdish_a_tray_one_shot.sh "$SCENE_MODE" "$MODE"
