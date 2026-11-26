#!/usr/bin/env bash
# One owner run per newly integrated production scenario. Evidence PASS != GT.
set -Eeuo pipefail
MODE="${1:---gui}"
[[ $# -le 1 && ( "$MODE" == --gui || "$MODE" == --headless ) ]] || exit 2
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
PIN="$(printenv SMARTDISH_A14_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ && "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] || { echo A14_R03_PIN_MISMATCH; exit 2; }
[[ "$(git -C "$ROOT" branch --show-current)" == feat/smartdish-a14-physics-evidence ]] || { echo A14_R03_BRANCH_MISMATCH; exit 2; }
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || { echo A14_R03_TRACKED_EDITS_PRESERVED; exit 2; }
case "$ROOT" in /mnt/*) echo A14_R03_EXT4_REQUIRED; exit 2;; esac
[[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease || { echo A14_R03_REAL_WSL2_REQUIRED; exit 2; }
cd "$ROOT"
DIR="$ROOT/generated/smartdish_a14/r03_owner_$(date -u +%Y%m%dT%H%M%SZ)_$$"
mkdir -p "$DIR"
echo "A14_R03_EVIDENCE_DIR=$DIR"
status=HOLD
first_error=NONE
finish() {
  local rc=$?
  trap - EXIT
  if [[ $rc != 0 && "$first_error" == NONE ]]; then first_error="UNEXPECTED_EXIT_$rc"; fi
  python3 - "$DIR" "$PIN" "$status" "$first_error" <<'PY'
import hashlib,json,sys,tarfile
from pathlib import Path
p=Path(sys.argv[1]);pin,status,error=sys.argv[2:]
(p/'run_status.json').write_text(json.dumps(dict(source_sha=pin,status=status,first_error=error,
     production_contact_health='HOLD',rule_candidate='UNKNOWN',human_approved=False,
     ground_truth='NOT_OPERATOR_APPROVED'),indent=2)+'\n')
def sha(f):
    h=hashlib.sha256()
    with f.open('rb') as r:
        for chunk in iter(lambda:r.read(1<<20),b''): h.update(chunk)
    return h.hexdigest()
files=sorted(f for f in p.rglob('*') if f.is_file() and not f.is_symlink())
sums=p/'SHA256SUMS'
sums.write_text(''.join(sha(f)+'  '+f.relative_to(p).as_posix()+'\n' for f in files))
bundle=p/'a14_r03_owner_evidence.tar.gz'
with tarfile.open(bundle,'w:gz') as t:
    for f in files+[sums]: t.add(f,arcname=f.relative_to(p))
(p/(bundle.name+'.sha256')).write_text(sha(bundle)+'  '+bundle.name+'\n')
print('A14_R03_ARCHIVE='+str(bundle))
print('A14_R03_ARCHIVE_SHA256='+sha(bundle))
PY
  if [[ "$status" == EVIDENCE_PASS_GT_HOLD && $rc == 0 ]]; then
    echo A14_R03_OWNER_EVIDENCE_CAPTURE_PASS_GT_HOLD
  else
    echo "A14_R03_OWNER_HOLD=$first_error"
    exit 2
  fi
}
trap finish EXIT
fail() { first_error="$1"; exit 2; }
[[ -r /opt/ros/jazzy/setup.bash ]] || fail A14_R03_JAZZY_MISSING
set +u
source /opt/ros/jazzy/setup.bash
set -u
for cmd in git cmake g++ gz ros2 python3 timeout sha256sum; do
  command -v "$cmd" >/dev/null || fail "A14_R03_COMMAND_MISSING_$cmd"
done
dpkg-query -W ros-jazzy-gz-sim-vendor ros-jazzy-gz-plugin-vendor > "$DIR/vendor.log" 2>&1 || fail A14_R03_VENDOR_MISSING
find /opt/ros/jazzy/opt/gz_sim_vendor -type f -name 'libgz-sim8-physics-system.so*' -exec sha256sum {} + >> "$DIR/vendor.log"
BUILD="$DIR/build"
timeout --signal=INT --kill-after=10s 120s cmake -S scripts/a14_physics_freshness -B "$BUILD" > "$DIR/configure.log" 2>&1 || fail A14_R03_CMAKE_VERSION_OR_DEPENDENCY
timeout --signal=INT --kill-after=10s 180s cmake --build "$BUILD" -j2 > "$DIR/build.log" 2>&1 || fail A14_R03_PLUGIN_BUILD
PLUGIN="$BUILD/liba14_physics_freshness.so"
[[ -s "$PLUGIN" ]] || fail A14_R03_PLUGIN_MISSING
sha256sum "$PLUGIN" > "$DIR/plugin.sha256"
if [[ "$MODE" == --gui ]]; then
  [[ -n "$(printenv DISPLAY || :)" ]] || fail A14_R03_DISPLAY_REQUIRED
  export SMARTDISH_A_TRAY_GUI_PROFILE="$(printenv SMARTDISH_A_TRAY_GUI_PROFILE || echo xcb)"
  timeout --signal=INT --kill-after=8s 65s python3 -u scripts/smartdish_a_tray_gui_preflight.py \
      --sha "$PIN" --profile "$SMARTDISH_A_TRAY_GUI_PROFILE" > "$DIR/gui_preflight.log" 2>&1 || fail A14_R03_GUI_PREFLIGHT
fi
# GUI default; physical evidence and GUI verdict stay distinct in trial_summary.
args=()
[[ "$MODE" == --headless ]] || args=(--gui)
for scene in ST-02 UN-01; do
  out="$DIR/$scene"; mkdir -p "$out"
  echo "A14_R03_START_SCENE=$scene"
  rc=0
  timeout --signal=INT --kill-after=20s 600s python3 -u scripts/a14_r02_production_collect.py \
      --sha "$PIN" --plugin "$PLUGIN" --scene "$scene" "${args[@]}" \
      2>&1 | tee "$out/runner.log" || rc=$?
  path="$(sed -n 's/^SMARTDISH_A_TRAY_EVIDENCE_BUNDLE=//p' "$out/runner.log" | tail -n 1)"
  [[ -n "$path" && -s "$path" ]] || fail "A14_R03_ARCHIVE_MISSING_$scene"
  cp "$path" "$out/production_raw.tar.gz"
  (cd "$out" && sha256sum production_raw.tar.gz > production_raw.tar.gz.sha256)
  [[ "$rc" == 0 ]] || fail "A14_R03_RUNNER_EXIT_${scene}_$rc"
  python3 -u scripts/a14_r02_production_verify.py --sha "$PIN" \
     --trial "$(dirname "$path")/trial_0001" > "$out/verifier.log" 2>&1 || fail "A14_R03_VERIFIER_$scene"
done
# Keep logs and plugin fingerprint, not CMake object files.
rm -rf -- "$BUILD"
status=EVIDENCE_PASS_GT_HOLD
