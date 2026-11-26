#!/usr/bin/env bash
# Review-only local owner archive; no Gazebo or GPU job.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PIN="$(printenv SMARTDISH_B_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] || { echo B_A14_PIN_MISMATCH; exit 2; }
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || { echo B_A14_DIRTY; exit 2; }
exec python3 "$ROOT/scripts/smartdish_platform/runtime.py" --role B -- python3 "$ROOT/ai/scripts/audit_b_a14.py" "$@"
