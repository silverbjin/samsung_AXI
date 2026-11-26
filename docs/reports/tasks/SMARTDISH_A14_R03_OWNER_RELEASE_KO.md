# R03 DBG — CI 검증 완료 및 UN-01 독립 Owner 인수 안내

## Immutable execution pin
`7c6e950653384cf7c9ac8af58ea849281886a468` is the verified execution SHA. This report-only later commit is NOT a new execution pin. R03 overall historical cleanup HOLD and GT UNKNOWN/HOLD remain. Owner UN-01 NOT_RUN.

## Actual CI results
- #45730294064 RED environment: missing pytest, L2 skipped. #45730378065 at exact pin SUCCESS; L0 17/17 and exact-pin checkout fixture PASS; L2 C++ build + actual ST-02 normal software GUI + actual UN-01 GUI process SIGABRT injection after observation unpause SUCCESS. Normal GUI PASS, data PASS, cleanup all 6 exit 0; injected GUI FAIL -6 preserved, data PASS, server+4 aux exit 0, all stopped. Both raw archives revalidated by actual code. No synthetic data. R02-2/R02-3 previous PASS reused. MVP #45730385179 exact pin SUCCESS. Packaging #45730294023 prior candidate b636ad3 SUCCESS; exact pin checkout fixture repeated as part of #45730378065 L0. 
- [CI #45730378065](https://github.com/silverbjin/samsung_AXI/actions/runs/45730378065), [Artifact #15076666194](https://github.com/silverbjin/samsung_AXI/actions/runs/45730378065/artifacts/15076666194), ZIP digest from metadata 449015c82d8d21633aac0fd4bde8bbe236be1a6e448c1766e33c80c9db04f0f5. Normal raw TAR SHA from actual log 03bcd8fba4f18cc5c63c1e1a210e8e2171193cb1c767a53d4e9ea59f0cda4532 (38 manifest rows), injected 792cb0b8cd98e8f61bba13f3c741110e4a0daeb56471df07fd264d4816cf8adf (40). Cloud artifact ZIP not independently downloaded/rehash here; log and metadata verified. No CI rerun.

## Historical ST-02 local read-only review
User raw SHA 4f4328e6d40ba2936467f4f462364869c2f5662a6d71565d05a9961d4ab4342f. Local environment raw GitHub DNS unavailable; copied relevant 19 verifier function bodies from exact GitHub pin to isolated Python harness, matched each length + FNV1a fingerprint with fetched source; not a full repo checkout or ROS run. Ran review(reuse=True) with actual historical TAR: 41/41, data PASS, 50960 refresh steps, 17167 raw ROS, GUI FAIL, cleanup FAIL, all owned stopped, next_independent_scene_allowed=true. Trial/stack 20261126T002816Z_2109_01, seed 212. Result JSON SHA256 098399f7c1cd501f37a4388d656b8b34d2042780e3c79779d88863f637536801. Execution SHA 194db14 vs reviewer SHA 7c6e950 preserved. Historical original private files not published. Full exact repo verifier executes before any new Gazebo run at Owner; fails closed if old raw missing/wrong hash. No ST-02 rerun needed.

## WSL2 one-shot
Use the historical ST-02 archive at the path recorded in the production run (or exact copied file matching the raw hash), not outer Owner TAR. Use exact pin only. The GUI child is software; server keeps inherited GPU. Existing WSLg native root and -11 teardown unresolved, separate diagnostic; do not call whole clean PASS. User visual QA separate.

```bash
(
set -Eeuo pipefail
PIN=7c6e950653384cf7c9ac8af58ea849281886a468
RAW="$HOME/samsung_AXI_A14_R03_194db14_wfddMo/generated/smartdish_tray/run_20261126T002816Z_2109/smartdish_a_tray_evidence.tar.gz"
[[ -f "$RAW" ]] || { echo ST02_ORIGINAL_RAW_NOT_FOUND; exit 2; }
printf '%s  %s\\n' 4f4328e6d40ba2936467f4f462364869c2f5662a6d71565d05a9961d4ab4342f "$RAW" | sha256sum -c -
curl -fsSLo "$HOME/a14_r03_dbg_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/a14_r03_dbg_bootstrap.sh"
SMARTDISH_A14_SOURCE_SHA="$PIN" bash "$HOME/a14_r03_dbg_bootstrap.sh" --gui "$RAW"
)
```
If historical path moved, change RAW to exact standalone ST-02 TAR; do not regenerate. Output NEW_EVIDENCE_ARCHIVE and NEW_EVIDENCE_SHA256; attach a14_r03_dbg_owner_evidence.tar.gz + sidecar. Expected R03_DBG_OWNER_STATUS=EVIDENCE_PASS_CLEANUP_REVIEW_GT_HOLD only if both data reviewed. This is evidence capture/cleanup review, not overall R03 clean or GT approval. On failure attach emitted evidence and do not retry automatically. Main merge prohibited until acceptance/approval.
