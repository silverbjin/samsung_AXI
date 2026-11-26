#!/usr/bin/env bash
# A14 opt-in, SHA-pinned static-gravity GT candidate evidence. No human GT.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
MODE=--gui
if [[ $# -gt 0 ]]; then MODE="$1"; shift; fi
[[ $# -eq 0 && ( "$MODE" == --gui || "$MODE" == --headless ) ]] || { echo A14_MODE_INVALID; exit 2; }
PIN="$(printenv SMARTDISH_A14_SOURCE_SHA || :)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo A14_PIN_REQUIRED; exit 2; }
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$PIN" ]] || { echo A14_SOURCE_SHA_MISMATCH; exit 2; }
[[ "$(git -C "$ROOT" branch --show-current)" == feat/smartdish-a14-physics-evidence ]] || { echo A14_BRANCH_MISMATCH; exit 2; }
[[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || { echo A14_DIRTY_WORKTREE; exit 2; }
case "$ROOT" in /mnt/*) echo A14_EXT4_REQUIRED; exit 2;; esac
if [[ -z "$(printenv CI || :)" ]]; then
  [[ -n "$(printenv WSL_DISTRO_NAME || :)" ]] && grep -qiE 'microsoft|wsl' /proc/sys/kernel/osrelease ||
    { echo A14_REAL_WSL2_REQUIRED; exit 2; }
fi
if [[ "$MODE" == --gui ]]; then
  [[ -n "$(printenv DISPLAY || :)$(printenv WAYLAND_DISPLAY || :)" ]] || { echo A14_WSLG_DISPLAY_REQUIRED; exit 2; }
fi
[[ -r /opt/ros/jazzy/setup.bash ]] || { echo A14_JAZZY_MISSING; exit 2; }
for command in gz ros2 python3 tar sha256sum; do
  type "$command" >/dev/null 2>&1 || { echo "A14_COMMAND_MISSING=$command"; exit 2; }
done
set +u
source /opt/ros/jazzy/setup.bash
set -u
ros2 pkg prefix ros_gz_bridge >/dev/null
ros2 interface show ros_gz_interfaces/msg/Contacts >/dev/null
cd "$ROOT"
DIR="$ROOT/generated/smartdish_a14/run_$(date -u +%Y%m%dT%H%M%SZ)_$$"
mkdir -p "$DIR"
echo "A14_SOURCE_SHA_PASS=$PIN"
echo "A14_PROFILE=STATIC_GRAVITY GUI=$MODE"
echo "A14_DIAG_DIR=$DIR"
overall=PASS
if [[ "$MODE" == --gui ]]; then
  export SMARTDISH_A_TRAY_GUI_PROFILE="$(printenv SMARTDISH_A_TRAY_GUI_PROFILE || echo xcb)"
  if python3 -u scripts/smartdish_a_tray_gui_preflight.py \
       --sha "$PIN" --profile "$SMARTDISH_A_TRAY_GUI_PROFILE" \
       > "$DIR/gui_preflight.log" 2>&1; then
    echo A14_GUI_PREFLIGHT_PASS
  else
    echo A14_GUI_PREFLIGHT_HOLD
    overall=HOLD
  fi
fi
if [[ "$overall" == PASS ]]; then
  for scene in ST-02 UN-01; do
    tag="$(echo "$scene" | tr '-' '_')"
    evidence="$DIR/$tag"
    mkdir -p "$evidence"
    if python3 -u scripts/smartdish_a_tray_live.py single \
        --scene "$scene" --seed 211 --a14-static "$MODE" \
        --expected-sha "$PIN" > "$evidence/runner.log" 2>&1; then
      echo "A14_REAL_GAZEBO_CAPTURE_COMPLETED=$scene"
    else
      echo "A14_REAL_GAZEBO_CAPTURE_HOLD=$scene"
      overall=HOLD
    fi
    path="$(sed -n 's/^SMARTDISH_A_TRAY_EVIDENCE_BUNDLE=//p' "$evidence/runner.log" | tail -1)"
    if [[ -n "$path" && -s "$path" ]]; then
      cp "$path" "$evidence/a13_raw_evidence.tar.gz"
      trial="$(dirname "$path")/trial_0001"
      for name in a14_gt_candidate.json geometry_layout.json capture_metadata.json \
                  camera_pose_metadata.json scenario.scenario.json physics_observations_v2.jsonl \
                  tray_pose_timeline.jsonl contact_events.jsonl contact_sensor_status.json; do
        if [[ -f "$trial/$name" ]]; then cp "$trial/$name" "$evidence/$name"; fi
      done
      if python3 -u scripts/smartdish_a14_verify.py --trial "$trial" --sha "$PIN" \
           --report "$evidence/qa_report.json" > "$evidence/verifier.log" 2>&1; then
        echo "A14_REAL_PHYSICS_PROFILE_PASS=$scene"
      else
        echo "A14_REAL_PHYSICS_PROFILE_HOLD=$scene"
        overall=HOLD
      fi
    else
      echo "A14_EVIDENCE_ARCHIVE_MISSING=$scene"
      overall=HOLD
    fi
  done
fi
printf '{"source_sha":"%s","status":"%s","human_approved":false}\n' \
  "$PIN" "$overall" > "$DIR/run_status.json"
python3 - "$DIR" "$PIN" "$overall" <<'PY'
import hashlib,json,sys,tarfile
from pathlib import Path
directory=Path(sys.argv[1]);sha=sys.argv[2];status=sys.argv[3]
def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()
names=["run_status.json","gui_preflight.log"]
required=("runner.log","verifier.log","qa_report.json","a13_raw_evidence.tar.gz",
          "a14_gt_candidate.json","geometry_layout.json","capture_metadata.json",
          "camera_pose_metadata.json","scenario.scenario.json",
          "physics_observations_v2.jsonl","tray_pose_timeline.jsonl",
          "contact_events.jsonl","contact_sensor_status.json")
for scene in ("ST_02","UN_01"):
    names.extend(scene+"/"+item for item in required)
present=[p for name in names if (p:=directory/name).is_file() and not p.is_symlink()]
inventory={"schema":2,"source_sha":sha,"physics_profile":"STATIC_GRAVITY",
    "human_approved":False,"status":status,
    "missing":sorted(set(names)-{p.relative_to(directory).as_posix() for p in present}),
    "files":[{"name":p.relative_to(directory).as_posix(),
              "sha256":digest(p),"bytes":p.stat().st_size} for p in present]}
(directory/"archive_inventory.json").write_text(json.dumps(inventory,indent=2,sort_keys=True)+"\n")
items=present+[directory/"archive_inventory.json"]
(directory/"SHA256SUMS").write_text("".join(
    digest(p)+"  "+p.relative_to(directory).as_posix()+"\n" for p in items))
bundle=directory/"smartdish_a14_diagnostics.tar.gz"
with tarfile.open(bundle,"w:gz") as t:
    for p in items+[directory/"SHA256SUMS"]:
        t.add(p,arcname=p.relative_to(directory).as_posix())
(directory/(bundle.name+".sha256")).write_text(digest(bundle)+"  "+bundle.name+"\n")
print("A14_DIAG_ARCHIVE="+str(bundle))
print("A14_DIAG_ARCHIVE_SHA256="+digest(bundle))
print("A14_DIAG_SHA_SIDECAR="+str(bundle)+".sha256")
PY
if [[ "$overall" == PASS ]]; then echo A14_STATIC_GRAVITY_P0_EVIDENCE_PASS_GT_REVIEW_REQUIRED; else
  echo A14_STATIC_GRAVITY_P0_EVIDENCE_HOLD
  exit 2
fi
