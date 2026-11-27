#!/usr/bin/env bash
# C P2: ONE approved frozen-head research run on private Dataset v1. No Test opening.
# Must run on Owner WSL2 with previously accepted P0/P1 receipts.
set -Eeuo pipefail
umask 077
PIN="$(printenv SMARTDISH_C_PIN || true)"
SCOPE="$(printenv SMARTDISH_C_USAGE_DECLARATION || true)"
SCOPE_REQUIRED="NONCOMMERCIAL_INTERNAL_EDUCATIONAL_RESEARCH_NO_REDISTRIBUTION"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo C_V1_P2_IMMUTABLE_PIN_REQUIRED >&2; exit 2; }
[[ "$SCOPE" == "$SCOPE_REQUIRED" ]] || { echo C_V1_P2_NONCOMMERCIAL_SCOPE_REQUIRED >&2; exit 2; }

VENV="$HOME/.venvs/smartdish-c-v1-py312-cpu"
TORCH_CACHE="$HOME/.cache/smartdish-c-v1/torch"
BASE_REPO="$HOME/samsung_AXI"
DATASET_ROOT="$HOME/smartdish_qa06_owner_release_026xvc/release/dataset_v1"
P0="$HOME/smartdish_c_dataset_v1_p0_evidence/20261126T084104Z_ea54959b66b1/p0_report.json"
P1="$HOME/smartdish_c_dataset_v1_p1_evidence/20261127T003050Z-p1-23e5dcd49361/p1_report.json"
PRIVATE="$HOME/smartdish_c_v1_p2_private"
RUN_BASE="$HOME/smartdish_c_v1_p2_evidence"
# Overrides are paths only, never change immutable SHA or approval scope.
if [[ -n "$(printenv SMARTDISH_C_P0_REPORT || true)" ]]; then P0="$(printenv SMARTDISH_C_P0_REPORT)"; fi
if [[ -n "$(printenv SMARTDISH_C_P1_REPORT || true)" ]]; then P1="$(printenv SMARTDISH_C_P1_REPORT)"; fi
if [[ -n "$(printenv SMARTDISH_C_DATASET_ROOT || true)" ]]; then DATASET_ROOT="$(printenv SMARTDISH_C_DATASET_ROOT)"; fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SHORT="$(printf "%s" "$PIN" | cut -c1-12)"
OUT="$RUN_BASE/$STAMP-p2-$SHORT"
WORK="$(mktemp -d /tmp/smartdish-c-p2-XXXXXXXX)"
mkdir -p "$OUT"
finish() {
  rc="$?"
  trap - EXIT
  python3 - "$OUT" "$PIN" "$rc" <<'PY'
import json,sys
from datetime import datetime,timezone
from pathlib import Path
out,pin,rc=sys.argv[1:]
Path(out,"execution_status.json").write_text(json.dumps({
 "schema":1,"source_sha":pin,"exit_code":int(rc),
 "finished_utc":datetime.now(timezone.utc).isoformat(),
 "data_freeze":"A18_LAST","production_contact":"HOLD",
 "A19":"NOT_AUTHORIZED","AI_OFF":"PROTECTED",
 "B_AUDIT_REEXECUTED":False,"P0_REEXECUTED":False,
 "P1_REEXECUTED":False,"test_opened":False,
 "P3_EVALUATION_EXECUTED":False,"product_AI_ON_approved":False
},indent=2,sort_keys=True)+"\n")
PY
  tar -C "$OUT" --sort=name --mtime='@0' --owner=0 --group=0 \
      --numeric-owner -czf "$OUT.tar.gz" .
  sha256sum "$OUT.tar.gz" > "$OUT.tar.gz.sha256"
  echo "C_V1_P2_OWNER_RESULT exit_code=$rc evidence=$OUT.tar.gz sidecar=$OUT.tar.gz.sha256"
  echo "C_V1_P2_PRIVATE_CHECKPOINT_LOCATION=$PRIVATE (DO NOT UPLOAD)"
  rm -rf "$WORK"
  exit "$rc"
}
trap finish EXIT
command -v git >/dev/null || { echo C_V1_P2_GIT_MISSING >&2; exit 2; }
command -v python3 >/dev/null || { echo C_V1_P2_PYTHON3_MISSING >&2; exit 2; }
command -v flock >/dev/null || { echo C_V1_P2_FLOCK_MISSING >&2; exit 2; }
[[ -f "$P0" && -f "$P1" && -d "$DATASET_ROOT" ]] ||
    { echo C_V1_P2_OWNER_EVIDENCE_OR_DATASET_MISSING >&2; exit 2; }
[[ -f "$VENV/.smartdish_c_v1_environment.json" && -f "$VENV/bin/activate" &&
   -x "$VENV/bin/python" ]] || { echo C_V1_P2_CPU_VENV_MISSING >&2; exit 2; }
[[ ! -L "$PRIVATE" ]] || { echo C_V1_P2_PRIVATE_DIR_SYMLINK_DENIED >&2; exit 2; }

# Shared lock blocks parallel wheel updates while training, not other WSL2 tasks.
exec 8>"$HOME/.venvs/.smartdish-c-v1.install.lock"
flock -n -s 8 || { echo C_V1_P2_CPU_VENV_UPDATE_IN_PROGRESS >&2; exit 2; }

# Clone exact object; never change any existing A/B/C/D/E working tree.
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
[[ "$ACTUAL" == "$PIN" && -z "$(git -C "$WORK/repo" status --porcelain)" ]] ||
  { echo C_V1_P2_PIN_OR_CLEAN_MISMATCH >&2; exit 2; }
