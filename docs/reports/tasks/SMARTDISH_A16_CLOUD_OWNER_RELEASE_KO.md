# A16 — 실제 Cloud 검증·WSL2 Owner 출고 원장 (2026-11-26 KST)

## 기준 및 검수 범위
Execution pin bacc1af4b47b6d1b2d4eb43b2d0223f578d1244e; A15 parent ea68e96710b62e982308fe740afeeba6081fd551; B d397bea7cd1ccc0f8ca5dcb3503c313e83405f47; platform b8ef3998973a5e33b67ddd5c5b63c3c89b837840. B Owner diagnostic dea58025451055e709f5bd1a8892ef352d4197756543b9d32598e39bc8026e98 verified outer/inner3; source HEAD not in diagnostic, user confirmation and PR46 comment 7181242168. B product review-only acceptance respected. No A15 physical repeat. A16 stacked Draft #51, parent A unchanged. Full product merge not authorized.
CI #45746842119 SUCCESS; actual L0 A16 10/10, A15 8/8, platform7/7, real Git exact pin and full ancestry/protected paths PASS. Actual L1 ROS Jazzy, gz sim8 8.15.0, plugin and native contact executable built; actual ROS type/QoS snapshots; L2 8/8 PASS. Common push #45746841988, PR #45746848047 and full Restaurant MVP #45746847944 SUCCESS. No actual RED occurred in this A16 execution; no invented debug issue. 

