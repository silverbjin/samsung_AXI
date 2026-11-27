#!/usr/bin/env bash
# Exact-SHA WSL2 Owner product candidate. No CI spoofing, no automatic staff approval, no torch install.
set -Eeuo pipefail
MODE="${1:---run}"
[[ $# -le 1 && "$MODE" =~ ^--(preflight|run)$ ]] || { echo E_OWNER_BAD_MODE; exit 2; }
PIN="${SMARTDISH_E_SOURCE_SHA:-}"
L2_PIN=28dd5150b96ae842bebab1cd2ee1a3ce78cc4a33
UP_PIN=45633014a14e8f438495b532a723e4ad45cbbd31
CHECKPOINT="${SMARTDISH_C_V1_CHECKPOINT:-}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && "$CHECKPOINT" = /* && -f "$CHECKPOINT" && ! -L "$CHECKPOINT" ]] || { echo E_OWNER_PIN_OR_PRIVATE_CHECKPOINT_REQUIRED; exit 2; }
[[ -n "${WSL_DISTRO_NAME:-}" && -z "${GITHUB_ACTIONS:-}" && "${CI:-}" != true && -t 0 && -r /dev/tty && -w /dev/tty && -n "${DISPLAY:-}" ]] || { echo E_OWNER_WSL2_TTY_GUI_REQUIRED; exit 2; }
grep -qi microsoft /proc/sys/kernel/osrelease || { echo E_OWNER_WSL_KERNEL_REQUIRED; exit 2; }
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo E_OWNER_UBUNTU_2404_REQUIRED; exit 2; }
WORK="$HOME/samsung_AXI_e_product_recovery/$PIN"
case "$(realpath -m "$WORK")" in /mnt/*) echo E_OWNER_EXT4_REQUIRED;exit 2;; esac
case "$(realpath "$CHECKPOINT")" in "$(realpath -m "$WORK")"/*) echo E_OWNER_MODEL_MUST_STAY_OUTSIDE_REPO;exit 2;; esac
REPO=https://github.com/silverbjin/samsung_AXI.git
RUNNER="$(realpath "${BASH_SOURCE[0]}")"
export GIT_TERMINAL_PROMPT=0
if [[ ! -e "$WORK" ]]; then
  mkdir -p "$WORK"
  git -C "$WORK" init -q
  git -C "$WORK" remote add origin "$REPO"
  git -C "$WORK" fetch -q --depth 64 origin "$PIN"
  git -C "$WORK" checkout -q --detach FETCH_HEAD
fi
[[ -d "$WORK/.git" && "$(git -C "$WORK" remote get-url origin)" == "$REPO" ]] || { echo E_OWNER_REPO_ORIGIN;exit 2; }
[[ "$(git -C "$WORK" rev-parse HEAD)" == "$PIN" && -z "$(git -C "$WORK" status --porcelain --untracked-files=no)" ]] || { echo E_OWNER_PIN_DRIFT_NO_RESET;exit 2; }
git -C "$WORK" merge-base --is-ancestor "$L2_PIN" "$PIN" || { echo E_OWNER_L2_PIN_NOT_ANCESTOR;exit 2; }
cd "$WORK"
cmp -s "$RUNNER" scripts/smartdish_e_product_owner_once.sh || { echo E_OWNER_RUNNER_BYTES_MISMATCH;exit 2; }
echo "E_OWNER_SOURCE_SHA=$PIN"
echo "E_OWNER_CI_L2_BASELINE=$L2_PIN"
RUN="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVD="$HOME/.local/state/smartdish-e-product/$PIN/runs/$RUN"
ROOT="$EVD/a04_live"
mkdir -p "$ROOT"
printf '%s\n' "$PIN" > "$ROOT/source_sha.txt"
printf '%s\n' "$UP_PIN" > "$ROOT/upstream_sha.txt"
export SMARTDISH_E_SOURCE_SHA="$PIN" SMARTDISH_E_OWNER_PRODUCT_RUN="$RUN"
export ROS_DOMAIN_ID="$((80+$$%100))" GZ_PARTITION="smartdish_a04_owner_$RUN"
export RESTAURANT_ROOT="$WORK" TURTLEBOT3_MODEL=waffle_pi PYTHONNOUSERSITE=1
unset PYTHONOPTIMIZE
STARTED=0
finish() {
  rc=$?
  trap - EXIT INT TERM
  set +e
  if [[ "$STARTED" == 1 ]]; then
    /usr/bin/python3 scripts/smartdish_e_product_supervisor.py --owner --cleanup-only --report "$ROOT/archive_cleanup.json"
    if [[ $? != 0 ]]; then echo E_OWNER_RESIDUAL_PROCESS_ARCHIVE_BLOCKED; exit 2; fi
  fi
  printf 'source_sha=%s\nmode=%s\nexit_code=%s\n' "$PIN" "$MODE" "$rc" > "$ROOT/runner_receipt.txt"
  (cd "$ROOT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS)
  if [[ $? != 0 ]] || ! tar -C "$EVD" -czf "$EVD/a04-live.tar.gz" a04_live || ! sha256sum "$EVD/a04-live.tar.gz" > "$EVD/a04-live.tar.gz.sha256"; then
    echo E_OWNER_ARCHIVE_FAILED; exit 2
  fi
  echo "E_OWNER_EVIDENCE=$EVD/a04-live.tar.gz"
  cat "$EVD/a04-live.tar.gz.sha256"
  if [[ "$MODE" == --run && "$rc" == 0 ]]; then
    /usr/bin/python3 scripts/smartdish_e_product_qa_adapter.py --owner --tar "$EVD/a04-live.tar.gz" \
      --sidecar "$EVD/a04-live.tar.gz.sha256" --repo "$WORK" --out "$EVD/qa" --source-sha "$PIN" --run-id "$RUN"
    if [[ $? != 0 ]]; then echo E_OWNER_PHYSICAL_QA_HOLD; exit 3; fi
    echo E_OWNER_WSL2_PRODUCT_L3_CANDIDATE_REVIEW_REQUIRED
    echo "E_OWNER_QA=$EVD/qa/e_independent_qa.json"
  fi
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT TERM
[[ -f /opt/ros/jazzy/setup.bash ]] || { echo E_OWNER_ROS_JAZZY_MISSING;exit 2; }
# Never inherit another workspace or inject the C site into A/D/UI.
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH LD_LIBRARY_PATH
set +u
source /opt/ros/jazzy/setup.bash
set -u
for cmd in colcon cmake g++ make flock ros2; do command -v "$cmd" >/dev/null || { echo "E_OWNER_DEPENDENCY_MISSING=$cmd";exit 2; }; done
/usr/bin/python3 -c 'import numpy,scipy,pandas,matplotlib,PIL,yaml,tkinter,rclpy' || { echo E_OWNER_SYSTEM_PYTHON_DEPENDENCIES_MISSING;exit 2; }
for pkg in ros_gz_sim ros_gz_bridge nav2_bringup nav2_msgs robot_state_publisher; do
  ros2 pkg prefix "$pkg" >/dev/null || { echo "E_OWNER_ROS_PACKAGE_MISSING=$pkg";exit 2; }
done
C_VENV="$HOME/.venvs/smartdish-c-v1-py312-cpu"
[[ -x "$C_VENV/bin/python" ]] || { echo E_OWNER_EXISTING_C_VENV_REQUIRED;exit 2; }
exec 8>"$HOME/.venvs/.smartdish-c-v1.install.lock"
flock -n -s 8 || { echo E_OWNER_C_VENV_UPDATE_IN_PROGRESS;exit 2; }
/usr/bin/python3 scripts/smartdish_e_c_runtime_guard.py --c-venv "$C_VENV" --ros-python /usr/bin/python3 | tee "$ROOT/c_runtime_guard.log"
export SMARTDISH_E_C_SITE_PACKAGES="$C_VENV/lib/python3.12/site-packages"
/usr/bin/python3 scripts/smartdish_e_owner_model_preflight.py --checkpoint "$CHECKPOINT" --report "$ROOT/model_preflight.json"
UP="$WORK/src/upstream/turtlebot3_simulations"
if [[ ! -e "$UP" ]]; then
  mkdir -p "$UP";git -C "$UP" init -q
  git -C "$UP" remote add origin https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git
  git -C "$UP" fetch -q --depth 1 origin "$UP_PIN";git -C "$UP" checkout -q --detach FETCH_HEAD
fi
[[ "$(git -C "$UP" remote get-url origin)" == https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git && "$(git -C "$UP" rev-parse HEAD)" == "$UP_PIN" && -z "$(git -C "$UP" status --porcelain)" ]] || { echo E_OWNER_UPSTREAM_PIN_DRIFT;exit 2; }
STATE="$HOME/.local/state/smartdish-e-product/$PIN"
mkdir -p "$STATE"
exec 9>"$STATE/build.lock"
flock -n -x 9 || { echo E_OWNER_SAME_PIN_BUILD_BUSY;exit 2; }
cmake -S scripts/smartdish_a04_observer -B "$STATE/observer" 2>&1 | tee "$ROOT/ecm_configure.log"
cmake --build "$STATE/observer" -j2 2>&1 | tee "$ROOT/ecm_build.log"
PLUGIN="$STATE/observer/libsmartdish_a04_observer.so"
sha256sum "$PLUGIN" > "$ROOT/ecm_binary.sha256"
colcon --log-base "$STATE/colcon_log" build --base-paths "$WORK/src" \
  --packages-up-to restaurant_world restaurant_bringup smartdish_robot smartdish_ai smartdish_service \
  --build-base "$STATE/build" --install-base "$STATE/install" 2>&1 | tee "$ROOT/build.log"
set +u
source "$STATE/install/local_setup.bash"
set -u
/usr/bin/python3 scripts/smartdish_e_product_owner_installed.py --root "$WORK" --pin "$PIN" --install-base "$STATE/install" --out "$ROOT/installed_origin.json"
[[ "$(realpath "$(ros2 pkg prefix turtlebot3_gazebo)")" == "$(realpath "$STATE/install/turtlebot3_gazebo")" ]] || { echo E_OWNER_UPSTREAM_INSTALL_DRIFT;exit 2; }
ROBOT="$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/models/turtlebot3_waffle_pi/model.sdf"
PARAMS="$(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/params/nav2_params.yaml"
[[ -f "$ROBOT" && -f "$PARAMS" && -f "$PLUGIN" ]] || { echo E_OWNER_RUNTIME_FILES_MISSING;exit 2; }
echo E_OWNER_PRODUCT_PREFLIGHT_PASS_NO_GOAL
if [[ "$MODE" == --preflight ]]; then exit 0; fi
echo '실제 WSL2 Gazebo 단일 세션을 시작합니다. UI에서 임계값 적용, T03 수거 시작, 신규 RGB 확인 및 직원 승인을 직접 수행하십시오.'
read -r -p 'YES-E-PRODUCT-GO 입력: ' consent </dev/tty
[[ "$consent" == YES-E-PRODUCT-GO ]] || { echo E_OWNER_CONSENT_DENIED;exit 2; }
export SMARTDISH_E_OWNER_CONSENT="$consent"
STARTED=1
/usr/bin/python3 -u scripts/smartdish_e_product_supervisor.py --owner \
  --phase "$ROOT/session/startup_phase.json" --report "$ROOT/supervisor.json" -- \
  /usr/bin/python3 -u scripts/smartdish_e_product_owner.py --pin "$PIN" --run-id "$RUN" --checkpoint "$CHECKPOINT" \
  --out "$ROOT/session" --observer-plugin "$PLUGIN" --robot-source "$ROBOT" \
  --bridge-source src/restaurant_bringup/config/bridge.yaml --world-source src/restaurant_world/worlds/restaurant.sdf \
  --map maps/restaurant_map.yaml --poses src/smartdish_robot/config/table_poses.yaml --params "$PARAMS" 2>&1 | tee "$ROOT/console.log"
