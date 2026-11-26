#!/usr/bin/env bash
# R03 production evidence only. Deploy the exact validated SHA, not branch tip.
set -Eeuo pipefail
MODE="${1:---gui}"
[[ $# -le 1 && ( "$MODE" == --gui || "$MODE" == --headless ) ]] || { echo A14_R03_INVALID_MODE; exit 2; }
PIN="$(printenv SMARTDISH_A14_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo A14_R03_PIN_REQUIRED; exit 2; }
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || { echo A14_R03_REAL_WSL2_REQUIRED; exit 2; }
case "$HOME" in /mnt/*) echo A14_R03_EXT4_REQUIRED; exit 2;; esac
URL=https://github.com/silverbjin/samsung_AXI.git
BRANCH=feat/smartdish-a14-physics-evidence
TARGET="$(mktemp -d "$HOME/samsung_AXI_A14_R03_${PIN:0:7}_XXXXXX")"
echo "A14_R03_OWNER_DIR=$TARGET"
# No downloaded helper from moving HEAD. Fetch only the requested object.
git init -q "$TARGET"
git -C "$TARGET" remote add origin "$URL"
timeout --signal=INT --kill-after=5s 120s git -C "$TARGET" fetch --no-tags --depth=1 origin "$PIN"
git -C "$TARGET" switch -q -c "$BRANCH" "$PIN"
[[ "$(git -C "$TARGET" rev-parse HEAD)" == "$PIN" ]] || { echo A14_R03_SHA_MISMATCH; exit 2; }
echo "A14_R03_PIN_PASS=$PIN"
cd "$TARGET"
exec bash scripts/a14_r03_owner.sh "$MODE"
