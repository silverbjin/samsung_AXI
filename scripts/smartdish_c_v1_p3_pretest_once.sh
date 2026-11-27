#!/usr/bin/env bash
# P3 pre-Test seal ONLY. Reads private P2 checkpoint, never opens Test or trains.
set -Eeuo pipefail
umask 077
PIN="$(printenv SMARTDISH_C_PIN || true)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo C_V1_P3_PRETEST_PIN_REQUIRED >&2; exit 2; }
VENV="$HOME/.venvs/smartdish-c-v1-py312-cpu"
PRIVATE="$HOME/smartdish_c_v1_p2_private"
P2_SUMMARY="$HOME/smartdish_c_v1_p2_evidence/20261127T004925Z-p2-9db90e52da30/summary.json"
if [[ -n "$(printenv SMARTDISH_C_P2_SUMMARY || true)" ]]; then
  P2_SUMMARY="$(printenv SMARTDISH_C_P2_SUMMARY)"
fi
BASE="$HOME/samsung_AXI"
EVIDENCE="$HOME/smartdish_c_v1_p3_pretest_evidence"
SHORT="$(printf %s "$PIN" | cut -c1-12)"
TAG="$(date -u +%Y%m%dT%H%M%SZ)-$SHORT"
OUT="$EVIDENCE/$TAG"
WORK="$(mktemp -d /tmp/smartdish-c-p3pretest-XXXXXXXX)"
mkdir -p "$OUT"
finish() {
  rc=$?
  trap - EXIT
  python3 - "$OUT" "$PIN" "$rc" <<'PY'
import json,sys
from pathlib import Path
out,pin,rc=sys.argv[1:]
Path(out,"execution_status.json").write_text(json.dumps({
"source_sha":pin,"exit_code":int(rc),"training_executed":False,
"P3_test_opened":False,"P3_test_evaluated":False,
"P3_test_authorized":False,"AI_OFF":"PROTECTED",
"production_contact":"HOLD","A19":"NOT_AUTHORIZED"},indent=2)+"\n")
PY
  tar -C "$OUT" --sort=name --mtime='@0' --owner=0 --group=0 \
      --numeric-owner -czf "$OUT.tar.gz" .
  sha256sum "$OUT.tar.gz" > "$OUT.tar.gz.sha256"
  echo "C_V1_P3_PRETEST_RESULT exit_code=$rc archive=$OUT.tar.gz sidecar=$OUT.tar.gz.sha256"
  rm -rf "$WORK"
  exit "$rc"
}
trap finish EXIT
command -v flock >/dev/null || { echo C_V1_P3_FLOCK_MISSING >&2; exit 2; }
[[ -f "$P2_SUMMARY" && -f "$PRIVATE/c_v1_frozen_head.pt" ]] ||
  { echo C_V1_P3_P2_PRIVATE_FILES_MISSING >&2; exit 2; }
[[ -f "$VENV/.smartdish_c_v1_environment.json" && -x "$VENV/bin/python" ]] ||
  { echo C_V1_P3_VENV_MISSING >&2; exit 2; }
exec 8>"$HOME/.venvs/.smartdish-c-v1.install.lock"
flock -n -s 8 || { echo C_V1_P3_VENV_INSTALL_BUSY >&2; exit 2; }
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
  { echo C_V1_P3_PIN_OR_DIRTY_CHECKOUT >&2; exit 2; }
printf 'C_V1_P3_PRETEST_SHA=%s\nC_V1_P3_CLEAN=1\n' "$PIN" > "$OUT/checkout.log"
export PYTHONNOUSERSITE=1 TORCH_HOME="$HOME/.cache/smartdish-c-v1/torch"
unset PYTHONPATH PYTHONHOME PYTHONUSERBASE
(
  source "$VENV/bin/activate"
  [[ "$(command -v python)" == "$VENV/bin/python" ]] ||
    { echo C_V1_P3_VENV_ACTIVATION_FAILED >&2; exit 2; }
  cd "$WORK/repo"
  # Future necessary acceptance in one WSL2 action: environment + checkpoint seal.
  # Existing accepted 2026-11-27 Owner pretest must NOT be rerun by this change.
  python -m ai.train.owner_environment_diagnostics \
      --p0-report "$HOME/smartdish_c_dataset_v1_p0_evidence/20261126T084104Z_ea54959b66b1/p0_report.json" \
      --p1-report "$HOME/smartdish_c_dataset_v1_p1_evidence/20261127T003050Z-p1-23e5dcd49361/p1_report.json" \
      --p2-summary "$P2_SUMMARY" \
      --experiment-lock ai/docs/C_V1_EXPERIMENT_LOCK.json \
      --checkpoint "$PRIVATE/c_v1_frozen_head.pt" \
      --venv "$VENV" --report "$OUT/environment_report.json"
  python -m ai.train.p3_pretest_seal \
      --p2-summary "$P2_SUMMARY" \
      --checkpoint "$PRIVATE/c_v1_frozen_head.pt" \
      --experiment-lock ai/docs/C_V1_EXPERIMENT_LOCK.json \
      --report "$OUT/pretest_report.json"
) > "$OUT/pretest_stdout.log" 2> "$OUT/pretest_stderr.log"
echo "C_V1_P3_PRETEST_ONLY: no Test, inference, training or approval."
