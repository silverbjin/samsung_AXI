#!/usr/bin/env bash
# B QA03: pinned, CPU-isolated, read-only A15 OWNER evidence reviewer. NEVER source.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
  exec python3 "$ROOT/ai/scripts/b_a15_qa_cli.py" --help
fi
PIN="${SMARTDISH_B_QA03_SOURCE_SHA:-}"
if [[ ! "$PIN" =~ ^[0-9a-f]{40}$ ]]; then echo B_A15_QA03_SHA_REQUIRED >&2;exit 2;fi
if [[ "$(git -C "$ROOT" rev-parse HEAD)" != "$PIN" ]]; then echo B_A15_QA03_SHA_DRIFT >&2;exit 2;fi
if [[ -n "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]]; then echo B_A15_QA03_DIRTY_WORKTREE >&2;exit 2;fi
python3 "$ROOT/scripts/smartdish_platform/baseline.py" --root "$ROOT" --baseline b8ef3998973a5e33b67ddd5c5b63c3c89b837840
exec python3 "$ROOT/scripts/smartdish_platform/runtime.py" --role B -- \
  python3 "$ROOT/ai/scripts/b_a15_qa_cli.py" "$@"
