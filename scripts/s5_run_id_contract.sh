#!/usr/bin/env bash
# Shared by pinned WSL2 GUI wrapper and in-repository S5 live runner.
# Source this file; run s5_run_id_commit before any ROS or Goal.
s5_run_id_commit() {
  local id="${SAMSUNGAXI_S5_RUN_ID:-}"
  if [[ -z "$id" ]]; then
    id="$(date -u +%Y%m%dT%H%M%SZ)-${BASHPID}"
  fi
  if [[ ! "$id" =~ ^[A-Za-z0-9_-]+$ ]]; then
    printf 'S5_BLOCKED_INVALID_RUN_ID\n' >&2
    return 2
  fi
  export SAMSUNGAXI_S5_RUN_ID="$id"
  printf 'S5_RUN_ID=%s\nS5_RUN_ID_CONTRACT_PASS\n' "$id"
}
