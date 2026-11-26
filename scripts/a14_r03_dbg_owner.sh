#!/usr/bin/env bash
# Resume only UN-01 after independent review of exact historical ST-02 raw.
set -Eeuo pipefail
MODE="$1"; RAW="$(realpath "$2")"
[[ $# -eq 2 && ( "$MODE" == --gui || "$MODE" == --headless ) && -f "$RAW" ]] || exit 2
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PIN="$(printenv SMARTDISH_A14_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] || exit 2
[[ "$(git -C "$ROOT" branch --show-current)" == feat/smartdish-a14-physics-evidence ]] || exit 2
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || exit 2
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || exit 2
case "$ROOT" in /mnt/*) exit 2;; esac
cd "$ROOT"
DIR="$(mktemp -d "$ROOT/generated_r03_dbg_XXXXXX")"
# Outside tracked tree contents; independent workspace only.
STATUS=HOLD
FIRST=NONE
finish() {
  local rc=$?;trap - EXIT
  if [[ $rc != 0 && "$FIRST" == NONE ]]; then FIRST="UNEXPECTED_EXIT_$rc"; fi
  python3 - "$DIR" "$PIN" "$STATUS" "$FIRST" <<'PY'
import hashlib,json,sys,tarfile
from pathlib import Path
p=Path(sys.argv[1]);pin,status,error=sys.argv[2:]
def sha(f):
    with f.open('rb') as s:return hashlib.file_digest(s,'sha256').hexdigest()
(p/'run_status.json').write_text(json.dumps(dict(source_sha=pin,status=status,first_error=error,
  human_approved=False,ground_truth='NOT_OPERATOR_APPROVED',rule_candidate='UNKNOWN'),indent=2)+'\n')
files=sorted(f for f in p.rglob('*') if f.is_file() and not f.is_symlink() and f.relative_to(p).parts[0]!='build')
sums=p/'SHA256SUMS';sums.write_text(''.join(sha(f)+'  '+f.relative_to(p).as_posix()+'\n' for f in files))
bundle=p/'a14_r03_dbg_owner_evidence.tar.gz'
with tarfile.open(bundle,'w:gz') as t:
    for f in files+[sums]:t.add(f,arcname=f.relative_to(p))
(p/(bundle.name+'.sha256')).write_text(sha(bundle)+'  '+bundle.name+'\n')
print('NEW_EVIDENCE_ARCHIVE='+str(bundle))
print('NEW_EVIDENCE_SHA256='+sha(bundle))
PY
  echo "R03_DBG_OWNER_STATUS=$STATUS"
  [[ "$STATUS" == EVIDENCE_PASS_CLEANUP_REVIEW_GT_HOLD && $rc == 0 ]] || exit 2
}
trap finish EXIT
fail(){ FIRST="$1"; exit 2; }
echo "REQUESTED_SHA=$PIN"
echo "ACTUAL_SOURCE_SHA=$(git rev-parse HEAD)"
echo "OWNER_WORKSPACE=$ROOT"
[[ -r /opt/ros/jazzy/setup.bash ]] || fail ROS_MISSING
set +u
source /opt/ros/jazzy/setup.bash
set -u
for cmd in git cmake g++ gz ros2 python3 timeout sha256sum; do command -v "$cmd" >/dev/null || fail "MISSING_$cmd"; done
mkdir "$DIR/ST-02"
cp "$RAW" "$DIR/ST-02/production_raw.tar.gz"
python3 -u scripts/a14_r03_dbg_review.py --archive "$DIR/ST-02/production_raw.tar.gz" \
  --sha 194db1429899775174096e24cde2e785feecda6b --reviewer-sha "$PIN" \
  --scene ST-02 --reuse --out "$DIR/ST-02/verdict.json" > "$DIR/ST-02/review.log" 2>&1 || fail ST02_REUSE_REVIEW
python3 - "$DIR/ST-02/verdict.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
for key,field in [('REUSED_EVIDENCE_SHA256','archive_sha256'),('ST02_REUSED_PHYSICS_VERDICT','data_verdict'),
                  ('ST02_GUI_VERDICT','gui'),('ST02_CLEANUP_VERDICT','cleanup')]:print(key+'='+str(r[field]))
assert r['data_verdict']=='PASS' and r['all_owned_stopped'] and r['reused']
PY
echo UN01_OWNER_EXECUTION_REQUIRED=true
dpkg-query -W ros-jazzy-gz-sim-vendor ros-jazzy-gz-plugin-vendor > "$DIR/vendor.log" 2>&1 || fail VENDOR_MISSING
find /opt/ros/jazzy/opt/gz_sim_vendor -type f -name 'libgz-sim8-physics-system.so*' -exec sha256sum {} + >> "$DIR/vendor.log"
timeout --signal=INT --kill-after=10s 120s cmake -S scripts/a14_physics_freshness -B "$DIR/build" > "$DIR/configure.log" 2>&1 || fail BUILD_CONFIG
timeout --signal=INT --kill-after=10s 180s cmake --build "$DIR/build" -j2 > "$DIR/build.log" 2>&1 || fail BUILD_FAIL
PLUGIN="$DIR/build/liba14_physics_freshness.so"
[[ -s "$PLUGIN" ]] || fail PLUGIN_MISSING
sha256sum "$PLUGIN" > "$DIR/plugin.sha256"
args=()
if [[ "$MODE" == --gui ]]; then
  [[ -n "$(printenv DISPLAY || :)" ]] || fail DISPLAY_REQUIRED
  # Preflight uses the same client software profile but is diagnostic, not physical evidence.
  rc=0
  env -u MESA_D3D12_DEFAULT_ADAPTER_NAME -u WAYLAND_DISPLAY GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1 QT_QPA_PLATFORM=xcb \
    timeout --signal=INT --kill-after=8s 65s python3 -u scripts/smartdish_a_tray_gui_preflight.py \
      --sha "$PIN" --profile xcb > "$DIR/gui_preflight.log" 2>&1 || rc=$?
  printf '%s\n' "$rc" > "$DIR/gui_preflight_exit.txt"
  if [[ $rc == 0 ]]; then echo GUI_PREFLIGHT_VERDICT=PASS; else echo GUI_PREFLIGHT_VERDICT=FAIL; fi
else
  echo GUI_PREFLIGHT_VERDICT=NOT_REQUESTED
  args=(--headless)
fi
bash scripts/a14_r03_dbg_trial.sh "$PIN" UN-01 "$PLUGIN" "$DIR/UN-01" "${args[@]}" || fail UN01_EVIDENCE_HOLD
# Historical cleanup remains FAIL; do not promote whole Owner run to clean PASS.
python3 - "$DIR/UN-01/verdict.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]))
assert r['data_verdict']=='PASS' and r['all_owned_stopped']
print('UN01_GUI_VERDICT='+r['gui'])
print('UN01_CLEANUP_VERDICT='+r['cleanup'])
PY
STATUS=EVIDENCE_PASS_CLEANUP_REVIEW_GT_HOLD
