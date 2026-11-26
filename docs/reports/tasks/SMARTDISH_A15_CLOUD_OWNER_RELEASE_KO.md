# A15 — 실제 Cloud 파일럿 검증 및 WSL2 Owner 출고 (교육용)
 
## 고정 기준
Execution SHA 65f0fa6fbf140f8fd2553ce2d8fdf3f515918695; platform b8ef3998973a5e33b67ddd5c5b63c3c89b837840; prior A Owner A14 7c6e950..., B QA c7cce70. A15 STATIC_TRAY_COMMON_TORQUE_PILOT, not real moving robot, not DACON equivalence. No existing A14 rerun.
 
## 실제 CI 이력
- #45737419258 L0 8/8+platform7/7+pin fixture PASS, L2 Git dubious ownership before C++ build or physical collection. SDFormat14 unsupported signed int64 parameter type identified during review (not observed compile failure), fixed in 2a530cd.
- #45737558826 L2 same CI container ownership failure; no real scenes executed. CI-only exact checkout safe.directory configured via process-local GIT_CONFIG, not global Owner changes; dependency aggregate narrowed.
- #45737733210 exact pin completed SUCCESS; L0 8/8 + platform7/7 + real Git pin fixture; L2 actual Harmonic C++ build, four actual pilot scenes, first software GUI, other three headless; all data PASS and all owned processes exit0. Common push #45737733208 and PR #45737741405 SUCCESS, E #45737741366 report HOLD. Auto full MVP #45737741379 was in progress at initial query, not part of scoped pilot gate.
 
## Actual raw recheck
Artifact #15080076270 downloaded to local container. ZIP SHA256 d49ca0955a26ab8b8a023e658f86632b1660a79f131265e9521d856aa5c23583 matches GitHub metadata; CRC all PASS. Outer TAR SHA a8d6badf1cec39cf6605bb4b4c064904bdcd203089ccd0d4a49702d365803936 matches log and 15/15 manifest. All four inner archives independently hashed, 61/61 manifests. Independent offline raw recomputation: actual 1ms 4-entity pose grid, source IDs and same iteration, relative displacement/path, component refresh grid, ROS exact-stamp positive pair stats, actual torque command trace; all match. Review JSON SHA ba40f9ee88b45c7c7a89b651f48eb6b7004459ffc670dcd2c73b9722a2bc643a. Actual RGB sheet checked: all trays loaded, upper/lower plates visible in frame; expected partial lower plate occlusion, top-only camera, not multi-view data. No human label approval.
 
|Scene|Raw SHA256|Manifest|Upper max displacement m|Upper cumulative path m|GUI|
|---|---|---|---:|---:|---|
|L15-01|a3f6fe4ea77aa047619a1e47add0b2a1e6f5628c600f7fdf46bdc314232861d5|16/16|0|0|PASS|
|L15-02|b1c8f59f955301debe9bee91766a04e0f25c12465dad9992cd358fe2779e6ca3|15/15|0.8198921435|1.0207173091|NOT_REQUESTED|
|L15-03|a679cfe9ee72f2236d91d6a05301695958b24766d49b385be7701063e0de4d09|15/15|0|0|NOT_REQUESTED|
|L15-04|5c5baeba58f9ba49001a1e45b9d47eaf51bb27d6ead16ccadbccd6bbf63302fd|15/15|0.7811042801|1.0323368975|NOT_REQUESTED|
 
All RGB 640x480 t0=2.000s, actual camera info skew 0, exact positive tray/lower and lower/upper at t0, 200ms settle displacement and rotation recorded zero for all. Same 500 torque command steps 2.200–2.699s, 0.12 Nm world-Y, command not measured wrench. Actual pose through 12.300s (10301 points per entity, 41204 rows/scene in interval), 41200 contact refresh rows each (164800 total), ROS raw callbacks 25832/39237/27620/38386 (131075 total). Two centered layouts unchanged, two offset upper dishes ended outside tray at floor. 2 geometry families, four layout IDs independent of scene ID. Contrast verified, not GT or product threshold. Full contact transport/engine registration and generalization remain HOLD. Native WSLg and historical teardown -11 not resolved by Cloud.
 
## Owner WSL2 one shot
Only A15 four new scenes, no A14 smoke repeats. Existing A14 and product pins preserved. GUI default all scenes; sensor server inherited GPU, GUI software profile. New exact-pin independent home workspace. No installs/global modifications, fail fast. Submit a15_pilot_evidence.tar.gz + .sha256 emitted by script. If nonzero, submit partial evidence, do not automatically rerun. Owner physical data, GUI and cleanup separate; historical GT HOLD stays. User visual inspection separate. 
```bash
(
set -Eeuo pipefail
PIN=65f0fa6fbf140f8fd2553ce2d8fdf3f515918695
curl -fsSLo "$HOME/a15_pilot_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/a15_pilot_bootstrap.sh"
SMARTDISH_A15_SOURCE_SHA="$PIN" bash "$HOME/a15_pilot_bootstrap.sh" --gui
)
```
Expected A15_PILOT_DATA_AND_CONTRAST_PASS_GT_HOLD, A15_EVIDENCE_ARCHIVE, A15_EVIDENCE_SHA256. WSL2 NOT_RUN until user evidence submitted. No main or E merge. After Owner: B independent Q01–07 audit; human labels and full contact health remain separate, then pilot expansion only after quality approval.
