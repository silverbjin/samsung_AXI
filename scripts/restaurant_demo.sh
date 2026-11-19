#!/usr/bin/env bash
# Independent, no global pkill, no changes to original AXIA repositories.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export RESTAURANT_ROOT="$ROOT"
export TURTLEBOT3_MODEL=waffle_pi
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-58}"
export GZ_PARTITION="${GZ_PARTITION:-restaurant_mvp}"
MODE="${1:-world}"; MENU="${2:-NORMAL}"
mkdir -p "$ROOT/logs" "$ROOT/generated"
STAMP="$(date +%Y%m%d_%H%M%S)"
RUNLOG="$ROOT/logs/${MODE}_${STAMP}.log"
LAUNCH_PID=""
cleanup() {
  local status=$?
  trap - EXIT INT TERM
  if [[ -n "$LAUNCH_PID" ]] && kill -0 "$LAUNCH_PID" 2>/dev/null; then
    kill -INT "$LAUNCH_PID" 2>/dev/null || true
    wait "$LAUNCH_PID" 2>/dev/null || true
  fi
  echo "RESTAURANT_OWNER_LOG=$RUNLOG"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

[[ -r /opt/ros/jazzy/setup.bash ]] || { echo 'BLOCKED: /opt/ros/jazzy/setup.bash missing'; exit 2; }
# shellcheck disable=SC1091
set +u
source /opt/ros/jazzy/setup.bash
set -u
command -v colcon >/dev/null || { echo 'BLOCKED: install python3-colcon-common-extensions'; exit 2; }
command -v git >/dev/null || { echo 'BLOCKED: git missing'; exit 2; }
[[ "${WSL_DISTRO_NAME:-}" != '' ]] || echo 'INFO: WSL_DISTRO_NAME absent; GUI must be confirmed manually.'

need_pkg() { ros2 pkg prefix "$1" >/dev/null 2>&1 || { echo "BLOCKED: ROS package $1 not installed"; return 1; }; }
if [[ "$MODE" == doctor ]]; then
  echo 'RESTAURANT_MVP_DIAGNOSTIC_ONLY_NO_GOAL'
  for pkg in ros_gz_sim ros_gz_bridge nav2_bringup nav2_simple_commander slam_toolbox turtlebot3_gazebo; do
    if ros2 pkg prefix "$pkg" >/dev/null 2>&1; then echo "OK $pkg"; else echo "MISSING $pkg"; fi
  done
  command -v gz || true
  echo "DISPLAY=${DISPLAY:-<unset>} WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<unset>}"
  exit 0
fi
case "$MODE" in world|mapping|navigation|demo) ;; *) echo 'Usage: restaurant_demo.sh world|mapping|navigation|demo [NORMAL|SOUP]'; exit 2;; esac
for pkg in ros_gz_sim ros_gz_bridge ros_gz_image; do need_pkg "$pkg"; done
# CI and Owner use the same pinned ROBOTIS Jazzy source, not a floating branch HEAD.
UPSTREAM="$ROOT/src/upstream/turtlebot3_simulations"
ROBOTIS_PIN='45633014a14e8f438495b532a723e4ad45cbbd31'
if [[ ! -d "$UPSTREAM/.git" ]]; then
  echo 'INFO: cloning reviewed ROBOTIS Jazzy simulation into isolated src/upstream/'
  mkdir -p "$ROOT/src/upstream"
  git clone -q --depth 1 -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git "$UPSTREAM"
fi
[[ "$(git -C "$UPSTREAM" remote get-url origin)" == 'https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git' ]] || {
  echo "BLOCKED: unexpected upstream repository origin=$UPSTREAM"; exit 2;
}
[[ -z "$(git -C "$UPSTREAM" status --porcelain --untracked-files=normal)" ]] || {
  echo "BLOCKED: local upstream has modifications=$UPSTREAM"; exit 2;
}
if [[ "$(git -C "$UPSTREAM" rev-parse HEAD)" != "$ROBOTIS_PIN" ]]; then
  git -C "$UPSTREAM" fetch -q --depth 1 origin "$ROBOTIS_PIN"
  git -C "$UPSTREAM" checkout -q --detach "$ROBOTIS_PIN"
