#!/usr/bin/env bash
# SmartDish E pinned WSL2 bootstrap: dedicated directory, no reset/force.
set -Eeuo pipefail
PIN="$(printenv SMARTDISH_E_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo SMARTDISH_E_BOOTSTRAP_PIN_REQUIRED; exit 2; }
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] || { echo SMARTDISH_E_BOOTSTRAP_WSL2_REQUIRED; exit 2; }
[[ -t 0 && -r /dev/tty && -w /dev/tty ]] || { echo SMARTDISH_E_BOOTSTRAP_TTY_REQUIRED; exit 2; }
ROOT="$HOME/samsung_AXI_E"
ORIGIN=https://github.com/silverbjin/samsung_AXI.git
if [[ ! -e "$ROOT" ]]; then
  git clone --no-checkout "$ORIGIN" "$ROOT"
  git -C "$ROOT" fetch --quiet origin "$PIN"
  git -C "$ROOT" checkout --quiet --detach "$PIN"
else
  [[ -d "$ROOT/.git" ]] || { echo SMARTDISH_E_WORKDIR_IS_NOT_GIT; exit 2; }
  [[ "$(git -C "$ROOT" remote get-url origin)" == "$ORIGIN" ]] ||
    { echo SMARTDISH_E_ORIGIN_MISMATCH; exit 2; }
  [[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] ||
    { echo SMARTDISH_E_LOCAL_TRACKED_CHANGES_BLOCKED; exit 2; }
  [[ "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] ||
    { echo SMARTDISH_E_EXISTING_CHECKOUT_SHA_MISMATCH_NO_RESET; exit 2; }
fi
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] ||
  { echo SMARTDISH_E_PIN_CHECK_FAILED; exit 2; }
echo "SMARTDISH_E_BOOTSTRAP_PIN_OK=$PIN"
export SMARTDISH_E_EXPECTED_SHA="$PIN"
exec bash "$ROOT/scripts/smartdish_e_wsl2_one_shot.sh" --gui
