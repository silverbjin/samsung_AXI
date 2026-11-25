#!/usr/bin/env bash
# SmartDish B12R offline WSL2 review runner. Run via bash; never source this file.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 "$ROOT/ai/scripts/smartdish_b12r_cli.py" "$@"
