#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
PIN="${SMARTDISH_A17_SOURCE_SHA:-}"
DIAG="$(mktemp -d "$HOME/smartdish_a17_boot_XXXXXX")"
: > "$DIAG/bootstrap.log"
finish(){
 local rc=$?;trap - EXIT
 if (( rc != 0 ));then
  printf 'requested_sha=%s\nexit_code=%s\n' "$PIN" "$rc" > "$DIAG/status.txt"
  (cd "$DIAG"; sha256sum status.txt bootstrap.log > SHA256SUMS; tar -czf a17_bootstrap_diagnostics.tar.gz status.txt bootstrap.log SHA256SUMS; sha256sum a17_bootstrap_diagnostics.tar.gz > a17_bootstrap_diagnostics.tar.gz.sha256)
  echo "A17_BOOTSTRAP_DIAGNOSTICS=$DIAG/a17_bootstrap_diagnostics.tar.gz"
 fi
 exit "$rc"
}
trap finish EXIT
[[ "$PIN" =~ ^[0-9a-f]{40}$ && $# == 0 ]] || exit 2
grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || { echo A17_WSL_REQUIRED; exit 2; }
helper="$DIAG/helper.sh"
curl -fsSL --max-time 30 "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_platform_bootstrap.sh" -o "$helper" 2>>"$DIAG/bootstrap.log"
source "$helper"
TARGET="$(smartdish_new_workspace "$PIN" A17 "$HOME")"
smartdish_pin_checkout https://github.com/silverbjin/samsung_AXI.git "$PIN" feat/smartdish-a17-cleanup-root-cause "$TARGET" >> "$DIAG/bootstrap.log" 2>&1
echo "REQUESTED_SHA=$PIN";echo "ACTUAL_SOURCE_SHA=$(git -C "$TARGET" rev-parse HEAD)";echo "OWNER_WORKSPACE=$TARGET"
cd "$TARGET"
set +u
source /opt/ros/jazzy/setup.bash
set -u
python3 -u scripts/a17_cleanup_probe.py --sha "$PIN" --out "$TARGET/generated_a17"
