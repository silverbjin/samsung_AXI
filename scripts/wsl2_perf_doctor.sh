#!/usr/bin/env bash
# Read-only snapshot: never edits Windows .wslconfig, WSL GPU, Gazebo or ROS.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/logs/wsl2_perf_$(date -u +%Y%m%dT%H%M%SZ).txt}"
mkdir -p "$(dirname -- "$OUT")"
{
  echo RESTAURANT_WSL2_PERF_DIAGNOSTIC_READ_ONLY=1
  date -u '+UTC=%Y-%m-%dT%H:%M:%SZ'
  printf 'KERNEL='; uname -r
  printf 'WSL_DISTRO_NAME=%s DISPLAY=%s WAYLAND_DISPLAY=%s\n' "${WSL_DISTRO_NAME:-unset}" "${DISPLAY:-unset}" "${WAYLAND_DISPLAY:-unset}"
  printf 'MESA_D3D12_DEFAULT_ADAPTER_NAME=%s\n' "${MESA_D3D12_DEFAULT_ADAPTER_NAME:-unset}"
  printf 'LIBGL_ALWAYS_SOFTWARE=%s GALLIUM_DRIVER=%s\n' "${LIBGL_ALWAYS_SOFTWARE:-unset}" "${GALLIUM_DRIVER:-unset}"
  if [[ -e /dev/dxg ]]; then echo 'DXG_DEVICE=present'; else echo 'DXG_DEVICE=absent'; fi
  printf 'CPU_LOGICAL_VISIBLE='; nproc
  echo '--- memory ---'; free -h
  echo '--- cgroup limits ---'
  for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/cpu.max; do
    if [[ -r "$f" ]]; then printf '%s=' "$f"; cat "$f"; fi
  done
  echo '--- OpenGL renderer ---'
  if command -v glxinfo >/dev/null; then
    glxinfo -B 2>&1 | grep -Ei '(OpenGL vendor|OpenGL renderer|accelerated|device:|direct rendering)' || true
    if [[ -e /dev/dxg && "${RESTAURANT_COMPARE_NVIDIA:-0}" == 1 ]]; then
      echo '--- alternate NVIDIA render test (no persistent setting) ---'
      MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA glxinfo -B 2>&1 | grep -Ei '(OpenGL vendor|OpenGL renderer|accelerated|device:|direct rendering)' || true
    fi
  else echo 'GLXINFO_MISSING: install optional mesa-utils for renderer name'; fi
  if command -v nvidia-smi >/dev/null; then
    echo '--- NVIDIA device visibility (not proof of Ogre2 usage) ---'
    timeout 8s nvidia-smi -L 2>&1 || true
  else echo 'NVIDIA_SMI_UNAVAILABLE'; fi
  echo '--- process snapshot ---'
  ps -eo pid,comm,%cpu,%mem,rss --sort=-%cpu | head -n 13 || true
  echo '--- Windows .wslconfig whitelisted settings, read-only ---'
  if command -v powershell.exe >/dev/null; then
    timeout 10s powershell.exe -NoProfile -NonInteractive -Command \
      '$p=Join-Path $env:USERPROFILE ".wslconfig"; if(Test-Path $p){Get-Content $p | Where-Object { $_ -match "^\s*(\[wsl2\]|memory|swap|processors|guiApplications|gpuSupport)\s*(=|$)" }} else {"WSLCONFIG=ABSENT"}' 2>&1 | tr -d '\r' || true
  else echo 'POWERSHELL_EXE_UNAVAILABLE: check %UserProfile%\\.wslconfig in Windows PowerShell'; fi
  if [[ "${RESTAURANT_READ_GZ_STATS:-0}" == 1 ]] && command -v gz >/dev/null; then
    echo '--- optional Gazebo stats (3 seconds) ---'
    timeout 3s gz topic -e -t /world/restaurant/stats 2>&1 | head -n 35 || true
  fi
  echo RESTAURANT_WSL2_PERF_PROBE_COMPLETE_NO_CONFIG_CHANGED
} | tee "$OUT"
printf 'RESTAURANT_WSL2_PERF_REPORT=%s\n' "$OUT"
