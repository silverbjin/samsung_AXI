#!/usr/bin/env bash
# Independent, no global pkill, no changes to original AXIA repositories.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export RESTAURANT_ROOT="$ROOT"
export TURTLEBOT3_MODEL=waffle_pi
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-58}"
export GZ_PARTITION="${GZ_PARTITION:-restaurant_mvp}"
MODE="${1:-world}"; MENU="${2:-NORMAL}"
if [[ "${3:-}" == "--preflight-only" ]]; then
  [[ "$MODE" == live ]] || { echo 'S5_BLOCKED_PREFLIGHT_REQUIRES_LIVE'; exit 2; }
  # Same contract as production live path, before ROS and map preflight.
  source "$ROOT/scripts/s5_run_id_contract.sh"
  s5_run_id_commit || exit 2
  echo 'S5_OWNER_CORE_PREFLIGHT_PASS_NO_GOAL'
  exit 0
fi
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
case "$MODE" in world|mapping|navigation|demo|live) ;; *) echo 'Usage: restaurant_demo.sh world|mapping|navigation|demo [NORMAL|SOUP]'; exit 2;; esac
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
# Live-S5 only, explicit A/B candidate. Never change LiDAR, motor, physics
# settings or the default 5Hz RGB-D for other teaching modes.
RGBD_RATE_ARGS=()
if [[ "$MODE" == live ]]; then
  case "${SAMSUNGAXI_S5_PERF_MODE:-baseline}" in
    baseline) echo 'S5_PERF_RGBD_RATE_HZ=5' ;;
    rgbd2) RGBD_RATE_ARGS=(--rgbd-rate-hz 2); echo 'S5_PERF_RGBD_RATE_HZ=2' ;;
    *) echo 'S5_PERF_BLOCKED_UNKNOWN_MODE' >&2; exit 2 ;;
  esac
fi
if [[ "$MODE" == live && "${SAMSUNGAXI_S6_VISION:-0}" == 1 ]]; then
  RGBD_RATE_ARGS+=(--vision-camera-offset-z 0.65)
  echo 'S6_VISION_CAMERA_MOUNT_Z_OFFSET_M=0.65'
fi
python3 "$ROOT/scripts/prepare_waffle_rgbd.py" --source "$OFFICIAL_SDF" --out "$ROOT/generated/waffle_pi_rgbd.sdf" "${RGBD_RATE_ARGS[@]}" | tee -a "$RUNLOG"
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
NAV_AUTO_ARGS=()
if [[ "$MODE" == navigation || "$MODE" == live ]]; then
  # Instructor GUI and S5 live only: improved proven S2-MAP-03 saved map.
  MAP="$ROOT/maps/candidates/s2_map03/restaurant_map.yaml"
  NAV_AUTO_ARGS=(--auto-initial-pose)
  echo "RESTAURANT_OWNER_GUI_MAP=S2_MAP03_CANDIDATE_81PCT"
  PYTHONPATH="$ROOT/scripts" python3 -c 'from s3_map_contract import validate_s2_map03_candidate; import os; print("S5_MAP03_CUSTODY_PASS",validate_s2_map03_candidate(os.environ["RESTAURANT_ROOT"]))'
fi
[[ -s "$MAP" ]] || { echo "BLOCKED: $MAP missing. Run mapping and save a real map first."; exit 2; }
NAV_SRC="$(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/params/nav2_params.yaml"
python3 "$ROOT/scripts/prepare_nav2_params.py" --source "$NAV_SRC" --out "$ROOT/generated/nav2_params.yaml" "${NAV_AUTO_ARGS[@]}" | tee -a "$RUNLOG"
if [[ "$MODE" == live ]]; then
  [[ "${SAMSUNGAXI_S5_GOALS_APPROVED:-}" == YES-S5-LIVE-GOALS ]] || {
    echo 'S5_LIVE_BLOCKED_OWNER_GOAL_APPROVAL_REQUIRED'; exit 2;
  }
  source "$ROOT/scripts/s5_run_id_contract.sh"
  s5_run_id_commit || exit 2
  S5_RUN_ID="$SAMSUNGAXI_S5_RUN_ID"
  S5_EVIDENCE_DIR="$ROOT/generated/s5/$S5_RUN_ID"
  mkdir -p "$S5_EVIDENCE_DIR"
  echo "S5_LIVE_EVIDENCE_DIR=$S5_EVIDENCE_DIR"
  echo 'S5_LIVE_START: REAL_GAZEBO_NO_GOAL_UNTIL_INTERACTIVE_APPROVAL'
  S6_MODE_ARGS=()
  if [[ "${SAMSUNGAXI_S6_VISION:-0}" == 1 ]]; then
    S6_MODE_ARGS=(--s6-vision --s6-scene-fixture
                  --s6-model "$ROOT/models/s6_dish_prototype.json")
    echo S6_OPT_IN_REAL_RGB_DISH_GATE_ENABLED
  elif [[ "${SAMSUNGAXI_S6_VISION:-0}" != 0 ]]; then
    echo S6_BLOCKED_INVALID_OPT_IN >&2; exit 2
  fi
  python3 "$ROOT/scripts/ci_s3_amcl_smoke.py" \
    "${S6_MODE_ARGS[@]}" \
    --exercise-goals --menu-safety --no-initial-pose-publish \
    --s5-integrated --gui --live-owner \
    --robot-sdf "$ROBOT_SDF" --map "$MAP" \
    --params "$ROOT/generated/nav2_params.yaml" \
    --log "$S5_EVIDENCE_DIR/s5_nav2_launch.log" \
    --evidence "$S5_EVIDENCE_DIR/s5_live_evidence.json" 2>&1 | tee -a "$RUNLOG"
  exit "${PIPESTATUS[0]}"
fi
if [[ "$MODE" == navigation ]]; then
  echo 'RESTAURANT_S3_NAV_READY_CHECK_OWN_ROBOT_BEFORE_GOAL'
  ros2 launch restaurant_bringup navigation.launch.py robot_sdf:="$ROBOT_SDF" map:="$MAP" params_file:="$ROOT/generated/nav2_params.yaml" 2>&1 | tee -a "$RUNLOG"
  # NO GOAL acceptance must never fall through to delivery_manager.
  exit "${PIPESTATUS[0]}"
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
