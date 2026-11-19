#!/usr/bin/env bash
# SAMSUNGAXI only: independent read-only WSLg GLX renderer checks.
set -Eeuo pipefail
OUT="$HOME/samsung_AXI/logs/gpu_route_$(date -u +%Y%m%dT%H%M%SZ)"
if [[ $# -gt 0 ]]; then OUT="$1"; fi
command -v glxinfo >/dev/null || { echo 'BLOCKED: install mesa-utils for glxinfo'; exit 2; }
mkdir -p "$OUT"
SUMMARY="$OUT/summary.txt"
printf 'SAMSUNGAXI_GPU_ROUTE_READ_ONLY=1\n' >"$SUMMARY"
probe() {
  local label="$1"; shift
  local rc=0
  env -u LIBGL_ALWAYS_SOFTWARE -u GALLIUM_DRIVER -u MESA_D3D12_DEFAULT_ADAPTER_NAME "$@" timeout 15s glxinfo -B >"$OUT/$label.txt" 2>&1 || rc=$?
  local renderer accel
  renderer="$(grep -m1 'OpenGL renderer string:' "$OUT/$label.txt" || true)"
  accel="$(grep -m1 'Accelerated:' "$OUT/$label.txt" || true)"
  printf 'CASE=%s EXIT=%s %s %s\n' "$label" "$rc" "$renderer" "$accel" | tee -a "$SUMMARY"
}
probe default
probe d3d12 GALLIUM_DRIVER=d3d12
probe d3d12_nvidia GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
echo 'SAMSUNGAXI_GLX_COMPLETE_NOT_GAZEBO_PASS' | tee -a "$SUMMARY"
printf 'REPORT=%s\n' "$SUMMARY"
