#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
PIN="${SMARTDISH_B_QA04_SOURCE_SHA:-}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] || exit 2
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || exit 2
python3 "$ROOT/scripts/smartdish_platform/baseline.py" --root "$ROOT" --baseline b8ef3998973a5e33b67ddd5c5b63c3c89b837840
exec python3 "$ROOT/scripts/smartdish_platform/runtime.py" --role B -- python3 "$ROOT/ai/scripts/b_a16_qa_cli.py" --verifier-sha "$PIN" "$@"
