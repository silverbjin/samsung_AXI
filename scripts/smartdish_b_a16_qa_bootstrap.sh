#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
PIN="${SMARTDISH_B_QA04_SOURCE_SHA:-}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && $# == 3 ]] || { echo "Usage: pin env + bootstrap A16_RAW A16_DIAG A15_RAW (absolute paths, companion .sha256)";exit 2; }
for p in "$@";do [[ "$p" == /* && -f "$p" && -f "$p.sha256" && ! -L "$p" && ! -L "$p.sha256" ]] || exit 2;done
RUN="$(mktemp -d "$HOME/smartdish_b_qa04_${PIN:0:12}_XXXXXX")"
git clone --no-checkout --filter=blob:none https://github.com/silverbjin/samsung_AXI.git "$RUN/repo"
git -C "$RUN/repo" checkout --detach "$PIN"
[[ "$(git -C "$RUN/repo" rev-parse HEAD)" == "$PIN" ]] || exit 2
SMARTDISH_B_QA04_SOURCE_SHA="$PIN" bash "$RUN/repo/scripts/smartdish_b_a16_qa_one_shot.sh" --owner "$1" --diagnostics "$2" --a15 "$3" --out-dir "$RUN/private_audit"
