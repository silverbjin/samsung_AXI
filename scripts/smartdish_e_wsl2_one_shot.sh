#!/usr/bin/env bash
# E real GUI integration; user clicks T03, A alone owns NavigateToPose.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
MODE=--gui
if (( $# > 0 )); then MODE="$1"; fi
case "$MODE" in
  --gui) : ;;
  --headless) echo SMARTDISH_E_HEADLESS_PREFLIGHT_ONLY_NO_GOAL; exit 0 ;;
  --help|-h) echo "Usage: bash scripts/smartdish_e_wsl2_one_shot.sh [--gui|--headless]"; exit 0 ;;
  *) echo SMARTDISH_E_INVALID_MODE; exit 2 ;;
esac
(( $# <= 1 )) || exit 2
RUN="$(date -u +%Y%m%dT%H%M%SZ)-$$"
EVD="$ROOT/generated/smartdish_e/$RUN"
mkdir -p "$EVD"
SHA="$(git -C "$ROOT" rev-parse HEAD)"
STAGE=INIT
ERROR=""
PASS=0
NAV="" ADAPTER="" SERVICE="" WITNESS=""
fail() { ERROR="$1"; echo "SMARTDISH_E_FIRST_FAILURE stage=$STAGE code=$ERROR" >&2; exit 2; }
alive() { [[ -n "$1" ]] && kill -0 "$1" 2>/dev/null; }
stop() {
  local pid="$1" group="$2"
  [[ -n "$pid" ]] || return 0
  if alive "$pid"; then
    if [[ "$group" == yes ]]; then kill -INT -- "-$pid" 2>/dev/null || :; else kill -INT "$pid" 2>/dev/null || :; fi
    sleep 1
    if alive "$pid"; then
      if [[ "$group" == yes ]]; then kill -TERM -- "-$pid" 2>/dev/null || :; else kill -TERM "$pid" 2>/dev/null || :; fi
    fi
  fi
  wait "$pid" 2>/dev/null || :
}
finish() {
  local rc=$?
  trap - EXIT INT TERM
  set +e
  stop "$SERVICE" yes
  stop "$ADAPTER" no
  stop "$NAV" yes
  stop "$WITNESS" no
  [[ -s "$EVD/live_evidence.json" ]] || printf '{"verdict":"NOT_RUN","first_error":"PRE_RUN_FAILURE"}\n' >"$EVD/live_evidence.json"
  python3 - "$EVD" "$SHA" "$rc" "$PASS" "$STAGE" "$ERROR" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); d=json.loads((p/"live_evidence.json").read_text())
ok=sys.argv[4]=="1" and int(sys.argv[3])==0
s={"source_sha":sys.argv[2],"verdict":"AI_OFF_REAL_RUN_PASS" if ok else "HOLD",
"WSL2_L3":"PASS" if ok else "NOT_PASS_OR_NOT_RUN",
"first_error":d.get("first_error") or sys.argv[6] or "UNVERIFIED",
"stage":sys.argv[5],"exit_code":int(sys.argv[3]),
"request_id":d.get("request_id"),"nav_result_count":len(d.get("results",[])),
"ui_applied_completed":ok}
(p/"summary.json").write_text(json.dumps(s,indent=2,ensure_ascii=False)+"\n")
print("SMARTDISH_E_SUMMARY="+json.dumps(s,ensure_ascii=False))
PY
  for f in build observer nav2 adapter service; do
    [[ -f "$EVD/$f.log" ]] || : >"$EVD/$f.log"
    tail -n 300 "$EVD/$f.log" >"$EVD/$f-tail.log"
  done
  tar -czf "$EVD/smartdish_e_owner_evidence.tar.gz" -C "$EVD" \
    summary.json live_evidence.json build-tail.log observer-tail.log \
    nav2-tail.log adapter-tail.log service-tail.log 2>/dev/null || :
  echo "SMARTDISH_E_EVIDENCE=$EVD/smartdish_e_owner_evidence.tar.gz"
  if [[ "$PASS" == 1 && "$rc" == 0 ]]; then echo SMARTDISH_E_AI_OFF_WSL2_L3_PASS
  else echo SMARTDISH_E_AI_OFF_WSL2_L3_HOLD; fi
  exit "$rc"
}
trap finish EXIT
trap 'ERROR=OPERATOR_INTERRUPTED; exit 130' INT TERM
STAGE=PREFLIGHT
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] || fail WSL2_REQUIRED
grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || fail WSL2_KERNEL_REQUIRED
[[ -t 0 && -r /dev/tty && -w /dev/tty ]] || fail INTERACTIVE_TTY_REQUIRED
case "$ROOT" in /mnt/*) fail WSL_EXT4_REQUIRED ;; esac
[[ -f /opt/ros/jazzy/setup.bash ]] || fail ROS_JAZZY_MISSING
for cmd in git colcon ros2 gz python3 setsid; do command -v "$cmd" >/dev/null || fail "MISSING_$cmd"; done
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || fail BAD_SOURCE_SHA
PIN="$(printenv SMARTDISH_E_EXPECTED_SHA || :)"
[[ -z "$PIN" || "$SHA" == "$PIN" ]] || fail SOURCE_SHA_MISMATCH
[[ "$(git -C "$ROOT" remote get-url origin)" == https://github.com/silverbjin/samsung_AXI.git ]] || fail GIT_ORIGIN_MISMATCH
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || fail GIT_TRACKED_DIRTY
[[ -n "$(printenv DISPLAY || :)$(printenv WAYLAND_DISPLAY || :)" ]] || fail WSLG_DISPLAY_MISSING
export RESTAURANT_ROOT="$ROOT" TURTLEBOT3_MODEL=waffle_pi
if [[ -z "$(printenv ROS_DOMAIN_ID || :)" ]]; then export ROS_DOMAIN_ID="$((60 + $$ % 35))"; fi
if [[ -z "$(printenv GZ_PARTITION || :)" ]]; then export GZ_PARTITION="smartdish_e_$RUN"; fi
echo "SMARTDISH_E_SOURCE_SHA=$SHA"
echo "SMARTDISH_E_ISOLATION=$ROS_DOMAIN_ID/$GZ_PARTITION"
set +u
source /opt/ros/jazzy/setup.bash
set -u
for pkg in ros_gz_sim ros_gz_bridge ros_gz_image nav2_bringup nav2_simple_commander slam_toolbox; do
  ros2 pkg prefix "$pkg" >/dev/null 2>&1 || fail "ROS_PACKAGE_MISSING_$pkg"
done
python3 -c 'import yaml; import pytest' || fail PYTHON_REQUIREMENTS_MISSING
STAGE=UPSTREAM
UPSTREAM="$ROOT/src/upstream/turtlebot3_simulations"
UP_PIN=45633014a14e8f438495b532a723e4ad45cbbd31
if [[ ! -d "$UPSTREAM/.git" ]]; then
  mkdir -p "$ROOT/src/upstream"
  git clone --quiet --depth 1 -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git "$UPSTREAM" || fail ROBOTIS_CLONE_FAILED
fi
[[ "$(git -C "$UPSTREAM" remote get-url origin)" == https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git ]] || fail ROBOTIS_ORIGIN_MISMATCH
[[ -z "$(git -C "$UPSTREAM" status --porcelain --untracked-files=normal)" ]] || fail ROBOTIS_DIRTY
if [[ "$(git -C "$UPSTREAM" rev-parse HEAD)" != "$UP_PIN" ]]; then
  git -C "$UPSTREAM" fetch --quiet --depth 1 origin "$UP_PIN" || fail ROBOTIS_FETCH_FAILED
  git -C "$UPSTREAM" checkout --quiet --detach "$UP_PIN" || fail ROBOTIS_CHECKOUT_FAILED
fi
STAGE=MAP
PYTHONPATH="$ROOT/scripts" python3 - "$ROOT" <<'PY' || fail S7_MAP_OR_A_POSES_MISMATCH
import sys,yaml
from pathlib import Path
from s3_map_contract import validate_s2_map03_candidate
root=Path(sys.argv[1]); validate_s2_map03_candidate(root)
p=yaml.safe_load((root/'src/smartdish_robot/config/table_poses.yaml').read_text())
assert p["frame"]=="map"
assert {k:(p["poses"][k]["x"],p["poses"][k]["y"]) for k in ('HOME','T03','DISH_RETURN')}=={
'HOME':(0.,0.),'T03':(5.25,.38),'DISH_RETURN':(-1.15,1.60)}
print("SMARTDISH_E_MAP_POSES_PASS_NO_GOAL")
PY
STAGE=TEST_BUILD
cd "$ROOT"
python3 -m pytest -q tests/test_smartdish_a_contract.py tests/test_smartdish_d_service.py \
  tests/test_smartdish_d_ui.py tests/test_smartdish_e_contract.py >"$EVD/build.log" 2>&1 || fail CONTRACT_PYTEST_FAILED
colcon build --symlink-install --packages-up-to restaurant_world restaurant_bringup \
  restaurant_delivery smartdish_robot smartdish_service >>"$EVD/build.log" 2>&1 || fail COLCON_BUILD_FAILED
set +u
source "$ROOT/install/setup.bash"
set -u
for pkgexe in "smartdish_robot navigation_adapter" "smartdish_service smartdish_manager" "smartdish_service smartdish_ui"; do
  ros2 pkg executables "$(echo "$pkgexe" | cut -d' ' -f1)" | grep -Fxq "$pkgexe" || fail ROS_ENTRYPOINT_MISSING
done
SRC="$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/models/turtlebot3_waffle_pi/model.sdf"
NAV_SRC="$(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/params/nav2_params.yaml"
SDF="$EVD/waffle_pi_rgbd.sdf"
PARAMS="$EVD/nav2_params.yaml"
python3 scripts/prepare_waffle_rgbd.py --source "$SRC" --out "$SDF" --rgbd-rate-hz 2 >>"$EVD/build.log" 2>&1 || fail SDF_OVERLAY_FAILED
python3 scripts/prepare_nav2_params.py --source "$NAV_SRC" --out "$PARAMS" --auto-initial-pose --s6-bt-ack-ms 200 >>"$EVD/build.log" 2>&1 || fail NAV2_OVERLAY_FAILED
echo SMARTDISH_E_BUILD_PASS_NO_GOAL
marker() {
  local file="$1" needle="$2" pid="$3" limit="$4" until
  until=$((SECONDS+limit))
  while (( SECONDS < until )); do
    alive "$pid" || fail "PROCESS_EXIT_BEFORE_$needle"
    if [[ -f "$file" ]] && grep -Fq "$needle" "$file"; then return 0; fi
    sleep 1
  done
  fail "TIMEOUT_$needle"
}
STAGE=OBSERVER
python3 -u scripts/smartdish_e_live_witness.py --source-sha "$SHA" \
  --evidence "$EVD/live_evidence.json" --timeout 1100 >"$EVD/observer.log" 2>&1 &
WITNESS=$!
marker "$EVD/observer.log" SMARTDISH_E_OBSERVER_READY_NO_GOAL "$WITNESS" 35
STAGE=NAV2
setsid ros2 launch restaurant_bringup navigation.launch.py gui:=true \
  s6_stagger_nav_start:=true robot_sdf:="$SDF" \
  map:="$ROOT/maps/candidates/s2_map03/restaurant_map.yaml" \
  params_file:="$PARAMS" >"$EVD/nav2.log" 2>&1 &
NAV=$!
sleep 3
alive "$NAV" || fail NAV2_LAUNCH_EXITED
STAGE=ADAPTER_TTY
echo "SMARTDISH_E_TTY_APPROVAL: type YES-SMARTDISH-A-GOALS only after world check"
EXE="$(ros2 pkg prefix smartdish_robot)/lib/smartdish_robot/navigation_adapter"
"$EXE" --ros-args -p goals_enabled:=true -p set_initial_home:=false \
 -p "poses_file:=$ROOT/src/smartdish_robot/config/table_poses.yaml" >"$EVD/adapter.log" 2>&1 &
ADAPTER=$!
marker "$EVD/adapter.log" SMARTDISH_A_READY "$ADAPTER" 440
STAGE=D_UI
setsid ros2 launch smartdish_service smartdish_service.launch.py ai_available:=false >"$EVD/service.log" 2>&1 &
SERVICE=$!
marker "$EVD/service.log" SMARTDISH_D_UI_READY "$SERVICE" 80
echo "SMARTDISH_E_CLICK_T03_IN_WSLG_NOW: 10s/5s, AI OFF"
STAGE=LIVE_NAV_UI
if wait "$WITNESS"; then WITNESS=""; else fail LIVE_OBSERVER_FAILED; fi
alive "$SERVICE" || fail D_SERVICE_EXITED
alive "$ADAPTER" || fail A_ADAPTER_EXITED
STAGE=UI_APPLIED
REQ="$(python3 - "$EVD/live_evidence.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert x["verdict"]=="AI_OFF_LIVE_TRACE_PASS_UI_LOG_PENDING"
print(x["request_id"])
PY
)" || fail EVIDENCE_INVALID
marker "$EVD/service.log" "SMARTDISH_D_UI_APPLIED request_id=$REQ state=COMPLETED" "$SERVICE" 20
grep -Fq "SMARTDISH_D_UI_CLICK request_id=$REQ table_id=T03" "$EVD/service.log" || fail UI_CLICK_NOT_CONFIRMED
python3 - "$EVD/live_evidence.json" <<'PY' || fail FINAL_EVIDENCE_INVALID
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);d=json.loads(p.read_text())
assert len(d["results"])==3 and all(x["result"]=="SUCCEEDED" for x in d["results"])
d["verdict"]="AI_OFF_REAL_RUN_PASS";d["ui_applied_completed"]=True
p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n")
PY
python3 - "$EVD" "$REQ" <<'PY' || fail ADAPTER_MANAGER_ORIGIN_NOT_PROVEN
import json,sys
from pathlib import Path
d=Path(sys.argv[1]); rid=sys.argv[2]
expected=["TO_TABLE","TO_RETURN","TO_HOME"]
def events(file,marker):
    out=[]
    for line in (d/file).read_text(errors="replace").splitlines():
        if marker in line:
            try: out.append(json.loads(line.split(marker,1)[1]))
            except (ValueError,TypeError): pass
    return [x for x in out if x.get("request_id")==rid]
a_goals=events("adapter.log","SMARTDISH_A_NAV_GOAL_SENT ")
a_results=events("adapter.log","SMARTDISH_A_NAV_RESULT ")
d_goals=events("service.log","SMARTDISH_D_EVENT topic=/collection/nav_goal json=")
assert [x.get("leg") for x in a_goals]==expected, "ADAPTER_NAV2_GOAL_3_NOT_PROVEN"
assert [x.get("leg") for x in a_results]==expected, "ADAPTER_RESULT_3_NOT_PROVEN"
assert [x.get("leg") for x in d_goals]==expected, "D_MANAGER_GOAL_3_NOT_PROVEN"
assert all(x.get("result")=="SUCCEEDED" and x.get("reason")=="" and
           x.get("odom_max_displacement_m",0)>=.25 for x in a_results)
print("SMARTDISH_E_ORIGIN_CROSSCHECK_PASS request_id="+rid,flush=True)
PY
PASS=1
echo SMARTDISH_E_AI_OFF_LIVE_VERIFIED