fi
echo "RESTAURANT_ROBOTIS_PIN=$ROBOTIS_PIN"
(
  cd "$ROOT"
  colcon build --symlink-install --packages-up-to restaurant_world restaurant_bringup restaurant_delivery ${EXTRA_COLCON_ARGS:-} >"$RUNLOG" 2>&1
) || { tail -n 40 "$RUNLOG"; echo "RESTAURANT_BUILD_BLOCKED_LOG=$RUNLOG"; exit 1; }
# shellcheck disable=SC1091
set +u
source "$ROOT/install/setup.bash"
set -u
for pkg in restaurant_world restaurant_bringup restaurant_delivery turtlebot3_gazebo; do need_pkg "$pkg"; done
ROBOTIS_SHARE="$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo"
OFFICIAL_SDF="$ROBOTIS_SHARE/models/turtlebot3_waffle_pi/model.sdf"
# Use the SAME generated RGB-D sensor in every mode, including the first GUI world demo.
python3 "$ROOT/scripts/prepare_waffle_rgbd.py" --source "$OFFICIAL_SDF" --out "$ROOT/generated/waffle_pi_rgbd.sdf" | tee -a "$RUNLOG"
ROBOT_SDF="$ROOT/generated/waffle_pi_rgbd.sdf"
if [[ "$MODE" == world ]]; then
  echo 'RESTAURANT_S1_STARTED_NOT_YET_GUI_VERIFIED'
  ros2 launch restaurant_bringup world.launch.py robot_sdf:="$ROBOT_SDF" 2>&1 | tee -a "$RUNLOG"
  exit "${PIPESTATUS[0]}"
fi
need_pkg nav2_bringup
need_pkg slam_toolbox
need_pkg nav2_simple_commander
if [[ "$MODE" == mapping ]]; then
  echo 'RESTAURANT_S2_MAPPING_STARTED_MAP_NOT_SAVED_YET'
  ros2 launch restaurant_bringup mapping.launch.py robot_sdf:="$ROBOT_SDF" 2>&1 | tee -a "$RUNLOG"
  exit "${PIPESTATUS[0]}"
fi
MAP="$ROOT/maps/restaurant_map.yaml"
[[ -s "$MAP" ]] || { echo "BLOCKED: $MAP missing. Run mapping and save a real map first."; exit 2; }
NAV_SRC="$(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/params/nav2_params.yaml"
python3 "$ROOT/scripts/prepare_nav2_params.py" --source "$NAV_SRC" --out "$ROOT/generated/nav2_params.yaml" | tee -a "$RUNLOG"
if [[ "$MODE" == navigation ]]; then
  echo 'RESTAURANT_S3_NAV_READY_CHECK_OWN_ROBOT_BEFORE_GOAL'
  ros2 launch restaurant_bringup navigation.launch.py robot_sdf:="$ROBOT_SDF" map:="$MAP" params_file:="$ROOT/generated/nav2_params.yaml" 2>&1 | tee -a "$RUNLOG"
fi
[[ "$MENU" == NORMAL || "$MENU" == SOUP ]] || { echo 'MENU must be NORMAL or SOUP'; exit 2; }
echo 'RESTAURANT_DEMO_STARTING: inspect empty Gazebo / real sensor before accepting goals.'
ros2 launch restaurant_bringup navigation.launch.py robot_sdf:="$ROBOT_SDF" map:="$MAP" params_file:="$ROOT/generated/nav2_params.yaml" >>"$RUNLOG" 2>&1 &
LAUNCH_PID=$!
ready=0
for _ in $(seq 1 90); do
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then break; fi
  if ros2 action list 2>/dev/null | grep -q '^/navigate_to_pose$'; then ready=1; break; fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "RESTAURANT_PREGOAL_BLOCKED_ACTION_ABSENT; log=$RUNLOG"; exit 1
fi
ros2 run restaurant_delivery delivery_manager --menu "$MENU" 2>&1 | tee -a "$RUNLOG"
