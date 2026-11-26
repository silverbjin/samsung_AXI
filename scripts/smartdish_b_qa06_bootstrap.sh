#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
PIN="${SMARTDISH_B_QA06_SOURCE_SHA:-}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]]
RUN="$(mktemp -d "$HOME/smartdish_b_qa06_${PIN:0:12}_XXXXXX")"
git clone --no-checkout --filter=blob:none https://github.com/silverbjin/samsung_AXI.git "$RUN/repo"
git -C "$RUN/repo" checkout --detach "$PIN"
[[ "$(git -C "$RUN/repo" rev-parse HEAD)" == "$PIN" ]]
SMARTDISH_B_QA06_SOURCE_SHA="$PIN" bash "$RUN/repo/scripts/smartdish_b_qa06_one_shot.sh" "$@"
