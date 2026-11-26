#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
PIN="$(printenv SMARTDISH_A18_SOURCE_SHA || :)"
MODE=--gui; PHASE=1
if [[ "${1:-}" == --phase ]]; then PHASE="${2:-}"; shift 2; fi
MODE="${1:---gui}"
[[ "$PHASE" == 1 && $# -le 1 ]] || { echo A18_PHASE2_NOT_RELEASED; exit 2; }
# Bootstrap failures also leave a minimal private diagnostic with sidecar.
DIAG="$(mktemp -d "$HOME/smartdish_a18_boot_XXXXXX")"
finish(){
 local rc=$?;trap - EXIT
 if (( rc != 0 ));then
  printf 'requested_sha=%s\nexit_code=%s\nmode=%s\n' "$PIN" "$rc" "$MODE" > "$DIAG/status.txt"
  (cd "$DIAG"; sha256sum status.txt bootstrap.log > SHA256SUMS; tar -czf a18_bootstrap_diagnostics.tar.gz status.txt bootstrap.log SHA256SUMS; sha256sum a18_bootstrap_diagnostics.tar.gz > a18_bootstrap_diagnostics.tar.gz.sha256)
  echo "A18_BOOTSTRAP_DIAGNOSTICS=$DIAG/a18_bootstrap_diagnostics.tar.gz"
 fi
 exit "$rc"
}
: > "$DIAG/bootstrap.log";trap finish EXIT
[[ "$PIN" =~ ^[0-9a-f]{40}$ && ( "$MODE" == --gui || "$MODE" == --headless ) ]] || exit 2
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || { echo A18_WSL_REQUIRED; exit 2; }
URL=https://github.com/silverbjin/samsung_AXI.git
helper="$DIAG/helper.sh"
curl -fsSL --max-time 30 "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_platform_bootstrap.sh" -o "$helper" 2>>"$DIAG/bootstrap.log"
source "$helper"
TARGET="$(smartdish_new_workspace "$PIN" A18 "$HOME")"
smartdish_pin_checkout "$URL" "$PIN" feat/smartdish-a18-crossed-layouts "$TARGET" >> "$DIAG/bootstrap.log" 2>&1
echo "REQUESTED_SHA=$PIN";echo "ACTUAL_SOURCE_SHA=$(git -C "$TARGET" rev-parse HEAD)";echo "OWNER_WORKSPACE=$TARGET"
cd "$TARGET"
bash scripts/a18_pilot_batch.sh "$PIN" "$TARGET/generated_a18" "$MODE" "$PHASE"
