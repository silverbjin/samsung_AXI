#!/usr/bin/env bash
# R03 standalone bootstrap and tested exact-pin checkout function.
a14_pin_checkout() { smartdish_pin_checkout "$@"; }

main() {
  set -Eeuo pipefail
  MODE="${1:---gui}"
  [[ $# -eq 2 && ( "$MODE" == --gui || "$MODE" == --headless ) ]] || { echo A14_R03_INVALID_MODE; exit 2; }
  RAW="$(realpath "$2")"
  [[ -f "$RAW" ]] || { echo DBG_REUSED_RAW_MISSING; exit 2; }
  PIN="$(printenv SMARTDISH_A14_SOURCE_SHA || :)"
  [[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo A14_R03_PIN_REQUIRED; exit 2; }
  [[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || { echo A14_R03_REAL_WSL2_REQUIRED; exit 2; }
  case "$HOME" in /mnt/*) echo A14_R03_EXT4_REQUIRED; exit 2;; esac
  URL=https://github.com/silverbjin/samsung_AXI.git
  BRANCH=feat/smartdish-a14-physics-evidence
  helper="$(mktemp)"
  trap 'rm -f -- "$helper"' EXIT
  curl -fsSL --max-time 30 "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_platform_bootstrap.sh" -o "$helper"
  source "$helper"
  rm -f -- "$helper"
  trap - EXIT
  TARGET="$(smartdish_new_workspace "$PIN" A14_R03_DBG "$HOME")"
  echo "A14_R03_OWNER_DIR=$TARGET"
  # No moving HEAD or merge; same checkout function exercised by L0.
  a14_pin_checkout "$URL" "$PIN" "$BRANCH" "$TARGET" || { echo A14_R03_PIN_CHECKOUT_FAILED; exit 2; }
  echo "A14_R03_PIN_PASS=$PIN"
  cd "$TARGET"
  exec bash scripts/a14_r03_dbg_owner.sh "$MODE" "$RAW"
  
}
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
else
  source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/smartdish_platform_bootstrap.sh"
fi
