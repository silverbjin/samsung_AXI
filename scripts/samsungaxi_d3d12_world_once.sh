#!/usr/bin/env bash
# SAMSUNGAXI only: one Gazebo world session with verified WSLg D3D12 adapter.
# Does not edit .wslconfig, driver, /etc, ~/.bashrc, or any AXIA project.
set -Eeuo pipefail

MODE="\${1:-world}"
if [[ "$MODE" != world && "$MODE" != doctor ]]; then
  echo 'Usage: bash SAMSUNGAXI_D3D12_world_once.sh [doctor|world]' >&2
  exit 2
fi

command -v glxinfo >/dev/null || {
  echo 'SAMSUNGAXI_D3D12_BLOCKED: glxinfo missing; install mesa-utils separately' >&2
  exit 2
}

# Only the child probe (and below, its Gazebo session) receives the GPU variables.
if ! PROBE="$(env -u LIBGL_ALWAYS_SOFTWARE \
    GALLIUM_DRIVER=d3d12 \
    MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
    glxinfo -B 2>&1)"; then
  printf '%s\n' "$PROBE" >&2
  echo 'SAMSUNGAXI_D3D12_BLOCKED: OpenGL probe failed' >&2
  exit 1
fi
RENDERER="$(printf '%s\n' "$PROBE" | sed -n 's/^[[:space:]]*OpenGL renderer string:[[:space:]]*//p' | head -n 1)"
ACCEL="$(printf '%s\n' "$PROBE" | sed -n 's/^[[:space:]]*Accelerated:[[:space:]]*//p' | head -n 1)"
printf 'SAMSUNGAXI_GL_RENDERER=%s\nSAMSUNGAXI_GL_ACCELERATED=%s\n' "\${RENDERER:-unknown}" "\${ACCEL:-unknown}"
if [[ "$RENDERER" != *D3D12* || "$RENDERER" != *NVIDIA* || "$ACCEL" != yes ]]; then
  echo 'SAMSUNGAXI_D3D12_BLOCKED: expected accelerated D3D12 NVIDIA; NO GAZEBO STARTED' >&2
  exit 1
fi

echo 'SAMSUNGAXI_GLX_D3D12_PASS_GAZEBO_NOT_YET_VERIFIED'
if [[ "$MODE" == doctor ]]; then
  echo 'SAMSUNGAXI_D3D12_DOCTOR_ONLY_NO_GOAL'
  exit 0
fi

ROOT="\${SAMSUNG_AXI_ROOT:-$HOME/samsung_AXI}"
if [[ ! -f "$ROOT/scripts/restaurant_demo.sh" ]]; then
  echo "SAMSUNGAXI_D3D12_BLOCKED: missing existing runner: $ROOT/scripts/restaurant_demo.sh" >&2
  exit 2
fi
if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
  echo 'SAMSUNGAXI_D3D12_BLOCKED: ROS 2 Jazzy environment missing' >&2
  exit 2
fi
printf 'SAMSUNGAXI_D3D12_WORLD_NO_GOAL_ROOT=%s\n' "$ROOT"
# No global env changes. Uses the already working, local S1 world runner.
exec env -u LIBGL_ALWAYS_SOFTWARE \
  GALLIUM_DRIVER=d3d12 \
  MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
  bash "$ROOT/scripts/restaurant_demo.sh" world
