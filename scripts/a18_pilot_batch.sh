#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PIN="$1"; OUT="$(realpath -m "$2")"; MODE="${3:---gui}"; PHASE="${4:-1}"; PRIOR="${5:-}"
[[ "$PHASE" == 1 || "$PHASE" == 2 ]] || exit 2
[[ "$MODE" == --gui || "$MODE" == --headless || "$MODE" == --ci ]] || exit 2
[[ "$MODE" != --ci || "${CI:-}" == true ]] || exit 2
[[ ! -e "$OUT" ]] || { echo A18_OUTPUT_EXISTS; exit 2; }
mkdir -p "$OUT"
finish(){
  local rc=$?;trap - EXIT
  python3 "$ROOT/scripts/a18_archive.py" "$OUT" "$PIN" "$MODE" "$rc" "$PHASE" || { echo A18_PACKAGING_FAILED; exit 2; }
  exit "$rc"
}
trap finish EXIT
cd "$ROOT"
export SMARTDISH_A18_BATCH_ID="$(python3 -c 'import uuid;print(uuid.uuid4().hex)')"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && "$(git rev-parse HEAD)" == "$PIN" ]] || exit 2
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || exit 2
BASE=b8ef3998973a5e33b67ddd5c5b63c3c89b837840
# Shallow owner clone uses pinned source and compares protected content against
# a separately fetched exact platform commit; ancestry checked in CI/full clone.
if [[ "$(git rev-parse --is-shallow-repository)" == true ]];then
 git fetch --no-tags --depth=1 origin "$BASE"
 git diff --quiet "$BASE" "$PIN" -- scripts/smartdish_platform scripts/smartdish_platform_bootstrap.sh tests/platform config/smartdish_platform_baseline.json config/smartdish_regression_ledger.json .github/workflows/smartdish-platform-ci.yml
else
 python3 scripts/smartdish_platform/baseline.py --baseline "$BASE"
fi
if [[ "$PHASE" == 2 ]];then
 python3 scripts/a18_phase_gate.py "$ROOT" "$PIN" "$MODE" "$PRIOR" "$OUT/phase_gate.json"
fi
set +u
source /opt/ros/jazzy/setup.bash
set -u
python3 - "$OUT" "$PIN" "$MODE" <<'PY'
import json,os,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1])
def cmd(*args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=15)
    return {"rc":r.returncode,"stdout":r.stdout[-8000:],"stderr":r.stderr[-2000:]}
d={"source_sha":sys.argv[2],"actual_head":cmd("git","rev-parse","HEAD"),"tracked_clean":cmd("git","status","--porcelain","--untracked-files=no"),"platform_sha":"b8ef3998973a5e33b67ddd5c5b63c3c89b837840","producer_version":"SMARTDISH_A18_V1","mode":sys.argv[3],"ros_distro":os.environ.get("ROS_DISTRO"),"gz_version":cmd("gz","sim","--versions"),"ros_contact_type":cmd("ros2","interface","show","ros_gz_interfaces/msg/Contacts"),"ros_image_type":cmd("ros2","interface","show","sensor_msgs/msg/Image"),"renderer":{k:os.environ.get(k) for k in ("GALLIUM_DRIVER","MESA_D3D12_DEFAULT_ADAPTER_NAME","LIBGL_ALWAYS_SOFTWARE","QT_QPA_PLATFORM")} }
(p/"preflight.json").write_text(json.dumps(d,indent=2)+"\n")
if d["ros_distro"]!="jazzy" or d["gz_version"]["stdout"].strip()!="8.15.0" or any(d[k]["rc"] for k in ("gz_version","ros_contact_type","ros_image_type")):raise SystemExit(2)
PY
timeout 120s cmake -S scripts/a16_pilot -B "$OUT/build_pose" > "$OUT/build_pose.log" 2>&1
timeout 180s cmake --build "$OUT/build_pose" -j2 >> "$OUT/build_pose.log" 2>&1 || { tail -80 "$OUT/build_pose.log"; exit 2; }
timeout 120s cmake -S scripts/a14_physics_freshness -B "$OUT/build_health" > "$OUT/build_health.log" 2>&1
timeout 180s cmake --build "$OUT/build_health" -j2 >> "$OUT/build_health.log" 2>&1 || { tail -80 "$OUT/build_health.log"; exit 2; }
ORDER="$(PYTHONPATH=scripts python3 -c 'import sys;from a18_pilot_world import phase_scenes;print(" ".join(phase_scenes(int(sys.argv[1]))))' "$PHASE")"
read -r -a SCENES <<< "$ORDER"
[[ ${#SCENES[@]} == 4 ]] || exit 2
for scene in "${SCENES[@]}"; do
 args=(); cls=OWNER_WSL2; profile=wsl_d3d12_retention_v1
 if [[ "$MODE" == --ci ]];then cls=CLOUD_CI;profile=inherit;fi
 if [[ "$MODE" == --headless || ( "$MODE" == --ci && "$scene" != "${SCENES[0]}" ) ]];then args=(--headless);fi
 timeout --signal=INT --kill-after=35s 420s python3 -u scripts/a18_pilot_collect.py --sha "$PIN" --scene "$scene" \
   --out "$OUT/$scene" --pose-plugin "$OUT/build_pose/liba16_pilot.so" --health-plugin "$OUT/build_health/liba14_physics_freshness.so" \
   --native-tap "$OUT/build_pose/a16_native_contact" --source-class "$cls" --server-profile "$profile" "${args[@]}" 2>&1 | tee "$OUT/$scene.log"
done
PYTHONPATH=scripts python3 - "$OUT" "$PHASE" <<'PY'
import json,sys
from pathlib import Path
from a18_pilot_world import phase_scenes
p=Path(sys.argv[1]);phase=int(sys.argv[2]);rows=[]
for s in phase_scenes(phase):
 d=json.loads((p/s/"a18_design.json").read_text());v=json.loads((p/s/"verdict.json").read_text())
 assert v["data_verdict"]=="PASS" and v["cleanup"]=="PASS" and v["all_owned_stopped"] and not v["human_approved"]
 upper=d["initial_dishes"][-1]["name"];m=v["metrics"][upper];disp=m["max_relative_displacement_m"]
 row={"scene":s,"family":d["geometry_family_id"],"layout":d["physical_layout_id"],"comparison_fingerprint":d["comparison_fingerprint"],"center_group":d["upper_tray_center_group"],"support_offset_x_m":d["upper_support_offset_x_m"],"center_margin_m":d["nominal_center_support_margin_m"],"containment_margin_m":d["nominal_full_containment_margin_m"],"max_displacement_m":disp,"path_m":m["cumulative_relative_path_m"],"observation":"POSITION_MAINTAINED" if disp<=1e-8 else "LARGE_DISPLACEMENT" if disp>=.1 else "OTHER_OBSERVED","gui":v["gui"],"cleanup":v["cleanup"],"production_profile_cleanup":v.get("server_runtime_profile",{}).get("production_cleanup","NOT_REQUESTED")}
 rows.append(row);print("A18_OBSERVED="+json.dumps(row))
assert len({r["comparison_fingerprint"] for r in rows})==4
(p/"contrast.json").write_text(json.dumps({"scope":"DESCRIPTIVE_ONLY_NOT_GT","phase":phase,"rows":rows,"human_approved":False,"training_eligible":False},indent=2,sort_keys=True)+"\n")
print(f"A18_PHASE{phase}_DATA_CAPTURE_4_OF_4_GT_HOLD")
PY
PYTHONPATH=scripts python3 scripts/a18_review_outputs.py "$OUT" "$PHASE"
