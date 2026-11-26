#!/usr/bin/env bash
set -Eeuo pipefail
PIN="$(printenv SMARTDISH_A15_SOURCE_SHA || :)"
MODE="${1:---gui}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && ( "$MODE" == --gui || "$MODE" == --headless ) ]] || exit 2
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || { echo A15_WSL_REQUIRED; exit 2; }
URL=https://github.com/silverbjin/samsung_AXI.git
helper="$(mktemp)";trap 'rm -f -- "$helper"' EXIT
curl -fsSL --max-time 30 "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_platform_bootstrap.sh" -o "$helper"
source "$helper";rm -f -- "$helper";trap - EXIT
TARGET="$(smartdish_new_workspace "$PIN" A15 "$HOME")"
smartdish_pin_checkout "$URL" "$PIN" feat/smartdish-a14-physics-evidence "$TARGET"
echo "REQUESTED_SHA=$PIN"
echo "ACTUAL_SOURCE_SHA=$(git -C "$TARGET" rev-parse HEAD)"
echo "OWNER_WORKSPACE=$TARGET"
cd "$TARGET"
exec bash scripts/a15_pilot_batch.sh "$PIN" "$TARGET/generated_a15" "$MODE"
