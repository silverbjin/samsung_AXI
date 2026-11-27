#!/usr/bin/env bash
# Owner-only C v1 AI integration: station mode requires explicit actual TTY and UI approvals.
set -Eeuo pipefail
MODE="${1:---preflight}"
[[ "$#" -le 1 && "$MODE" =~ ^--(preflight|run-ui|run-station)$ ]] ||
  { echo E_OWNER_AION_BLOCKED=INVALID_MODE >&2; exit 2; }
PIN="${SMARTDISH_E_SOURCE_SHA:-}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] ||
  { echo E_OWNER_AION_BLOCKED=SOURCE_PIN_REQUIRED >&2; exit 2; }
RUNNER_PATH="$(realpath "${BASH_SOURCE[0]}")"
WORKDIR="$HOME/samsung_AXI_e_ai_on_v1"
REPO="https://github.com/silverbjin/samsung_AXI.git"
CHECKPOINT="${SMARTDISH_C_V1_CHECKPOINT:-}"
[[ -n "$CHECKPOINT" && "$CHECKPOINT" = /* ]] ||
  { echo E_OWNER_AION_BLOCKED=PRIVATE_MODEL_ABSOLUTE_PATH_REQUIRED >&2; exit 2; }
export GIT_TERMINAL_PROMPT=0
if [[ -e "$WORKDIR" ]]; then
  [[ -d "$WORKDIR/.git" ]] ||
    { echo E_OWNER_AION_BLOCKED=WORKDIR_EXISTS_NOT_GIT >&2; exit 2; }
  origin="$(git -C "$WORKDIR" remote get-url origin)"
  case "$origin" in
    https://github.com/silverbjin/samsung_AXI|https://github.com/silverbjin/samsung_AXI.git|git@github.com:silverbjin/samsung_AXI.git) ;;
    *) echo E_OWNER_AION_BLOCKED=WRONG_ORIGIN >&2; exit 2 ;;
  esac
  [[ -z "$(git -C "$WORKDIR" status --porcelain --untracked-files=all)" ]] ||
    { echo E_OWNER_AION_BLOCKED=LOCAL_CHANGES_PRESERVED >&2; exit 2; }
  CURRENT_HEAD="$(git -C "$WORKDIR" rev-parse HEAD)"
  if [[ "$CURRENT_HEAD" != "$PIN" ]]; then
    # One-way migration ONLY from the exact accepted original Owner E PIN.
    # New caller PIN is immutable; never reset/clean or merge a moving branch.
    if [[ "$CURRENT_HEAD" != "4dbdeca6a0a8f8120cb42a44bd589d356726eb5d" &&
          "$CURRENT_HEAD" != "316639a0a5c47121f3026c76e180efde3cea12d4" ]]; then
      echo E_OWNER_AION_BLOCKED=PIN_DRIFT_MANUAL_REVIEW >&2; exit 2
    fi
    git -C "$WORKDIR" fetch --depth 64 origin "$PIN" ||
      { echo E_OWNER_AION_BLOCKED=PIN_FETCH_FAILED >&2; exit 2; }
    git -C "$WORKDIR" merge-base --is-ancestor "$CURRENT_HEAD" "$PIN" ||
      { echo E_OWNER_AION_BLOCKED=PIN_NOT_DESCENDANT >&2; exit 2; }
    git -C "$WORKDIR" checkout --quiet --detach "$PIN" ||
      { echo E_OWNER_AION_BLOCKED=PIN_CHECKOUT_FAILED >&2; exit 2; }
    echo "E_OWNER_RUNTIME_PIN_FAST_FORWARD old=$CURRENT_HEAD new=$PIN"
  fi
  [[ "$(git -C "$WORKDIR" rev-parse HEAD)" == "$PIN" ]] ||
    { echo E_OWNER_AION_BLOCKED=PIN_DRIFT_MANUAL_REVIEW >&2; exit 2; }
else
  git clone --no-checkout --filter=blob:none "$REPO" "$WORKDIR"
  git -C "$WORKDIR" fetch --depth 1 origin "$PIN"
  git -C "$WORKDIR" checkout --detach "$PIN"
fi
cd "$WORKDIR"
[[ "$(git hash-object --no-filters "$RUNNER_PATH")" == "$(git rev-parse "$PIN:scripts/smartdish_e_owner_aion.sh")" ]] &&
  cmp -s "$RUNNER_PATH" scripts/smartdish_e_owner_aion.sh ||
  { echo E_OWNER_AION_BLOCKED=RUNNER_BYTES_MISMATCH >&2; exit 2; }
echo E_OWNER_RUNNER_BYTES_MATCH
echo "E_OWNER_SOURCE_SHA=$(git rev-parse HEAD)"
python3 scripts/smartdish_e_owner_model_preflight.py --checkpoint "$CHECKPOINT"
[[ -f /opt/ros/jazzy/setup.bash ]] ||
  { echo E_OWNER_AION_BLOCKED=ROS_JAZZY_MISSING >&2; exit 2; }
set +u
source /opt/ros/jazzy/setup.bash
set -u
command -v colcon >/dev/null ||
  { echo E_OWNER_AION_BLOCKED=COLCON_MISSING >&2; exit 2; }
colcon list --base-paths "$WORKDIR/src" --names-only |
  grep -Fxq smartdish_ai || { echo E_OWNER_AION_BLOCKED=C_PACKAGE_NOT_FOUND >&2; exit 2; }
colcon list --base-paths "$WORKDIR/src" --names-only |
  grep -Fxq smartdish_service || { echo E_OWNER_AION_BLOCKED=D_PACKAGE_NOT_FOUND >&2; exit 2; }
# E consumes the already-installed C P2 CPU runtime. Never reinstall torch.
C_VENV="$HOME/.venvs/smartdish-c-v1-py312-cpu"
[[ -x "$C_VENV/bin/python" ]] ||
  { echo E_OWNER_C_RUNTIME_BLOCKED=EXISTING_C_VENV_NOT_FOUND >&2; exit 2; }
command -v flock >/dev/null ||
  { echo E_OWNER_C_RUNTIME_BLOCKED=FLOCK_REQUIRED >&2; exit 2; }
exec 8>"$HOME/.venvs/.smartdish-c-v1.install.lock"
flock -n -s 8 ||
  { echo E_OWNER_C_RUNTIME_BLOCKED=C_VENV_UPDATE_IN_PROGRESS >&2; exit 2; }
python3 scripts/smartdish_e_c_runtime_guard.py \
  --c-venv "$C_VENV" --ros-python /usr/bin/python3 ||
  { echo E_OWNER_AION_BLOCKED=C_RUNTIME_CONTRACT_NOT_MET >&2; exit 2; }
export SMARTDISH_E_C_SITE_PACKAGES="$C_VENV/lib/python3.12/site-packages"
echo E_OWNER_AION_PREFLIGHT_PASS_OWNER_SCOPE_NO_GOAL
if [[ "$MODE" == --preflight ]]; then exit 0; fi
[[ -n "${DISPLAY:-}" ]] ||
  { echo E_OWNER_AION_BLOCKED=WSLG_DISPLAY_UNAVAILABLE >&2; exit 2; }
# Full station acceptance stays separate from the earlier C+D-only R2 mode.
if [[ "$MODE" == --run-station ]]; then
  [[ -n "${WSL_DISTRO_NAME:-}" && -t 0 && -r /dev/tty && -w /dev/tty && -z "${GITHUB_ACTIONS:-}" ]] ||
    { echo E_OWNER_STATION_BLOCKED=WSL_TTY_REQUIRED >&2; exit 2; }
  grep -qi microsoft /proc/sys/kernel/osrelease || { echo E_OWNER_STATION_BLOCKED=WSL_KERNEL_REQUIRED; exit 2; }
  case "$WORKDIR" in /mnt/*) echo E_OWNER_STATION_BLOCKED=EXT4_REQUIRED; exit 2;; esac
  RUN="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  EVD="$WORKDIR/generated/smartdish_e_owner_station/$RUN"
  mkdir -p "$EVD"
  finish_station() {
    rc=$?
    trap - EXIT INT TERM
    set +e
    printf 'source_sha=%s\nexit_code=%s\n' "$PIN" "$rc" > "$EVD/runner_receipt.txt"
    if ! tar -czf "$EVD.tar.gz" -C "$EVD" . || ! sha256sum "$EVD.tar.gz" > "$EVD.tar.gz.sha256"; then
      echo E_OWNER_STATION_EVIDENCE_ARCHIVE_FAILED >&2
      exit 2
    fi
    echo "E_OWNER_STATION_EVIDENCE=$EVD.tar.gz"
    cat "$EVD.tar.gz.sha256"
    exit "$rc"
  }
  trap finish_station EXIT
  trap 'exit 130' INT TERM
  echo "E_OWNER_STATION_RUN=$RUN" | tee "$EVD/console.log"
  unset PYTHONOPTIMIZE
  export PYTHONNOUSERSITE=1
  export RESTAURANT_ROOT="$WORKDIR" TURTLEBOT3_MODEL=waffle_pi
  export ROS_DOMAIN_ID="$((60 + $$ % 35))"
  export GZ_PARTITION="smartdish_e_owner_nav_$RUN"
  echo "E_OWNER_STATION_ISOLATION=$ROS_DOMAIN_ID/$GZ_PARTITION"
  # Existing Ubuntu/ROS dependencies only. No install or new C venv here.
  for pkg in ros_gz_sim ros_gz_bridge ros_gz_image nav2_bringup nav2_simple_commander slam_toolbox; do
    ros2 pkg prefix "$pkg" >/dev/null || { echo E_OWNER_STATION_MISSING_ROS_PACKAGE="$pkg"; exit 2; }
  done
  UPSTREAM="$WORKDIR/src/upstream/turtlebot3_simulations"
  UP_PIN=45633014a14e8f438495b532a723e4ad45cbbd31
  if [[ ! -d "$UPSTREAM/.git" ]]; then
    mkdir -p "$WORKDIR/src/upstream"
    git clone --quiet --no-checkout --filter=blob:none https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git "$UPSTREAM"
    git -C "$UPSTREAM" fetch --quiet --depth 1 origin "$UP_PIN"
    git -C "$UPSTREAM" checkout --quiet --detach "$UP_PIN"
  fi
  [[ "$(git -C "$UPSTREAM" remote get-url origin)" == https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git ]]
  [[ -z "$(git -C "$UPSTREAM" status --porcelain --untracked-files=normal)" ]]
  [[ "$(git -C "$UPSTREAM" rev-parse HEAD)" == "$UP_PIN" ]] || { echo E_OWNER_STATION_BLOCKED=UPSTREAM_PIN_DRIFT; exit 2; }
  STATE="$HOME/.local/state/smartdish-e-owner-aion/$PIN"
  mkdir -p "$STATE"
  colcon --log-base "$STATE/colcon_log" build --base-paths "$WORKDIR/src" \
    --packages-up-to restaurant_world restaurant_bringup restaurant_delivery smartdish_robot smartdish_ai smartdish_service \
    --build-base "$STATE/build" --install-base "$STATE/install" --symlink-install 2>&1 | tee "$EVD/build.log"
  set +u
  source "$STATE/install/local_setup.bash"
  set -u
  /usr/bin/python3 scripts/smartdish_e_installed_origin.py --root "$WORKDIR" --pin "$PIN" --install-base "$STATE/install" --packages smartdish_ai smartdish_service smartdish_robot --out "$EVD/installed_origin.json"
  /usr/bin/python3 scripts/smartdish_e_owner_model_preflight.py --checkpoint "$CHECKPOINT" --report "$EVD/model_preflight.json"
  SDF="$EVD/waffle.sdf"
  PARAMS="$EVD/nav2.yaml"
  /usr/bin/python3 scripts/prepare_waffle_rgbd.py --source "$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/models/turtlebot3_waffle_pi/model.sdf" --out "$SDF" --rgbd-rate-hz 2
  /usr/bin/python3 scripts/prepare_nav2_params.py --source "$(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/params/nav2_params.yaml" --out "$PARAMS" --auto-initial-pose --s6-bt-ack-ms 200
  echo E_OWNER_STATION_BUILD_VERIFIED_NO_GOAL
  /usr/bin/python3 -u scripts/smartdish_e_ci_station_nav_probe.py --pin "$PIN" --owner-checkpoint "$CHECKPOINT" --robot-sdf "$SDF" --params "$PARAMS" --out "$EVD/trace" 2>&1 | tee -a "$EVD/console.log"
  /usr/bin/python3 - "$EVD/trace/result.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["verdict"]=="E_OWNER_WSL2_AI_ON_STATION_L3_PASS" and d["private_model_loaded"] and d["ui_click_verified"]
assert not d["robot_mounted_tray_verified"] and not d["test4_opened"]
assert len(d["legs"])==len(d["action_status"])==3
print("E_OWNER_STATION_EVIDENCE_VERIFIED_SCOPE_ONLY")
PY
  exit 0
fi
STATE="$HOME/.local/state/smartdish-e-owner-aion/$PIN"
mkdir -p "$STATE"
colcon --log-base "$STATE/colcon_log" build --base-paths "$WORKDIR/src" \
  --packages-select smartdish_ai smartdish_service \
  --build-base "$STATE/build" --install-base "$STATE/install" --symlink-install
set +u
source "$STATE/install/local_setup.bash"
set -u
ros2 pkg executables smartdish_ai | grep -Fxq "smartdish_ai stability_inference_node" ||
  { echo E_OWNER_AION_BLOCKED=C_ENTRYPOINT_MISSING >&2; exit 2; }
ros2 pkg executables smartdish_service | grep -Fxq "smartdish_service smartdish_manager" ||
  { echo E_OWNER_AION_BLOCKED=D_ENTRYPOINT_MISSING >&2; exit 2; }
/usr/bin/python3 scripts/smartdish_e_installed_origin.py --root "$WORKDIR" --pin "$PIN" --install-base "$STATE/install" --packages smartdish_ai smartdish_service
echo E_OWNER_AION_LAUNCHING_C_D_ONLY
echo E_OWNER_AION_REQUIRE_A_OPERATOR_TTY_AND_NAV2_SEPARATELY
exec ros2 launch smartdish_service smartdish_e_owner_aion.launch.py \
  ai_available:=true owner_gazebo_integration:=true "model_path:=$CHECKPOINT"