printf "C_V1_P2_CHECKOUT_SHA=%s\nC_V1_P2_CLEAN=1\n" "$ACTUAL" > "$OUT/checkout.log"

# Keep raw images, signed approval and checkpoint out of diagnostics archive.
mkdir -p "$PRIVATE" "$RUN_BASE"
chmod 700 "$PRIVATE"
export TORCH_HOME="$TORCH_CACHE" PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
unset PYTHONPATH PYTHONHOME PYTHONUSERBASE
(
  source "$VENV/bin/activate"
  hash -r
  [[ "$(command -v python)" == "$VENV/bin/python" ]] ||
    { echo C_V1_P2_VENV_ACTIVATION_FAILED >&2; exit 2; }
  python - "$VENV" <<'PY'
import sys
from pathlib import Path
assert sys.prefix!=sys.base_prefix and Path(sys.prefix).resolve()==Path(sys.argv[1]).resolve()
import torch,torchvision,PIL
assert torch.__version__=="2.5.1+cpu" and torchvision.__version__=="0.20.1+cpu"
assert PIL.__version__=="10.2.0" and torch.version.cuda is None
PY
  python --version > "$OUT/environment.log" 2>&1
  python -m pip --version >> "$OUT/environment.log" 2>&1
  cd "$WORK/repo"

  # Previously accepted P0/P1 reports are SHA-pinned and used read-only.
  python -m ai.train.prepare_v1_research_approval \
      --p0-report "$P0" --p1-report "$P1" \
      --experiment-lock ai/docs/C_V1_EXPERIMENT_LOCK.json \
      --scope-attestation "$SCOPE" \
      --out "$PRIVATE/c_v1_research_train_approval.json" \
      > "$OUT/approval_stdout.log" 2> "$OUT/approval_stderr.log"

  # One attempt per frozen Dataset v1. O_EXCL means no silent re-training.
  python - "$PRIVATE/c_v1_p2_single_attempt_reserved.json" "$PIN" <<'PY'
import json,sys
from datetime import datetime,timezone
from pathlib import Path
p=Path(sys.argv[1])
with p.open("x",encoding="utf-8") as f:
    f.write(json.dumps({"state":"ONE_P2_ATTEMPT_RESERVED",
                        "pin":sys.argv[2],
                        "reserved_at_utc":datetime.now(timezone.utc).isoformat(),
                        "test_opened":False,
                        "automatic_retry_authorized":False},sort_keys=True)+"\n")
PY
  python -m ai.train.train_classifier \
      --root "$DATASET_ROOT" \
      --split-manifest "$DATASET_ROOT/split_manifest.csv" \
      --phase frozen --device cpu --seed 42 --epochs 3 \
      --batch-size 4 --lr 0.0001 \
      --experiment-lock ai/docs/C_V1_EXPERIMENT_LOCK.json \
      --p0-report "$P0" \
      --research-approval "$PRIVATE/c_v1_research_train_approval.json" \
      --out "$PRIVATE/c_v1_frozen_head.pt" \
      --report "$PRIVATE/c_v1_frozen_train.json" \
      > "$OUT/train_stdout.log" 2> "$OUT/train_stderr.log"
  # Independent post-training audit; no Test data read or model scoring.
  python - "$PRIVATE/c_v1_frozen_train.json" "$PRIVATE/c_v1_frozen_head.pt" \
      "$OUT/summary.json" <<'PY'
import json,sys,hashlib
from pathlib import Path
report=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
weight=Path(sys.argv[2])
digest=hashlib.sha256(weight.read_bytes()).hexdigest()
assert digest==report["checkpoint_sha256"], "C_V1_P2_CHECKPOINT_SHA_MISMATCH"
assert report["data_scope"]=="PHYSICS_OBSERVED"
assert report["training_evidence"]=="REAL_TRAINING" and not report["deployment_allowed"]
assert report["phase"]=="frozen" and report["seed"]==42 and report["device"]=="cpu"
assert report["dataset"]["rows"]==14 and report["dataset"]["split_counts"]["test"]=={}
assert report["best_epoch_by_min_val_loss"] in (1,2,3)
assert report["test_used_for_training"] is False
summary={"verdict":"P2_FROZEN_TRAINED_AWAIT_C_REVIEW",
 "checkpoint_sha256":digest,
 "P1_plan_sha256":report["P1_approval"]["plan_sha256"],
 "pretrained_weight_sha256":report["P1_approval"]["pretrained_weight_sha256"],
 "data_scope":report["data_scope"],
 "phase":report["phase"],"seed":report["seed"],
 "split_counts":report["dataset"]["split_counts"],
 "epochs":report["epochs"],"selected_epoch":report["best_epoch_by_min_val_loss"],
 "best_val_loss":report["best_val_loss"],
 "test_used_for_training":False,"test_evaluated":False,
 "training_approved_scope":"NONCOMMERCIAL_INTERNAL_EDUCATIONAL_RESEARCH_ONLY",
 "checkpoint_distribution_authorized":False,
 "C_RESEARCH_PILOT_ACCEPTED":False,"E_AI_ON":"HOLD",
 "AI_OFF":"PROTECTED","production_contact":"HOLD","A19":"NOT_AUTHORIZED"}
Path(sys.argv[3]).write_text(json.dumps(summary,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
PY
)
echo "C_V1_P2_TRAINING_COMPLETE_RESEARCH_ONLY; Test sealed; private checkpoint not in evidence TAR."
