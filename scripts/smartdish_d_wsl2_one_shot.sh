#!/usr/bin/env bash
# SmartDish D05: safe repeatable WSL2 entry. No automatic Nav2 Goals.
set -Eeuo pipefail
STAGE=BOOT
SOURCE_SHA=UNVERIFIED
MODE="${1:---verify}"
if [[ $# -gt 1 || ! "$MODE" =~ ^--(preflight|verify|run-ui)$ ]]; then
  echo SMARTDISH_D_BLOCKED=INVALID_MODE >&2; exit 2
fi
TEST_MODE="${SMARTDISH_D_TEST_MODE:-0}"
BRANCH=feat/smartdish-d-service
REPO_URL=https://github.com/silverbjin/samsung_AXI.git
WORKDIR="$HOME/samsung_AXI_d_service"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/smartdish-d"
ROS_SETUP=/opt/ros/jazzy/setup.bash
if [[ "$TEST_MODE" == 1 ]]; then
  BRANCH="${SMARTDISH_D_TEST_BRANCH:-$BRANCH}"
  REPO_URL="${SMARTDISH_D_TEST_REPO_URL:-$REPO_URL}"
  WORKDIR="${SMARTDISH_D_TEST_WORKDIR:-$WORKDIR}"
  STATE_DIR="${SMARTDISH_D_TEST_STATE_DIR:-$STATE_DIR}"
  ROS_SETUP="${SMARTDISH_D_TEST_ROS_SETUP:-$ROS_SETUP}"
fi
REQUIRED_SHA="${SMARTDISH_D_SOURCE_SHA:-}"
[[ -z "$REQUIRED_SHA" || "$REQUIRED_SHA" =~ ^[a-f0-9]{40}$ ]] ||
  { echo SMARTDISH_D_BLOCKED=INVALID_SOURCE_PIN >&2; exit 2; }
[[ "$WORKDIR" = /* && "$STATE_DIR" = /* ]] ||
  { echo SMARTDISH_D_BLOCKED=RELATIVE_PATH_FORBIDDEN >&2; exit 2; }
WORKDIR="$(realpath -m -- "$WORKDIR")"
STATE_DIR="$(realpath -m -- "$STATE_DIR")"
[[ "$WORKDIR" != "$HOME" && "$WORKDIR" != "$HOME/samsung_AXI" &&
   "$WORKDIR" != / && ! -L "$WORKDIR" ]] ||
  { echo SMARTDISH_D_BLOCKED=UNSAFE_WORKDIR >&2; exit 2; }
mkdir -p "$STATE_DIR"
LOG_FILE="$STATE_DIR/run_$(date -u +%Y%m%dT%H%M%SZ)_$$.log"
exec > >(tee -a "$LOG_FILE") 2>&1
echo "SMARTDISH_D_MODE=$MODE"
echo "SMARTDISH_D_LOG=$LOG_FILE"
fail() {
  echo "SMARTDISH_D_BLOCKED=$1" >&2
  echo "FAILED_STAGE=$STAGE" >&2
  echo "SOURCE_SHA=$SOURCE_SHA" >&2
  echo "NEXT_ACTION=$2" >&2
  exit 2
}
on_error() {
  local rc="$1" line="$2"
  trap - ERR
  echo SMARTDISH_D_BLOCKED=COMMAND_FAILED >&2
  echo "FAILED_STAGE=$STAGE" >&2
  echo "SOURCE_SHA=$SOURCE_SHA" >&2
  echo "FIRST_ERROR_EXIT=$rc LINE=$line" >&2
  echo "NEXT_ACTION=Review the earliest failure in $LOG_FILE" >&2
  exit "$rc"
}
trap 'on_error "$?" "$LINENO"' ERR
STAGE=LOCK
command -v flock >/dev/null || fail MISSING_FLOCK "Install util-linux"
exec 9>"$STATE_DIR/runner.lock"
flock -n 9 || fail RUNNER_ALREADY_ACTIVE "Finish the earlier D invocation"
canonical_origin() {
  local u="$1"
  u="${u%/}"
  u="${u%.git}"
  case "$u" in
    https://github.com/silverbjin/samsung_AXI|git@github.com:silverbjin/samsung_AXI|ssh://git@github.com/silverbjin/samsung_AXI)
      echo github.com/silverbjin/samsung_AXI ;;
    file://*)
      [[ "$TEST_MODE" == 1 ]] || return 1
      echo "$u" ;;
    *) return 1 ;;
  esac
}
STAGE=GIT
for cmd in git realpath awk find; do
  command -v "$cmd" >/dev/null || fail MISSING_TOOL "Install $cmd"
done
expected="$(canonical_origin "$REPO_URL")" || fail UNTRUSTED_ORIGIN "Only the configured repo may be cloned"
export GIT_TERMINAL_PROMPT=0
if [[ -e "$WORKDIR" ]]; then
  [[ -d "$WORKDIR" ]] || fail WORKDIR_NOT_DIRECTORY "Inspect the target path"
  if [[ ! -e "$WORKDIR/.git" ]]; then
    [[ -z "$(find "$WORKDIR" -mindepth 1 -maxdepth 1 -print -quit)" ]] ||
      fail EXISTING_NON_GIT_DIRECTORY "Preserve existing files; inspect $WORKDIR"
    git clone --single-branch --branch "$BRANCH" "$REPO_URL" "$WORKDIR"
  fi
else
  mkdir -p "$(dirname "$WORKDIR")"
  git clone --single-branch --branch "$BRANCH" "$REPO_URL" "$WORKDIR"
fi
[[ "$(git -C "$WORKDIR" rev-parse --is-inside-work-tree)" == true &&
   "$(realpath -m "$(git -C "$WORKDIR" rev-parse --show-toplevel)")" == "$WORKDIR" ]] ||
  fail INVALID_GIT_WORKTREE "Expected the exact D repository root"
remote="$(git -C "$WORKDIR" remote get-url origin)" ||
  fail NO_ORIGIN "Inspect the existing worktree"
actual="$(canonical_origin "$remote")" || fail WRONG_ORIGIN "Do not reuse a different repository"
[[ "$actual" == "$expected" ]] || fail WRONG_ORIGIN "Do not reuse a different repository"
branch_now="$(git -C "$WORKDIR" symbolic-ref --quiet --short HEAD)" ||
  fail DETACHED_HEAD "Manually checkout the D branch without discarding changes"
[[ "$branch_now" == "$BRANCH" ]] || fail WRONG_BRANCH "Review local work and manually select the D branch"
SOURCE_SHA="$(git -C "$WORKDIR" rev-parse --verify HEAD)"
[[ -z "$(git -C "$WORKDIR" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail DIRTY_WORKTREE "Keep local files; commit or stash manually, never reset/clean"
line="$(git -C "$WORKDIR" ls-remote --exit-code --heads "$remote" "refs/heads/$BRANCH")" ||
  fail REMOTE_BRANCH_NOT_FOUND "Check network, origin and branch name"
remote_sha="$(printf '%s\n' "$line" | awk -v r="refs/heads/$BRANCH" '$2==r{print $1}')"
[[ "$remote_sha" =~ ^[a-f0-9]{40}$ ]] ||
  fail REMOTE_BRANCH_NOT_FOUND "Check the branch on GitHub"
[[ "$SOURCE_SHA" == "$remote_sha" ]] ||
  fail REMOTE_HEAD_CHANGED "Inspect fetch manually; never auto merge/rebase/reset"
[[ -z "$REQUIRED_SHA" || "$SOURCE_SHA" == "$REQUIRED_SHA" ]] ||
  fail SOURCE_PIN_MISMATCH "Review the SHA change and update the pinned release"
printf 'SMARTDISH_D_BRANCH=%s\nSOURCE_SHA=%s\n' "$BRANCH" "$SOURCE_SHA"
echo SMARTDISH_D_GIT_PASS

STAGE=SOURCE
cd "$WORKDIR"
for f in src/smartdish_service/package.xml tests/test_smartdish_d_service.py \
         tests/test_smartdish_d_ui.py src/smartdish_service/smartdish_service/ui_app.py; do
  [[ -f "$f" ]] || fail REQUIRED_SOURCE_MISSING "Missing file: $f"
done
echo SMARTDISH_D_SOURCE_PASS
STAGE=ROS_ENV
[[ -f "$ROS_SETUP" ]] || fail ROS_JAZZY_NOT_INSTALLED "Check /opt/ros/jazzy/setup.bash"
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH ROS_PACKAGE_PATH PYTHONPATH
set +u
source "$ROS_SETUP"
set -u
[[ "$TEST_MODE" == 1 || "${ROS_DISTRO:-}" == jazzy ]] ||
  fail WRONG_ROS_DISTRO "Source ROS 2 Jazzy"
for cmd in python3 colcon ros2; do
  command -v "$cmd" >/dev/null || fail MISSING_TOOL "Install $cmd"
done
python3 -m pytest --version >/dev/null ||
  fail MISSING_PYTEST "Install python3-pytest for this Python interpreter"
STAGE=PACKAGE_DISCOVERY
list="$(colcon list --base-paths "$WORKDIR/src" --names-only)" ||
  fail COLCON_DISCOVERY_FAILED "Inspect colcon and package.xml"
printf '%s\n' "$list" | grep -Fxq smartdish_service ||
  fail PACKAGE_NOT_DISCOVERED "Check the D package.xml and checked-out SHA"
echo SMARTDISH_D_PREFLIGHT_PASS
if [[ "$MODE" == --preflight ]]; then
  echo SMARTDISH_D_PREFLIGHT_PASS_NO_GOAL
  exit 0
fi

STAGE=PYTEST
export PYTHONDONTWRITEBYTECODE=1
python3 -m pytest -q -p no:cacheprovider \
    tests/test_smartdish_d_service.py tests/test_smartdish_d_ui.py ||
  fail PYTEST_FAILED "Inspect first pytest failure: $LOG_FILE"
echo SMARTDISH_D_PYTEST_PASS
STAGE=COLCON_BUILD
colcon --log-base "$STATE_DIR/colcon_log" build --base-paths "$WORKDIR/src" \
  --build-base "$STATE_DIR/build" --install-base "$STATE_DIR/install" \
  --packages-select smartdish_service --symlink-install ||
  fail COLCON_BUILD_FAILED "Inspect $STATE_DIR/colcon_log; GUI not started"
echo SMARTDISH_D_BUILD_PASS
STAGE=PACKAGE_INSTALL
[[ -f "$STATE_DIR/install/local_setup.bash" ]] ||
  fail INSTALL_OVERLAY_MISSING "Inspect isolated install tree"
set +u
source "$STATE_DIR/install/local_setup.bash"
set -u
prefix="$(ros2 pkg prefix smartdish_service)" ||
  fail ROS_PACKAGE_NOT_FOUND "Inspect package.xml and install tree"
resolved="$(realpath -m "$prefix")"
[[ "$resolved" == "$STATE_DIR/install/smartdish_service" ||
   "$resolved" == "$STATE_DIR/install" ]] ||
  fail STALE_PACKAGE_PREFIX "Wrong overlay package prefix: $prefix"
exe="$(ros2 pkg executables smartdish_service)" ||
  fail ROS_EXECUTABLES_MISSING "Inspect setup.py console_scripts"
printf '%s\n' "$exe" | grep -Fxq 'smartdish_service smartdish_manager' ||
  fail ROS_MANAGER_MISSING "Inspect setup.py and rebuild"
printf '%s\n' "$exe" | grep -Fxq 'smartdish_service smartdish_ui' ||
  fail ROS_UI_MISSING "Inspect setup.py and rebuild"
echo SMARTDISH_D_PACKAGE_PASS
echo SMARTDISH_D_VERIFY_PASS_NO_GOAL
if [[ "$MODE" == --run-ui ]]; then
  STAGE=GUI_DISPLAY
  [[ -n "${DISPLAY:-}" ]] ||
    fail DISPLAY_UNAVAILABLE "Enable WSLg or an X server and check DISPLAY"
  python3 - <<'PY'
import tkinter as tk
root = tk.Tk()
root.withdraw()
root.update_idletasks()
root.destroy()
PY
  STAGE=GUI_LAUNCH
  echo SMARTDISH_D_UI_LAUNCH_REQUESTED_NO_GOAL
  echo "SMARTDISH_D_UI_READY is emitted only by the Tk mainloop."
  exec ros2 launch smartdish_service smartdish_service.launch.py ai_available:=false
fi
