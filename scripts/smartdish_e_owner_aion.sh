#!/usr/bin/env bash
# Owner-only C v1 AI integration: no A/Nav2 auto-launch.
set -Eeuo pipefail
MODE="${1:---preflight}"
[[ "$#" -le 1 && "$MODE" =~ ^--(preflight|run-ui)$ ]] ||
  { echo E_OWNER_AION_BLOCKED=INVALID_MODE >&2; exit 2; }
PIN="${SMARTDISH_E_SOURCE_SHA:-}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] ||
  { echo E_OWNER_AION_BLOCKED=SOURCE_PIN_REQUIRED >&2; exit 2; }
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
    if [[ "$CURRENT_HEAD" != "4dbdeca6a0a8f8120cb42a44bd589d356726eb5d" ]]; then
      echo E_OWNER_AION_BLOCKED=PIN_DRIFT_MANUAL_REVIEW >&2; exit 2
    fi
    git -C "$WORKDIR" fetch --depth 16 origin "$PIN" ||
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
STATE="$HOME/.local/state/smartdish-e-owner-aion"
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
echo E_OWNER_AION_LAUNCHING_C_D_ONLY
echo E_OWNER_AION_REQUIRE_A_OPERATOR_TTY_AND_NAV2_SEPARATELY
exec ros2 launch smartdish_service smartdish_e_owner_aion.launch.py \
  ai_available:=true owner_gazebo_integration:=true "model_path:=$CHECKPOINT"
