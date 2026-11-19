#!/usr/bin/env bash
# Samsung AXI owner GUI entrypoint: fetch a reviewed revision, then reuse the
# same in-repository runner and robot/Nav2 assets used by CI.
set -Eeuo pipefail

REPO_URL='https://github.com/silverbjin/samsung_AXI.git'
MODE='world'
MENU='NORMAL'
REF="${SAMSUNG_AXI_REF:-main}"
WORKSPACE="${SAMSUNG_AXI_WORKSPACE:-$HOME/samsung_AXI}"
INSTALL_DEPS=1
SELF_TEST=0

usage() {
  cat <<'USAGE'
Usage: bash owner_wsl2_once.sh [world|mapping|navigation|demo|doctor] [NORMAL|SOUP] [--ref <commit-sha-or-main>] [--workspace <directory>] [--no-install-deps]
  world       Gazebo GUI + Waffle Pi + registered RGB-D + LiDAR (NO GOAL, default)
  mapping     Gazebo + official SLAM Toolbox, manual mapping (NO GOAL)
  navigation  Gazebo + existing saved map + Nav2, no automatic goal
  demo        Real Nav2 delivery/return (requires an observed valid saved map)
  doctor      Dependency/WSLg diagnostic, NO GOAL
  --self-test Syntax/runtime argument smoke only; does not install or launch ROS

Defaults: --ref main, --workspace "$HOME/samsung_AXI".
Pin --ref to the exact CI-reviewed 40-character SHA for owner acceptance.
No force checkout, no global process kill, no changes to AXIA repositories.
USAGE
}

if [[ $# -gt 0 && "$1" != --* ]]; then MODE="$1"; shift; fi
if [[ $# -gt 0 && "$1" != --* ]]; then MENU="$1"; shift; fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref) [[ $# -ge 2 ]] || { echo 'ERROR: --ref needs a value' >&2; exit 2; }; REF="$2"; shift 2 ;;
    --workspace) [[ $# -ge 2 ]] || { echo 'ERROR: --workspace needs a directory' >&2; exit 2; }; WORKSPACE="$2"; shift 2 ;;
    --no-install-deps) INSTALL_DEPS=0; shift ;;
    --self-test) SELF_TEST=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument $1" >&2; usage; exit 2 ;;
  esac
done
case "$MODE" in world|mapping|navigation|demo|doctor) ;; *) usage; exit 2 ;; esac
case "$MENU" in NORMAL|SOUP) ;; *) echo 'ERROR: menu must be NORMAL or SOUP' >&2; exit 2 ;; esac
if [[ "$REF" != main && ! "$REF" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo 'ERROR: --ref must be main or 40-character commit SHA' >&2; exit 2
fi
if (( SELF_TEST )); then
  echo 'RESTAURANT_OWNER_WSL2_SELF_TEST_PASS_NO_ROS_NO_GOAL'
  exit 0
fi
if ! grep -qiE '(microsoft|wsl)' /proc/sys/kernel/osrelease 2>/dev/null; then
  echo 'RESTAURANT_OWNER_BLOCKED_NOT_WSL2: run on the instructor WSL2 Ubuntu 24.04' >&2
  exit 2
fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != ubuntu || "${VERSION_ID:-}" != '24.04' ]]; then
  echo "RESTAURANT_OWNER_BLOCKED_OS: expected Ubuntu 24.04; found ${PRETTY_NAME:-unknown}" >&2
  exit 2
fi
if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
  echo 'RESTAURANT_OWNER_BLOCKED_ROS: install ROS 2 Jazzy (Ubuntu 24.04) first' >&2
  exit 2
fi
for command_name in git python3; do
  command -v "$command_name" >/dev/null || { echo "RESTAURANT_OWNER_BLOCKED_TOOL=$command_name" >&2; exit 2; }
