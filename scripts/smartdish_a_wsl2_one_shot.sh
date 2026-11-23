#!/usr/bin/env bash
# SmartDish A-07 — WSL2 owner real Gazebo Nav2 3-leg, operator TTY consent.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
MODE=--gui
if [[ $# -gt 0 ]]; then MODE="$1"; fi
case "$MODE" in
 --headless) GUI_ARG="" ;;
 --gui) GUI_ARG=--gui ;;
 -h|--help)
   echo 'Usage: bash scripts/smartdish_a_wsl2_one_shot.sh [--gui|--headless]'
   echo 'Default: WSLg --gui. Fallback: --headless. Real Gazebo 3-leg test.'
   echo 'YES-SMARTDISH-A-GOALS entered by operator /dev/tty.'
   exit 0 ;;
 *) echo "INVALID_OPTION=$MODE"; exit 2 ;;
esac
[[ $# -le 1 ]] || exit 2
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVD="$ROOT/generated/smartdish_a_wsl2/$RUN_ID"
mkdir -p "$EVD"
SHA=UNKNOWN
PASSED=0
finish() {
 rc=$?
 trap - EXIT INT TERM
 set +e
 for name in build nav2 adapter console; do
   [[ -f "$EVD/$name.log" ]] || : > "$EVD/$name.log"
   tail -n 350 "$EVD/$name.log" > "$EVD/$name-tail.log"
 done
 [[ -s "$EVD/l3_evidence.json" ]] ||
   printf '{"verdict":"NOT_RUN","first_error":"PRE_RUN_FAILURE"}\n' > "$EVD/l3_evidence.json"
 python3 - "$EVD/l3_evidence.json" "$EVD/summary.json" "$rc" "$SHA" <<'PY'
import json,sys
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
rc=int(sys.argv[3]); passed=rc==0 and d['verdict']=='ROBOT_ONLY_REAL_GAZEBO_WSL2_L3_PASS'
v={'verdict':'PASS' if passed else 'NOT_PASS','exit_code':rc,
   'source_sha':sys.argv[4],'physical_verdict':d['verdict'],
   'first_error':d.get('first_error'),'scope':'A ROBOT_ONLY, NOT D UI'}
Path(sys.argv[2]).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
print('SMARTDISH_A_WSL2_SUMMARY='+json.dumps(v,ensure_ascii=False))
PY
 tar czf "$EVD/smartdish_a_owner_evidence.tar.gz" -C "$EVD" \
   summary.json l3_evidence.json build-tail.log nav2-tail.log \
   adapter-tail.log console-tail.log 2>/dev/null
 echo "SMARTDISH_A_WSL2_EVIDENCE_BUNDLE=$EVD/smartdish_a_owner_evidence.tar.gz"
 if [[ "$rc" == 0 && "$PASSED" == 1 ]]; then
   echo SMARTDISH_A_WSL2_OWNER_L3_PASS
 else
   echo "SMARTDISH_A_WSL2_OWNER_L3_NOT_PASS rc=$rc"
 fi
 exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT TERM
block() { echo "SMARTDISH_A_WSL2_BLOCKED_NO_GOAL: $*" >&2; exit 2; }
[[ -n "$(printenv WSL_DISTRO_NAME)" ]] || block 'Run in WSL2 Ubuntu, not PowerShell.'
grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || block 'WSL2 kernel required.'
[[ -t 0 && -r /dev/tty && -w /dev/tty ]] || block 'Interactive /dev/tty required.'
case "$ROOT" in /mnt/*) block 'Clone into WSL2 ext4, not /mnt/c.' ;; esac
[[ -r /opt/ros/jazzy/setup.bash ]] || block 'ROS 2 Jazzy missing.'
for cmd in git colcon python3 gz; do command -v "$cmd" >/dev/null || block "Missing $cmd"; done
[[ "$(git -C "$ROOT" branch --show-current)" == feat/smartdish-a-robot ]] ||
  block 'Use feat/smartdish-a-robot branch, not main.'
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] ||
  block 'Tracked files are modified; commit or stash first.'
SHA="$(git -C "$ROOT" rev-parse HEAD)"
export RESTAURANT_ROOT="$ROOT" TURTLEBOT3_MODEL=waffle_pi
if [[ -z "$(printenv ROS_DOMAIN_ID)" ]]; then export ROS_DOMAIN_ID="$((60 + $$ % 35))"; fi
if [[ -z "$(printenv GZ_PARTITION)" ]]; then export GZ_PARTITION="smartdish_a_owner_$RUN_ID"; fi
echo "SMARTDISH_A_WSL2_SOURCE_SHA=$SHA"
echo "SMARTDISH_A_WSL2_ISOLATION=$ROS_DOMAIN_ID/$GZ_PARTITION"
set +u
source /opt/ros/jazzy/setup.bash
set -u
for pkg in ros_gz_sim ros_gz_bridge ros_gz_image nav2_bringup nav2_simple_commander slam_toolbox; do
 ros2 pkg prefix "$pkg" >/dev/null 2>&1 || block "Missing ROS package $pkg"
done
python3 -c 'import yaml' || block 'Install python3-yaml.'
if [[ "$MODE" == --gui && -z "$(printenv DISPLAY)$(printenv WAYLAND_DISPLAY)" ]]; then
 block 'WSLg DISPLAY is required for --gui.'
fi
UPSTREAM="$ROOT/src/upstream/turtlebot3_simulations"
PIN=45633014a14e8f438495b532a723e4ad45cbbd31
if [[ ! -d "$UPSTREAM/.git" ]]; then
 mkdir -p "$ROOT/src/upstream"
 git clone -q --depth 1 -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git "$UPSTREAM" ||
   block 'ROBOTIS upstream clone failed.'
fi
[[ "$(git -C "$UPSTREAM" remote get-url origin)" == https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git ]] ||
 block 'Unexpected ROBOTIS origin.'
[[ -z "$(git -C "$UPSTREAM" status --porcelain --untracked-files=normal)" ]] ||
 block 'Upstream source is modified.'
if [[ "$(git -C "$UPSTREAM" rev-parse HEAD)" != "$PIN" ]]; then
 git -C "$UPSTREAM" fetch -q --depth 1 origin "$PIN"
 git -C "$UPSTREAM" checkout -q --detach "$PIN"
fi
[[ "$(git -C "$UPSTREAM" rev-parse HEAD)" == "$PIN" ]] || block 'Wrong ROBOTIS PIN.'
PYTHONPATH="$ROOT/scripts" python3 - "$ROOT" <<'PY' || block 'Map custody or Pose mismatch.'
import sys,yaml
from pathlib import Path
from s3_map_contract import validate_s2_map03_candidate
root=Path(sys.argv[1])
validate_s2_map03_candidate(root)
d=yaml.safe_load((root/'src/smartdish_robot/config/table_poses.yaml').read_text())
assert d['frame']=='map'
assert [(d['poses'][k]['x'],d['poses'][k]['y']) for k in ('HOME','T03','DISH_RETURN')]==[
 (0.0,0.0),(5.25,0.38),(-1.15,1.60)]
print('SMARTDISH_A_WSL2_MAP_CUSTODY_PASS_NO_GOAL')
PY
cd "$ROOT"
echo SMARTDISH_A_WSL2_COLCON_START_NO_GOAL
colcon build --symlink-install --event-handlers console_direct+ \
 --packages-up-to restaurant_world restaurant_bringup restaurant_delivery smartdish_robot \
 >"$EVD/build.log" 2>&1 ||
 { tail -n 50 "$EVD/build.log"; block 'Colcon build failed.'; }
set +u
source "$ROOT/install/setup.bash"
set -u
ros2 pkg executables smartdish_robot | grep -qx 'smartdish_robot navigation_adapter' ||
 block 'A NavigationAdapter executable missing.'
echo SMARTDISH_A_WSL2_BUILD_PASS_NO_GOAL
SDF="$EVD/waffle_pi_rgbd.sdf"
PARAMS="$EVD/nav2_params.yaml"
SRC="$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/models/turtlebot3_waffle_pi/model.sdf"
NAV_SRC="$(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/params/nav2_params.yaml"
python3 scripts/prepare_waffle_rgbd.py --source "$SRC" --out "$SDF" --rgbd-rate-hz 2 ||
 block 'Failed to make official Waffle Pi SDF overlay.'
python3 scripts/prepare_nav2_params.py --source "$NAV_SRC" --out "$PARAMS" \
 --auto-initial-pose --s6-bt-ack-ms 200 || block 'Nav2 params overlay failed.'
echo SMARTDISH_A_WSL2_REAL_GAZEBO_L3_START
# GUI_ARG expands to zero words for headless, or a single --gui when requested.
python3 -u scripts/smartdish_a_wsl2_l3.py --source-sha "$SHA" \
 --robot-sdf "$SDF" --map "$ROOT/maps/candidates/s2_map03/restaurant_map.yaml" \
 --params "$PARAMS" --poses "$ROOT/src/smartdish_robot/config/table_poses.yaml" \
 --launch-log "$EVD/nav2.log" --adapter-log "$EVD/adapter.log" \
 --evidence "$EVD/l3_evidence.json" $GUI_ARG 2>&1 | tee "$EVD/console.log"
python3 - "$EVD/l3_evidence.json" "$SHA" <<'PY' || block 'Invalid L3 evidence.'
import sys,json
from pathlib import Path
d=json.loads(Path(sys.argv[1]).read_text())
assert d['source_sha']==sys.argv[2]
assert d['verdict']=='ROBOT_ONLY_REAL_GAZEBO_WSL2_L3_PASS'
assert [x['leg'] for x in d['legs']]==['TO_TABLE','TO_RETURN','TO_HOME']
assert [x['result'] for x in d['nav_results']]==['SUCCEEDED']*3
assert all(x['odom_max_m']>=.25 and x['scan_count']>=3 for x in d['legs'])
print('SMARTDISH_A_WSL2_EVIDENCE_VERIFIED')
PY
PASSED=1
