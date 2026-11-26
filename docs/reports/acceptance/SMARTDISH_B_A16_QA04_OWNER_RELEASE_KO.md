# B-QA04 — A16 신규 독립 검수 및 Owner 출고 원장 (2026-11-26)
A16 Owner acceptance 87b65e3, producer bacc1af4b47b6d1b2d4eb43b2d0223f578d1244e. Actual raw ec3eac2a4af99f0deefa67a44254ea1b07a9fef1ee80cd4a715156105cbb4f15, diagnostics 61cd76bfedd5f3908444e6d6f1bfe9296f5e2a175c0428310812047e26566a65, prior A15 Owner raw 828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05. User visual review completed for A16, not per-scene GT/rights approval. Existing B-QA03 accepted d397bea7cd1ccc0f8ca5dcb3503c313e83405f47 preserved; new stacked branch feat/smartdish-b-a16-qa04 PR52.
## Actual verification
Execution/verifier source b36694d8c243e44147f9f32b9c2189deef1e8f9f. CI #45749553565 SUCCESS: 33 pytest (27 old +6 new), common7, exact Git pin fixture, baseline; dataset contract #45749561586, B adoption #45749561527, platform #45749553459/#45749561591, full MVP #45749561604 SUCCESS. Source-only artifact #15085310466 independently downloaded ZIP SHA caa7a7e7094f05596fe5f077d34bc82cb3a2ef703b718c906e8d4d11ebd96160, CRC and 4/4 manifest, SOURCE_SHA exact. Linux CPU private CLI ran actual three archives, no full repo checkout or WSL2 runner in this audit. First tool-imposed 60s timeout interrupted before result, no code failure or diagnostic produced; process confirmed stopped. One bounded retry (180s cap) exit0 REVIEW_ONLY. No simulation rerun, no false RED. Forced external termination is not a normal CLI exception; cannot guarantee archive on external kill. 
Official QA04 actual output report SHA 8cebb1fbe64de0b5db8acb55aa34f461f7f67c9a7158462cd3ba6289a6ca6eec, diagnostic TAR 7b82b9163e03948e7b1a1c8f11e41da97e9ebe04ece3b63493440b70ed6ea446 external/internal3/3 verified, worksheet8 blank decision/rights/occlusion/reviewer/reason. Private artifacts not committed. A16 raw outer17 inner120 diag57, prior A15 audit actual raw passed with outer15 inner64. Full dynamic t0/CameraInfo/geometry/SDF, FOV, settle, support chain, 1ms pose/metrics, derived velocity/angular velocity, trigger target and registry, ECM and native/ROS multisets independently recomputed. 
## Results
A16 370836 pose rows, 370800 ECM refresh, 4000 commands, exact support2×4+3×4=20. ECM/native positive matched306017; ROS observed104982; native-only201035; ROS-only0, duplicate/order0. Not loss rate, production contact HOLD. 8 server -11, camera-only probe -11; all owned stopped. No stack/root fix. Cloud/Owner identical geometry counted once. A15+A16 12 distinct pixel hashes, 12 layouts, 4 families; 8 observed upper position-maintained /4 large displacement (observations, not labels). aHash near review threshold <=8: all 66 pairs, Hamming distribution 0:22,1:2,2:15,3:14,4:8,5:2,6:1,7:2; 0 exact pixel duplicates. Coarse aHash dominated by common overhead background/tray, not evidence of identical images. Signed support-offset alignment still shortcut concern. Human review and diversification necessary.
|Gate|Verdict|Reason|
|---|---|---|
|Q01|PASS|Exact provenance, safe hash chain, both real sources|
|Q02|HOLD|t0/FOV/settle/support recalculated; user visual complete but per-sample occlusion review not recorded|
|Q03|HOLD|Physical metrics PASS, full contact health unproven; cleanup FAIL separate|
|Q04|HOLD|0 approved GT, rights/decisions blank|
|Q05|HOLD|12 independent layouts, 4 families; near duplicates/offset alignment/domain concerns|
|Q06|HOLD|No approved independent family split; do not count repeated environments|
|Q07|HOLD|No training manifest/C training; t0 RGB only future input|
## Owner runner release
Only read-only offline audit; no Gazebo. Download immutable bootstrap at b36694d8c243e44147f9f32b9c2189deef1e8f9f. Three absolute paths to existing files plus sidecars named by original filenames. CPU-only, independent worktree, platform baseline, exact SHA, private output. Must have Pillow installed, no global GPU changes. WSL2 runner NOT_RUN; do not confuse local CPU actual evidence audit with user Owner runner. 
```bash
(
set -Eeuo pipefail
PIN=b36694d8c243e44147f9f32b9c2189deef1e8f9f
# Set existing absolute paths first (same files submitted):
A16_RAW="/absolute/path/a16_pilot_evidence.tar.gz"
A16_DIAG="/absolute/path/a16_pilot_diagnostics.tar.gz"
A15_RAW="/absolute/path/a15_pilot_evidence.tar.gz"
curl -fsSLo "$HOME/smartdish_b_a16_qa_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_b_a16_qa_bootstrap.sh"
SMARTDISH_B_QA04_SOURCE_SHA="$PIN" bash "$HOME/smartdish_b_a16_qa_bootstrap.sh" "$A16_RAW" "$A16_DIAG" "$A15_RAW"
)
```
Submit b_a16_qa04_diagnostics.tar.gz + .sha256. Next after Owner: per-scene human/rights worksheet; separate targeted A17 teardown camera-only (no A15/A16 repeat; stack and controlled renderer comparison before fix), and B diversity requirement review. No further expansion/real training without approval. Main and E remain unchanged. 
