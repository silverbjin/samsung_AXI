#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
PIN="${SMARTDISH_B_QA05_SOURCE_SHA:-}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && $# == 4 ]] || { echo "Usage: pin env + bootstrap A15_RAW A16_RAW A16_DIAG QA04_DIAG (absolute paths, companion .sha256)";exit 2; }
# CLI owns input file and sidecar validation so a missing input still yields diagnostics.
for p in "$@";do [[ "$p" == /* ]] || { echo B_QA05_ABSOLUTE_PATH_REQUIRED;exit 2; };done
RUN="$(mktemp -d "$HOME/smartdish_b_qa05_${PIN:0:12}_XXXXXX")"
git clone --no-checkout --filter=blob:none https://github.com/silverbjin/samsung_AXI.git "$RUN/repo"
git -C "$RUN/repo" checkout --detach "$PIN"
[[ "$(git -C "$RUN/repo" rev-parse HEAD)" == "$PIN" ]] || exit 2
SMARTDISH_B_QA05_SOURCE_SHA="$PIN" bash "$RUN/repo/scripts/smartdish_b_qa05_one_shot.sh" --a15 "$1" --a16 "$2" --a16-diag "$3" --qa04 "$4" --out-dir "$RUN/private_audit"
