#!/usr/bin/env bash
# Fixed pilot: no automatic retry or label generation. Existing workspaces untouched.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PIN="$1"; OUT="$(realpath -m "$2")"; MODE="${3:---gui}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] || exit 2
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || exit 2
[[ "$MODE" == --gui || "$MODE" == --headless || "$MODE" == --ci ]] || exit 2
[[ "$MODE" != --ci || "${CI:-}" == true ]] || exit 2
[[ ! -e "$OUT" ]] || { echo A15_OUTPUT_EXISTS; exit 2; }
mkdir -p "$OUT"
finish(){
 local rc=$?; trap - EXIT
 python3 - "$OUT" "$PIN" "$rc" <<'PY'
import hashlib,json,sys,tarfile
from pathlib import Path
p=Path(sys.argv[1]); pin=sys.argv[2]; rc=int(sys.argv[3])
def sha(f):
    with f.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
scenes={}
for s in ('L15-01','L15-02','L15-03','L15-04'):
    d=p/s
    v=d/'verdict.json'
    scenes[s]=json.loads(v.read_text()) if v.is_file() else {'data_verdict':'NOT_RUN'}
(p/'batch_status.json').write_text(json.dumps(dict(source_sha=pin,exit_code=rc,scenes=scenes,ground_truth='UNKNOWN_HOLD',human_approved=False),indent=2)+'\n')
files=[p/'batch_status.json']
for f in sorted(p.glob('*.log')):files.append(f)
for s in scenes:
    d=p/s
    for name in ('a15_raw.tar.gz','a15_raw.tar.gz.sha256'):
        if (d/name).is_file():files.append(d/name)
sums=p/'SHA256SUMS';sums.write_text(''.join(sha(f)+'  '+f.relative_to(p).as_posix()+'\n' for f in files))
bundle=p/'a15_pilot_evidence.tar.gz'
with tarfile.open(bundle,'x:gz') as t:
    for f in files+[sums]:t.add(f,arcname=f.relative_to(p).as_posix(),recursive=False)
(p/(bundle.name+'.sha256')).write_text(sha(bundle)+'  '+bundle.name+'\n')
print('A15_EVIDENCE_ARCHIVE='+str(bundle))
print('A15_EVIDENCE_SHA256='+sha(bundle))
PY
 exit "$rc"
}
trap finish EXIT
set +u
source /opt/ros/jazzy/setup.bash
set -u
cd "$ROOT"
timeout 120s cmake -S scripts/a15_pilot -B "$OUT/build_pose" > "$OUT/build_pose.log" 2>&1
timeout 180s cmake --build "$OUT/build_pose" -j2 >> "$OUT/build_pose.log" 2>&1
timeout 120s cmake -S scripts/a14_physics_freshness -B "$OUT/build_health" > "$OUT/build_health.log" 2>&1
timeout 180s cmake --build "$OUT/build_health" -j2 >> "$OUT/build_health.log" 2>&1
for scene in L15-01 L15-02 L15-03 L15-04; do
 args=()
 if [[ "$MODE" == --headless || ( "$MODE" == --ci && "$scene" != L15-01 ) ]];then args=(--headless);fi
 timeout --signal=INT --kill-after=30s 420s python3 -u scripts/a15_pilot_collect.py --sha "$PIN" --scene "$scene" \
    --out "$OUT/$scene" --pose-plugin "$OUT/build_pose/liba15_pilot.so" --health-plugin "$OUT/build_health/liba14_physics_freshness.so" "${args[@]}" \
    2>&1 | tee "$OUT/$scene.log"
done
python3 - "$OUT" "$MODE" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);mode=sys.argv[2]
cases=[json.loads((p/s/'verdict.json').read_text()) for s in ('L15-01','L15-02','L15-03','L15-04')]
assert all(x['data_verdict']=='PASS' and x['all_owned_stopped'] and not x['human_approved'] for x in cases)
if mode=='--ci':
    assert cases[0]['gui']=='PASS' and all(x['cleanup']=='PASS' for x in cases)
# Nonbinding experimental contrast: each family needs observed different responses.
# This is not a GT classifier or a 15mm product acceptance threshold.
for a,b in zip(cases[::2],cases[1::2]):
    va=a['metrics']['dish_02']['max_relative_displacement_m'];vb=b['metrics']['dish_02']['max_relative_displacement_m']
    print('A15_PILOT_CONTRAST',a['scene_id'],va,b['scene_id'],vb)
    assert max(va,vb)>=.025 and min(va,vb)<=.01 and abs(va-vb)>=.02,'A15_PILOT_CONTRAST_INSUFFICIENT'
print('A15_PILOT_DATA_AND_CONTRAST_PASS_GT_HOLD')
PY