done
if [[ "$MODE" != doctor && -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  echo 'RESTAURANT_OWNER_BLOCKED_GUI: WSLg DISPLAY/WAYLAND_DISPLAY is absent' >&2
  exit 2
fi
# Never overwrite another repo/worktree or discard user's local edits.
if [[ -e "$WORKSPACE" ]]; then
  [[ -d "$WORKSPACE/.git" ]] || { echo "RESTAURANT_OWNER_BLOCKED_WORKSPACE_NOT_GIT=$WORKSPACE" >&2; exit 2; }
  origin="$(git -C "$WORKSPACE" remote get-url origin)"
  [[ "$origin" == "$REPO_URL" ]] || { echo "RESTAURANT_OWNER_BLOCKED_ORIGIN=$origin" >&2; exit 2; }
  [[ -z "$(git -C "$WORKSPACE" status --porcelain --untracked-files=normal)" ]] || {
    echo "RESTAURANT_OWNER_BLOCKED_DIRTY_WORKTREE=$WORKSPACE" >&2; exit 2;
  }
else
  mkdir -p "$(dirname -- "$WORKSPACE")"
  git clone --quiet --no-checkout "$REPO_URL" "$WORKSPACE"
fi

git -C "$WORKSPACE" fetch --quiet --depth 1 origin "$REF"
RESOLVED="$(git -C "$WORKSPACE" rev-parse --verify FETCH_HEAD^{commit})"
if [[ "$REF" != main && "$RESOLVED" != "$REF" ]]; then
  echo "RESTAURANT_OWNER_BLOCKED_REF_MISMATCH requested=$REF fetched=$RESOLVED" >&2
  exit 2
fi
# Checkout without force. Existing modifications would already have blocked above.
git -C "$WORKSPACE" checkout --quiet --detach "$RESOLVED"
mkdir -p "$WORKSPACE/logs"
OWNER_LOG="$WORKSPACE/logs/owner_${MODE}_$(date -u +%Y%m%dT%H%M%SZ).log"
printf 'RESTAURANT_OWNER_REPO=%s\nRESTAURANT_OWNER_PINNED_SHA=%s\nRESTAURANT_OWNER_LOG=%s\n' "$WORKSPACE" "$RESOLVED" "$OWNER_LOG"

# ROS environment setup may expand unset variables; suspend nounset only here.
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

required_packages=(ros_gz_sim ros_gz_bridge ros_gz_image nav2_bringup nav2_simple_commander slam_toolbox robot_state_publisher tf2_ros)
missing=()
command -v colcon >/dev/null || missing+=(colcon)
python3 -c 'import yaml' >/dev/null 2>&1 || missing+=(python3-yaml)
for p in "${required_packages[@]}"; do
  ros2 pkg prefix "$p" >/dev/null 2>&1 || missing+=("$p")
done
if (( ${#missing[@]} > 0 )); then
  echo "RESTAURANT_OWNER_MISSING_DEPENDENCIES=${missing[*]}" | tee -a "$OWNER_LOG"
  if (( ! INSTALL_DEPS )); then
    echo 'RESTAURANT_OWNER_BLOCKED_DEPENDENCIES (use without --no-install-deps)' >&2
    exit 2
  fi
  # No apt source changes, no ROS distro upgrades, no Docker.
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends \
    python3-colcon-common-extensions python3-yaml \
    ros-jazzy-ros-gz ros-jazzy-ros-gz-image \
    ros-jazzy-nav2-bringup ros-jazzy-navigation2 ros-jazzy-slam-toolbox \
    ros-jazzy-robot-state-publisher ros-jazzy-tf2-ros
fi
if [[ "$MODE" == doctor ]]; then
  echo 'RESTAURANT_OWNER_DOCTOR_ONLY_NO_GOAL' | tee -a "$OWNER_LOG"
  bash "$WORKSPACE/scripts/restaurant_demo.sh" doctor 2>&1 | tee -a "$OWNER_LOG"
  exit "${PIPESTATUS[0]}"
fi
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-58}"
export GZ_PARTITION="${GZ_PARTITION:-restaurant_mvp}"
echo 'RESTAURANT_OWNER_STARTING_GUI_NO_GOAL_UNLESS_DEMO' | tee -a "$OWNER_LOG"
# Core runner belongs to this source revision and is also statically checked in Actions.
# Keep its Ctrl+C lifecycle in the foreground; never launch a background orphan.
bash "$WORKSPACE/scripts/restaurant_demo.sh" "$MODE" "$MENU" 2>&1 | tee -a "$OWNER_LOG"
exit "${PIPESTATUS[0]}"
