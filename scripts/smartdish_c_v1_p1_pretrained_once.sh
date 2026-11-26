#!/usr/bin/env bash
# C P1 pretrained weights review only. No training/Test, B audit or P0 rerun.
set -Eeuo pipefail
umask 077
PIN="$SMARTDISH_C_PIN"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo C_V1_P1_PIN_INVALID >&2; exit 2; }
P0="$HOME/smartdish_c_dataset_v1_p0_evidence/20261126T084104Z_ea54959b66b1/p0_report.json"
if [[ -n "$(printenv SMARTDISH_C_P0_REPORT || true)" ]]; then P0="$(printenv SMARTDISH_C_P0_REPORT)"; fi
MIRROR="$HOME/samsung_AXI"
if [[ -n "$(printenv SMARTDISH_C_LOCAL_REPO || true)" ]]; then MIRROR="$(printenv SMARTDISH_C_LOCAL_REPO)"; fi
EVIDENCE="$HOME/smartdish_c_dataset_v1_p1_evidence"
if [[ -n "$(printenv SMARTDISH_C_P1_EVIDENCE_DIR || true)" ]]; then EVIDENCE="$(printenv SMARTDISH_C_P1_EVIDENCE_DIR)"; fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SHORT="$(printf %s "$PIN" | cut -c1-12)"
OUT="$EVIDENCE/$STAMP-p1-$SHORT"
WORK="$(mktemp -d /tmp/smartdish-c-p1-XXXXXXXX)"
mkdir -p "$OUT"

finish() {
  rc=$?
  trap - EXIT
  python3 - "$OUT" "$PIN" "$rc" <<'PY'
import datetime,json,sys
from pathlib import Path
out,pin,rc=sys.argv[1:]
p=Path(out)/"execution_status.json"
p.write_text(json.dumps({
    "schema": 1, "source_sha": pin, "exit_code": int(rc),
    "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "training_executed": False, "test_opened": False,
    "B_AUDIT_REEXECUTED": False, "P0_REEXECUTED": False,
    "A19": "NOT_AUTHORIZED", "production_contact": "HOLD",
    "AI_OFF": "PROTECTED"}, indent=2)+"\n")
PY
  tar -C "$OUT" --sort=name --mtime="@0" --owner=0 --group=0 --numeric-owner -czf "$OUT.tar.gz" .
  sha256sum "$OUT.tar.gz" > "$OUT.tar.gz.sha256"
  echo "C_V1_P1_OWNER_RESULT exit_code=$rc archive=$OUT.tar.gz sidecar=$OUT.tar.gz.sha256"
  rm -rf "$WORK"
  exit "$rc"
}
trap finish EXIT
[[ -f "$P0" ]] || { echo C_V1_P1_P0_REPORT_MISSING >&2; exit 2; }
command -v git >/dev/null || { echo C_V1_P1_GIT_MISSING >&2; exit 2; }
command -v python3 >/dev/null || { echo C_V1_P1_PYTHON_MISSING >&2; exit 2; }
if [[ -d "$MIRROR/.git" ]] && git -C "$MIRROR" cat-file -e "$PIN^{commit}" 2>/dev/null; then
  git clone --quiet --no-checkout --shared "$MIRROR" "$WORK/repo"
else
  git clone --quiet --no-checkout --filter=blob:none https://github.com/silverbjin/samsung_AXI.git "$WORK/repo"
fi
if ! git -C "$WORK/repo" cat-file -e "$PIN^{commit}" 2>/dev/null; then
  git -C "$WORK/repo" fetch --quiet --depth 1 origin "$PIN"
fi
git -C "$WORK/repo" checkout --quiet --detach "$PIN"
[[ "$(git -C "$WORK/repo" rev-parse HEAD)" == "$PIN" ]] || {
  echo C_V1_P1_HEAD_MISMATCH >&2; exit 2;
}
[[ -z "$(git -C "$WORK/repo" status --porcelain)" ]] || {
  echo C_V1_P1_WORKTREE_DIRTY >&2; exit 2;
}
printf 'C_V1_P1_CHECKOUT_SHA=%s\nC_V1_P1_CLEAN=1\n' "$PIN" > "$OUT/checkout.log"
git --version > "$OUT/environment.log"
python3 --version >> "$OUT/environment.log" 2>&1
(
  cd "$WORK/repo"
  python3 -m ai.train.p1_pretrained_inspection \
      --p0-report "$P0" \
      --experiment-lock ai/docs/C_V1_EXPERIMENT_LOCK.json \
      --report "$OUT/p1_report.json"
) > "$OUT/preflight_stdout.log" 2> "$OUT/preflight_stderr.log"
echo 'C_V1_P1_WEIGHT_REVIEW_ONLY: actual training/Test not executed.'
