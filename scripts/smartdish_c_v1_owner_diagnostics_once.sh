#!/usr/bin/env bash
# Optional SINGLE WSL2 command after a new blocker; do NOT rerun existing PASS.
# Read-only: no apt/pip, Test, model inference, training or new physical data.
set -Eeuo pipefail
umask 077
PIN="$(printenv SMARTDISH_C_PIN || true)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo C_V1_DOCTOR_PIN_REQUIRED >&2; exit 2; }
VENV="$HOME/.venvs/smartdish-c-v1-py312-cpu"
P0="$HOME/smartdish_c_dataset_v1_p0_evidence/20261126T084104Z_ea54959b66b1/p0_report.json"
P1="$HOME/smartdish_c_dataset_v1_p1_evidence/20261127T003050Z-p1-23e5dcd49361/p1_report.json"
P2="$HOME/smartdish_c_v1_p2_evidence/20261127T004925Z-p2-9db90e52da30/summary.json"
CKPT="$HOME/smartdish_c_v1_p2_private/c_v1_frozen_head.pt"
[[ -z "$(printenv SMARTDISH_C_P0_REPORT || true)" ]] || P0="$(printenv SMARTDISH_C_P0_REPORT)"
[[ -z "$(printenv SMARTDISH_C_P1_REPORT || true)" ]] || P1="$(printenv SMARTDISH_C_P1_REPORT)"
[[ -z "$(printenv SMARTDISH_C_P2_SUMMARY || true)" ]] || P2="$(printenv SMARTDISH_C_P2_SUMMARY)"
[[ -z "$(printenv SMARTDISH_C_CHECKPOINT || true)" ]] || CKPT="$(printenv SMARTDISH_C_CHECKPOINT)"
BASE="$HOME/samsung_AXI"
OUT_BASE="$HOME/smartdish_c_v1_owner_diagnostic_evidence"
SHORT="$(printf %s "$PIN" | cut -c1-12)"
OUT="$OUT_BASE/$(date -u +%Y%m%dT%H%M%SZ)-$SHORT"
WORK="$(mktemp -d /tmp/smartdish-c-doctor-XXXXXXXX)"
mkdir -p "$OUT"
finish() {
  rc=$?
  trap - EXIT
  python3 - "$OUT" "$PIN" "$rc" <<'PY'
import json,sys
from pathlib import Path
out,pin,rc=sys.argv[1:]
Path(out,"execution_status.json").write_text(json.dumps({
"source_sha":pin,"exit_code":int(rc),
"P0_REEXECUTED":False,"P1_REEXECUTED":False,"P2_RETRAINED":False,
"P3_test_opened":False,"P3_test_authorized":False,
"AI_OFF":"PROTECTED","production_contact":"HOLD","A19":"NOT_AUTHORIZED"
},sort_keys=True,indent=2)+"\n")
PY
  tar -C "$OUT" --sort=name --mtime='@0' --owner=0 --group=0 \
      --numeric-owner -czf "$OUT.tar.gz" .
  sha256sum "$OUT.tar.gz" > "$OUT.tar.gz.sha256"
  echo "C_V1_OWNER_DOCTOR_RESULT exit_code=$rc archive=$OUT.tar.gz sidecar=$OUT.tar.gz.sha256"
  rm -rf "$WORK"
  exit "$rc"
}
trap finish EXIT
command -v git >/dev/null || { echo C_V1_DOCTOR_GIT_MISSING >&2; exit 2; }
command -v flock >/dev/null || { echo C_V1_DOCTOR_FLOCK_MISSING >&2; exit 2; }
[[ -f "$P0" && -f "$P1" && -f "$P2" && -f "$CKPT" ]] ||
  { echo C_V1_DOCTOR_EVIDENCE_FILE_MISSING >&2; exit 2; }
[[ -x "$VENV/bin/python" && -f "$VENV/.smartdish_c_v1_environment.json" ]] ||
  { echo C_V1_DOCTOR_VENV_MISSING >&2; exit 2; }
exec 8>"$HOME/.venvs/.smartdish-c-v1.install.lock"
flock -n -s 8 || { echo C_V1_DOCTOR_VENV_INSTALL_BUSY >&2; exit 2; }
if [[ -d "$BASE/.git" ]] && git -C "$BASE" cat-file -e "$PIN^{commit}" 2>/dev/null; then
  git clone --quiet --no-checkout --shared "$BASE" "$WORK/repo"
else
  git clone --quiet --no-checkout --filter=blob:none \
       https://github.com/silverbjin/samsung_AXI.git "$WORK/repo"
fi
if ! git -C "$WORK/repo" cat-file -e "$PIN^{commit}" 2>/dev/null; then
  git -C "$WORK/repo" fetch --quiet --depth 1 origin "$PIN"
fi
git -C "$WORK/repo" checkout --quiet --detach "$PIN"
[[ "$(git -C "$WORK/repo" rev-parse HEAD)" == "$PIN" &&
   -z "$(git -C "$WORK/repo" status --porcelain)" ]] ||
  { echo C_V1_DOCTOR_PIN_OR_DIRTY_CHECKOUT >&2; exit 2; }
printf "C_V1_DOCTOR_SHA=%s\nC_V1_DOCTOR_CLEAN=1\n" "$PIN" > "$OUT/checkout.log"
export PYTHONNOUSERSITE=1 TORCH_HOME="$HOME/.cache/smartdish-c-v1/torch"
unset PYTHONPATH PYTHONHOME PYTHONUSERBASE
(
  source "$VENV/bin/activate"
  [[ "$(command -v python)" == "$VENV/bin/python" ]] ||
    { echo C_V1_DOCTOR_VENV_ACTIVATION_FAILED >&2; exit 2; }
  cd "$WORK/repo"
  python -m ai.train.owner_environment_diagnostics \
      --p0-report "$P0" --p1-report "$P1" --p2-summary "$P2" \
      --experiment-lock ai/docs/C_V1_EXPERIMENT_LOCK.json \
      --checkpoint "$CKPT" --venv "$VENV" \
      --report "$OUT/environment_report.json"
) > "$OUT/diagnostic_stdout.log" 2> "$OUT/diagnostic_stderr.log"
echo C_V1_DOCTOR_DONE_READ_ONLY_TEST_STILL_SEALED
