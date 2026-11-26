#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PIN="$1"; OUT="$(realpath -m "$2")"; MODE="${3:---gui}"
[[ "$MODE" == --gui || "$MODE" == --headless || "$MODE" == --ci ]] || exit 2
[[ "$MODE" != --ci || "${CI:-}" == true ]] || exit 2
[[ ! -e "$OUT" ]] || { echo A16_OUTPUT_EXISTS; exit 2; }
mkdir -p "$OUT"
finish(){
  local rc=$?;trap - EXIT
  python3 "$ROOT/scripts/a16_archive.py" "$OUT" "$PIN" "$MODE" "$rc" || { echo A16_PACKAGING_FAILED; exit 2; }
  exit "$rc"
}
trap finish EXIT
cd "$ROOT"
export SMARTDISH_A16_BATCH_ID="$(python3 -c 'import uuid;print(uuid.uuid4().hex)')"
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
d={"source_sha":sys.argv[2],"actual_head":cmd("git","rev-parse","HEAD"),"tracked_clean":cmd("git","status","--porcelain","--untracked-files=no"),"platform_sha":"b8ef3998973a5e33b67ddd5c5b63c3c89b837840","producer_version":"SMARTDISH_A16_V1","mode":sys.argv[3],"ros_distro":os.environ.get("ROS_DISTRO"),"gz_version":cmd("gz","sim","--versions"),"ros_contact_type":cmd("ros2","interface","show","ros_gz_interfaces/msg/Contacts"),"ros_image_type":cmd("ros2","interface","show","sensor_msgs/msg/Image"),"renderer":{k:os.environ.get(k) for k in ("GALLIUM_DRIVER","MESA_D3D12_DEFAULT_ADAPTER_NAME","LIBGL_ALWAYS_SOFTWARE","QT_QPA_PLATFORM")} }
(p/"preflight.json").write_text(json.dumps(d,indent=2)+"\n")
if d["ros_distro"]!="jazzy" or any(d[k]["rc"] for k in ("gz_version","ros_contact_type","ros_image_type")):raise SystemExit(2)
PY
timeout 120s cmake -S scripts/a16_pilot -B "$OUT/build_pose" > "$OUT/build_pose.log" 2>&1
timeout 180s cmake --build "$OUT/build_pose" -j2 >> "$OUT/build_pose.log" 2>&1 || { tail -80 "$OUT/build_pose.log"; exit 2; }
timeout 120s cmake -S scripts/a14_physics_freshness -B "$OUT/build_health" > "$OUT/build_health.log" 2>&1
timeout 180s cmake --build "$OUT/build_health" -j2 >> "$OUT/build_health.log" 2>&1 || { tail -80 "$OUT/build_health.log"; exit 2; }
for scene in L16-01 L16-02 L16-03 L16-04 L16-05 L16-06 L16-07 L16-08; do
 args=(); cls=OWNER_WSL2
 if [[ "$MODE" == --ci ]];then cls=CLOUD_CI;fi
 if [[ "$MODE" == --headless || ( "$MODE" == --ci && "$scene" != L16-01 ) ]];then args=(--headless);fi
 timeout --signal=INT --kill-after=35s 420s python3 -u scripts/a16_pilot_collect.py --sha "$PIN" --scene "$scene" \
   --out "$OUT/$scene" --pose-plugin "$OUT/build_pose/liba16_pilot.so" --health-plugin "$OUT/build_health/liba14_physics_freshness.so" \
   --native-tap "$OUT/build_pose/a16_native_contact" --source-class "$cls" "${args[@]}" 2>&1 | tee "$OUT/$scene.log"
done
# Separate diagnostic only once, no repeated loaded-domain simulation.
timeout --signal=INT --kill-after=25s 130s python3 -u scripts/a16_cleanup_probe.py "$ROOT" "$OUT"
python3 - "$OUT" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);rows=[]
for s in [f"L16-{i:02d}" for i in range(1,9)]:
 d=json.loads((p/s/"a16_design.json").read_text());v=json.loads((p/s/"verdict.json").read_text())
 assert v["data_verdict"]=="PASS" and v["all_owned_stopped"] and not v["human_approved"]
 upper=d["initial_dishes"][-1]["name"];m=v["metrics"][upper]
 row={"scene":s,"family":d["geometry_family_id"],"layout":d["physical_layout_id"],"center_group":d["upper_tray_center_group"],"support_offset_x_m":d["upper_support_offset_x_m"],"margin_m":d["nominal_support_margin_m"],"max_displacement_m":m["max_relative_displacement_m"],"path_m":m["cumulative_relative_path_m"],"gui":v["gui"],"cleanup":v["cleanup"]}
 rows.append(row);print("A16_OBSERVED="+json.dumps(row))
# Report whether contrasting responses exist, do not label or discard cases.
def contrast(xs):
 vals=[x["max_displacement_m"] for x in xs]
 return {"min_m":min(vals),"max_m":max(vals),"span_m":max(vals)-min(vals),"pilot_contrast_observed":min(vals)<=.01 and max(vals)>=.025}
families={x["family"] for x in rows}
res={"scope":"EXPLORATORY_CONTRAST_NOT_GT","rows":rows,"by_family":{f:contrast([x for x in rows if x["family"]==f]) for f in families},"by_center_group":{g:contrast([x for x in rows if x["center_group"]==g]) for g in ("CENTER","ECCENTRIC")},"human_approved":False}
res["shortcut_review"]="REVIEW_REQUIRED" if not all(v["pilot_contrast_observed"] for v in [*res["by_family"].values(),*res["by_center_group"].values()]) else "CROSSED_CONTRAST_OBSERVED_HUMAN_REVIEW_REQUIRED"
(p/"contrast.json").write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
print("A16_SHORTCUT_REVIEW="+res["shortcut_review"])
print("A16_DATA_CAPTURE_8_OF_8_GT_HOLD")
PY
