# SmartDish A18 — P1~P4 실제 Cloud 완료 및 신규 8개 WSL2 인수 출고 (2026-11-26)
## 범위와 출고 상태
사용자 승인 SMARTDISH_A18_PHYSICAL_LAYOUT_DEVELOPMENT_SPEC_KO.md와 PROPOSED_LAYOUT_REGISTRY 기준. P3 실제 검증 fd44ac7e9cca56c774bec810c438382219a786b1, #45763439864 SUCCESS. P3 정합성/교육 원장 docs/reports/acceptance/SMARTDISH_A18_PHASE1_CLOUD_OWNER_RELEASE_KO.md 보존. P4 f1bf400f9b9ef6f554f90b92d92e1e63aeffb049에서 P3 core/registry/profile 동일성 gate, 확대 05~08만 실행. P3 기존 4개를 P4에서 다시 실행하지 않음. 선행 alternate CI ae5f614는 같은 물리 4개 다른 ID 계약이며 신규 수 증가 없음. A15/A16 물리 원본 재실험 없음. A17 원인 분석/최소 완화 및 A17-08 scoped CI 재사용; 실제 생산 GPU qualification 아직 NOT_RUN.
## 실제 CI 및 독립 증거
P4 #45764157107 SUCCESS, l0 12 A18+15 A17+10 A16+8 A15+7 Platform=52, immutable pin/baseline PASS, L2 actual Jazzy/Harmonic8.15.0 4/4. Platform #45764157088 / #45764162904 SUCCESS. 자동 Restaurant MVP #45764162911 마지막 조회 in_progress, 전체 제품 통합 PASS 아님. 기존 A17-08 broad cancelled 역사 보존.
P3 artifact15090787547 ZIP 726d7f8ec1d053402fcd64bc5d0be75a73db41d95086247a33de4d382a1a95c6, raw525549fd7d5e12a0c8c28e397aab555d7ed0a423fc420d20487c8bd74d3674aa, diag71dd06b5f2b0c4a2afd82ac8585701c0f22fb7ab9b6098032a1c284a8a6e9840; 9+60+26=95/95. P4 artifact15091033606 ZIP84e06385d881acc3f948eb90fc535aedf291b7cdf6ddca7fcc4bcb01ac9082c9, rawc7db794cf03ae9ff45c170db21e037907a916f7d0eb70dbf6213d18176316750, diag7e092727e1c1b198e60ff5de67ade0f452fb0efd2bf6e49a3c7f6a9886495d8a; 9+60+32=101/101. Both independently downloaded, rehashed ZIP/CRC, sidecar, manifest/path/identity check, raw pose/ECM/native/ROS/trigger/actual RGB+CameraInfo checks and relative displacement/path recomputed. P4 independent review JSON SHA7d7ebb0cf2eeebf76b289ccc99c48ae05abdeb16682910a6cedab640a4cd8c32. P4 gate receipt P3 source/raw/diag and core_unchanged true, four actual BBOX overlay PNG and four-row worksheet blank. Review files are private, not GT masks, no new data from review copies.
8 unique Layout/signature/pixel hash, 6 Family (F1..F4 retained, F5,F6 new), each t0 exactly2s, same-stamp CameraInfo, actual support pair at t0, pre-t0 settle, 1ms through12.3s, each 500 torque commands linked upper registered link. 439554 poses, 439554 ECM rows, 4000 torque commands. All34 owned processes actual SIGINT only, exit0, no remaining process group; GUI first per phase PASS, others headless NOT_REQUESTED. Cloud inherit software, no Owner GPU claim.
|Scene|Family|signed X mm|upper max m|path m|observation|data/cleanup|
|---|---|---:|---:|---:|---|---|
|L18-03|F3|-97|0|0|POSITION_MAINTAINED|PASS/PASS|
|L18-04|F4|+87|1.0004537607729|1.166514545765118|LARGE_DISPLACEMENT|PASS/PASS|
|L18-01|F1|-92|0|0|POSITION_MAINTAINED|PASS/PASS|
|L18-02|F2|-112|0|0|POSITION_MAINTAINED|PASS/PASS|
|L18-05|F3|0|0|0|POSITION_MAINTAINED|PASS/PASS|
|L18-06|F4|-87|0|0|POSITION_MAINTAINED|PASS/PASS|
|L18-07|F5|-29|0|0|POSITION_MAINTAINED|PASS/PASS|
|L18-08|F6|+47|0.0000032135865896317023|0.000006806510443619095|OTHER_OBSERVED|PASS/PASS|
L18-05 actual signed X -1.2638304093569777e-10m, QA05 epsilon within zero. L18-07 actual full containment margin0.0009999963428622693m; L18-08 -0.002000006419889122m, near-boundary geometry confirmed, both initial support and settle PASS. L18-08 small nonzero response retained under current descriptive thresholds <=1e-8m maintained / >=.1m large / otherwise other, not an unstable label. New Cloud observation6 maintained/1 large/1 other; prior Owner 12 counts8/4. Combined reference 14/5/1 only descriptive cross-environment comparison, not an approved dataset. Existing 4 families nominal-center × actual signed X cell coverage9→13/24, 11 remaining; new family cells not included in that denominator. Fixed +Y conditional response only, direction effects not universally solved. 
Contact after t0 ECM positive286853, empty73647, exact native ECM intersection286853, native/ROS intersection168445, native-only118408, ROS-only0. Observed multiset counts, not full delivery or loss rate; production contact HOLD. GT UNKNOWN_HOLD, no human approval/training eligibility. A15/A16 cleanup FAIL history preserved. 
## Owner one-shot release
Exact execution f1bf400f9b9ef6f554f90b92d92e1e63aeffb049. A17-08 profile wsl_d3d12_retention_v1, existing exact WSL/Jazzy/Harmonic/Mesa/WSL libraries allowlist, no global LD_PRELOAD, no CPU fallback. User GUI default, visual separate. --phase all runs phase1 then phase2 only after phase1 actual 4/4 data/cleanup/profile + outer/inner hashes, source/registry/layout validation. A18 phase1 core is exact same code as P3 fd44; new wrapper and gate verified in P4 Cloud and L0. Actual combined Owner route and WSL2 positive prior gate are not yet executed; negative gate tested, actual archive gate only at Owner. If phase1 failure, no phase2; preserve partial and do not retry accepted scenes, review first. If phase1 already successfully run with P3 pin, use phase2 --prior path (with same-basename sidecar) to avoid repeat. 
```bash
(
set -Eeuo pipefail
PIN=f1bf400f9b9ef6f554f90b92d92e1e63aeffb049
curl -fsSLo "$HOME/a18_pilot_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/a18_pilot_bootstrap.sh"
SMARTDISH_A18_SOURCE_SHA="$PIN" bash "$HOME/a18_pilot_bootstrap.sh" --phase all --gui
)
```
Submit both generated_a18_phase1 and generated_a18_phase2 each a18_pilot_evidence.tar.gz + .sha256 and a18_pilot_diagnostics.tar.gz + .sha256; if failure only existing evidence, early bootstrap diag if generated. No new A15/A16 physical run, no forced reattempt. P5 Owner NOT_RUN, P6 B handoff contract ready but actual final transfer pending Owner. B QA05 exact pins unchanged, new adapter required. No main/Platform/E/other branch change, PR56 Draft. 
