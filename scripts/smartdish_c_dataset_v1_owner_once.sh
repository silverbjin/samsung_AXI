#!/usr/bin/env bash
# Read-only C Dataset v1 P0. Never invokes B audit/release, training, or Gazebo.
# Must be downloaded from one IMMUTABLE C commit and checked against that SHA.
set -Eeuo pipefail
umask 077

PIN="${SMARTDISH_C_PIN:?Set full 40-character immutable C SHA}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo 'C_V1_IMMUTABLE_SHA_INVALID' >&2; exit 2; }
DATASET_ROOT="${SMARTDISH_C_DATASET_ROOT:-/home/jinho/smartdish_qa06_owner_release_026xvc/release/dataset_v1}"
BASE_REPO="${SMARTDISH_C_LOCAL_REPO:-${HOME}/samsung_AXI}"
RUN_ROOT="${SMARTDISH_C_EVIDENCE_DIR:-${HOME}/smartdish_c_dataset_v1_p0_evidence}"
RUN_TAG="$(date -u +%Y%m%dT%H%M%SZ)_${PIN:0:12}"
DEST="${RUN_ROOT}/${RUN_TAG}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/smartdish-c-v1-XXXXXXXX")"
mkdir -p "$DEST"
STARTED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

finish() {
  local rc="$?"; trap - EXIT
  python3 - "$DEST" "$PIN" "$STARTED" "$rc" <<'PY'
import json,sys,datetime
from pathlib import Path
out,pin,started,rc=sys.argv[1:]
(Path(out)/"execution_status.json").write_text(json.dumps({
 "schema":1,"source_sha":pin,"started_utc":started,
 "finished_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "exit_code":int(rc),"training_executed":False,
 "B_AUDIT_REEXECUTED":False,"A19":"NOT_AUTHORIZED",
 "production_contact":"HOLD","AI_OFF":"PROTECTED"},indent=2)+"\n")
PY
  if [[ -f "$DEST/p0_report.json" ]]; then
    python3 - "$DEST/p0_report.json" "$DEST/summary.json" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
keys=('verdict','reason','P0_verdict','files_independently_hashed','approved','excluded',
      'family_count','dataset_version','training_permitted')
Path(sys.argv[2]).write_text(json.dumps({k:r.get(k) for k in keys},indent=2)+"\n")
PY
  fi
  tar -C "$DEST" --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner -czf "${DEST}.tar.gz" .
  sha256sum "${DEST}.tar.gz" > "${DEST}.tar.gz.sha256"
  echo "C_V1_OWNER_RESULT exit_code=${rc} report=${DEST}/p0_report.json evidence=${DEST}.tar.gz sidecar=${DEST}.tar.gz.sha256"
  rm -rf "$WORK"
  exit "$rc"
}
trap finish EXIT

command -v git >/dev/null || { echo C_V1_GIT_MISSING >&2; exit 2; }
command -v python3 >/dev/null || { echo C_V1_PYTHON_MISSING >&2; exit 2; }
python3 -c 'from PIL import Image; print("C_V1_PILLOW_PRESENT")' > "$DEST/environment.log" 2>&1 || {
  echo C_V1_PILLOW_MISSING >&2; exit 2;
}
git --version >> "$DEST/environment.log"
python3 --version >> "$DEST/environment.log" 2>&1

# Clone from local mirror if available (no mutation of user's working tree).
# Fall back to GitHub if the exact immutable object is not present locally.
if [[ -d "$BASE_REPO/.git" ]] &&
   git -C "$BASE_REPO" cat-file -e "$PIN^{commit}" 2>/dev/null; then
  git clone --quiet --no-checkout --shared "$BASE_REPO" "$WORK/repo"
else
  git clone --quiet --no-checkout --filter=blob:none \
    https://github.com/silverbjin/samsung_AXI.git "$WORK/repo"
fi
if ! git -C "$WORK/repo" cat-file -e "$PIN^{commit}" 2>/dev/null; then
  git -C "$WORK/repo" fetch --quiet --depth 1 origin "$PIN"
fi
git -C "$WORK/repo" checkout --quiet --detach "$PIN"
ACTUAL="$(git -C "$WORK/repo" rev-parse HEAD)"
[[ "$ACTUAL" == "$PIN" ]] || { echo C_V1_HEAD_MISMATCH >&2; exit 2; }
[[ -z "$(git -C "$WORK/repo" status --porcelain)" ]] || {
  echo C_V1_CHECKOUT_NOT_CLEAN >&2; exit 2;
}
printf 'C_V1_CHECKOUT_SHA=%s\nC_V1_CHECKOUT_CLEAN=1\n' "$ACTUAL" > "$DEST/checkout.log"
[[ -d "$DATASET_ROOT" ]] || { echo C_V1_PRIVATE_ROOT_NOT_ACCESSIBLE >&2; exit 2; }

# The source file is from the immutable checkout, not the unpinned downloaded wrapper.
(
  cd "$WORK/repo"
  python3 -m ai.train.dataset_v1_gate \
     --dataset-root "$DATASET_ROOT" --report "$DEST/p0_report.json"
) > "$DEST/preflight_stdout.log" 2> "$DEST/preflight_stderr.log"

# Exit 0 is only CONTRACT_READY_HUMAN_REVIEW_REQUIRED; NO training is started.
echo 'C_V1_P0_CONTRACT_READY_HUMAN_REVIEW_REQUIRED; training NOT_RUN; P1 approval required'
