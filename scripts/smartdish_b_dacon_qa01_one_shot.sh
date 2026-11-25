#!/usr/bin/env bash
# B-DATA-QA-01: offline QA only; no Gazebo, operator approval, or C model training.
# Launch with `bash`; do not source into the interactive shell.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 "$ROOT/ai/scripts/smartdish_b_dacon_qa01_cli.py" "$@"