## Independent real artifact verification
Artifact 15083748107 ZIP SHA256 4b865bd4f1094c0fcf6d01f94336ba0524bc79cc2e6b623a9859341427ab25bb downloaded and independently rehashed, CRC checked. Raw outer SHA 8b47b14a81ccb794af5ea63a9e4f5df7f8e44327f0ab485b8fff9bb17ef18b2c, manifest17/17; inner8×15=120/120. Diagnostic SHA bd0749064dab609b06b8ae57fd0b165b15b1241e8a4c8b91d66e90c0989a8685, manifest50/50. Source identity, canonical family/layout, unique trial IDs (8), batch ID (1), PNG file and pixel hash (8 distinct), actual SDF SHA, exact 1ms pose grid, quaternion/relative path/max displacement, trigger and native/ROS stamp/pair multiset independently rechecked. Independent review JSON SHA 93c3e944f04432166d3c60041cc34343a48ae9ca1764b3f0ea3c69b13baabd13. No actual raw or worksheet committed to Git.
t0 and CameraInfo exact 2.000s all; measured settle maxima zero 200ms; actual support pairs at exact t0 2 per F1 and 3 per F2; conservative FOV pass, natural occlusion/user visual review NOT_RUN (not gate). Pose 370836 rows in t0–end, ECM refresh 370800, trigger4000 rows. All 8 independent physical fingerprints vs A15 distinct dimensions/layout, not seed jitter.
|Scene|Inner SHA256|Upper max displacement m|Upper path m|GUI|Cleanup|
|---|---|---:|---:|---|---|
|L16-01|6c710586dfbae0454ef9c09885e8bd87c74826dfbb0b462a88334d923f12de86|0|0|PASS|PASS|
|L16-02|7ba22910ab0967f08dcec57a87af3563f2527a807e340e2bb929dbca907068ad|1.027801423564175|1.1828286062312654|NOT_REQUESTED|PASS|
|L16-03|0095f71c0c234104371e2bf2ce1358ae4c3c3eab3e2491056e932211ea94c608|0|0|NOT_REQUESTED|PASS|
|L16-04|3fff492cbac98d0e2cde8f58a4a925a49d6f21293f6ac0f05eb34d1825d54c49|0|0|NOT_REQUESTED|PASS|
|L16-05|af30b4d4ea84933c1022e89f413b5d55888c4f51b59dcc84584d971592648047|0|0|NOT_REQUESTED|PASS|
|L16-06|077daf02ef02b3c0b7d6d1ddc65ca44328ce4437975ce18a1e54e11d035823a8|0|0|NOT_REQUESTED|PASS|
|L16-07|16404d21445f7fbf48f42622f8063362f371463b52373f94b1bf331c89a9dc94|0|0|NOT_REQUESTED|PASS|
|L16-08|9826cf49280d7c86ae0642de9dea9d41970e791ac9a152e163e0833d7095d386|0.8386881864961306|1.0312261934302895|NOT_REQUESTED|PASS|
All 8 data acquisition PASS; top-dish observable contrast 6 zero/2 large, not approved GT. Center tray group one large/three zero, eccentric tray group one large/three zero; both families one large/three zero. At individual family×center-group intersections not all crossed; positive signed large support offset predicts both large observations here. Thus shortcut reduced for tray center vs outcome but relative alignment/torque direction and limited families remain, no generalized quality PASS. Preserve all layouts and outcomes; no rerun/select to balance. B Q02–07 prior HOLD preserved, new A16 B audit NOT_RUN. 
## Contact/cleanup
Source review gz-sim8_8.15.0 Contact.cc blob 3e1ba71a4e381dabaa983e9d898e02ae53ef163f https://github.com/gazebosim/gz-sim/blob/gz-sim8_8.15.0/src/systems/contact/Contact.cc : PostUpdate while running reads positive components and publishes only nonempty; zero contacts are not emitted heartbeats. Physics.cc maps internal engine IDs to ECM and can omit unmapped IDs; ECM refresh and registry do not prove complete engine registration. Actual 306017 ECM positive steps exact equal native subscriber stamp/pair multisets, 64783 empty steps; 189789 ROS observed subset exact, native-only116228, ROS-only0, duplicate and out-of-order0. Six floor channels silent in both, corresponding ECM empty. Native observed coverage of recorded positive ECM 100% only in these runs; ROS/native observed overlap 62.02%, NOT system delivery or packet loss rate. Bridge/queue/subscriber location and engine completeness unproven, production_contact_health=HOLD. No invented threshold. 
Historical A15 server logs re-read: four SIGINT then -11; no decisive teardown stack; warnings about gz_frame_id, visibility mask and serialization, not proven root. New A16 cloud all 33 owned processes exit0 (5 first scene +4×7) and no group remaining; separate camera-only no-dish/contact minimal probe server/bridge exit0. Cloud llvmpipe does not prove WSLg D3D12 root or native cleanup fix. Owner probe once, independent. No A15 rerun. 
## Owner release
Exact validated execution pin above, not subsequent docs commit. GUI default all scenes, optional --headless. Server inherits GPU, GUI child software. Source checkout fresh, no global config, exact source; shallow owner checks common protected runtime paths against pinned baseline, full ancestry and full protected path equality already proven on exact execution SHA in CI. Owner raw and diagnostics separate private archives with SHA sidecars; bootstrap failures minimal diagnostic. No need to repeat failed scene automatically. Submit both TAR and sidecar pairs; if early bootstrap failure submit its diagnostic and sidecar. Owner visual inspection independent; automatic data gate exact t0/support/FOV and physical evidence, no GUI visual gate. No training label/manifest/split. Owner L3 NOT_RUN. 
```bash
(
set -Eeuo pipefail
PIN=bacc1af4b47b6d1b2d4eb43b2d0223f578d1244e
curl -fsSLo "$HOME/a16_pilot_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/a16_pilot_bootstrap.sh"
SMARTDISH_A16_SOURCE_SHA="$PIN" bash "$HOME/a16_pilot_bootstrap.sh" --gui
)
```
Expected A16_DATA_CAPTURE_8_OF_8_GT_HOLD, A16_EVIDENCE_ARCHIVE/SHA256, A16_DIAGNOSTICS_ARCHIVE/SHA256. B receives new independent adapter schema v2 only after actual Owner source/hash acceptance; human decisions blank. A15/B/C/D/E/main unchanged; no merge. 
