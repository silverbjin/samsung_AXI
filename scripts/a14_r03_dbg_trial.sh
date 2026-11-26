#!/usr/bin/env bash
# One bounded physical collection followed by independent raw evidence review.
set -Eeuo pipefail
PIN="$1"; SCENE="$2"; PLUGIN="$3"; OUT="$4"; shift 4
mkdir -p "$OUT"
OUT="$(realpath "$OUT")"
rc=0
timeout --signal=INT --kill-after=20s 600s python3 -u scripts/a14_r03_dbg_collect.py \
  --sha "$PIN" --plugin "$PLUGIN" --scene "$SCENE" --trace "$OUT/process_trace.json" "$@" \
  2>&1 | tee "$OUT/runner.log" || rc=$?
printf '%s\n' "$rc" > "$OUT/runner_exit.txt"
path="$(sed -n 's/^SMARTDISH_A_TRAY_EVIDENCE_BUNDLE=//p' "$OUT/runner.log" | tail -n 1)"
[[ -n "$path" && -f "$path" && -f "$OUT/process_trace.json" ]] || { echo DBG_EVIDENCE_MISSING; exit 2; }
cp "$path" "$OUT/production_raw.tar.gz"
(cd "$OUT" && sha256sum production_raw.tar.gz > production_raw.tar.gz.sha256)
python3 -u scripts/a14_r03_dbg_review.py --archive "$OUT/production_raw.tar.gz" \
  --sha "$PIN" --reviewer-sha "$PIN" --scene "$SCENE" --trace "$OUT/process_trace.json" --out "$OUT/verdict.json"
python3 - "$OUT/verdict.json" "$rc" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));rc=int(sys.argv[2])
# Only legacy late GUI RuntimeError exit 1 may accompany verified physical evidence.
assert (rc==0 and r['gui']!='FAIL') or (rc==1 and r['gui']=='FAIL' and r['gui_error'])
assert r['data_verdict']=='PASS' and r['all_owned_stopped']
print('R03_DBG_PHYSICAL_EVIDENCE_PASS_GUI_'+r['gui']+'_CLEANUP_'+r['cleanup'])
PY
