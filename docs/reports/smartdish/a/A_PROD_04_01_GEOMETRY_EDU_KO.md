# A-PROD-04-01 — 실제 로봇 장착 외형 및 질량 감사 (L0)
## WHAT / WHY
A-PROD-04: E #66 @2dc70622, A @ce26a41d(20s contract), Seed 57c5f57b. E의 unknown-aware screen HOLD를 검토하되 footprint 축소 금지. Waffle upstream 45633014a14e8f438495b532a723e4ad45cbbd31 고정. 실제 생성 robot/world, 기존 plate SDF generator 사용.
## HOW
scripts/smartdish_a04_clearance.py는 model/link/collision pose를 4x4 rigid transform으로 합성하고 box/cylinder/sphere의 보수적 3D AABB를 계산. 미지원 shape/relative_to/nested model/dynamic world 발견 시 중지. 실제 관성 행렬 회전 및 평행축 정리 적용. 물리 collision 삭제/고정 없음.
- base x[-.1965,.0685] y±.1325 z[.0035,.0925] m. wheel y max .1531m. tray x/y±.27, z[.415,.445] m; mast x[-.2675,-.2525], y±.0125, z[.430,1.130]; crossbar x[-.26,0], y±.0125, z[1.1175,1.1425].
- plate collision cylinder radius .245, height .037, mass .22 kg each; centering 15mm yields max radius .260m (nominal upright, dynamic tilt/shift not yet measured).
- actual SDF inertial aggregate empty 2.05090748 kg, COM [-.05598898,0,.16795814] m, diag I [0.1731753,0.1786636,0.1087504] kg m²; nominal centered loaded 2.71090748 kg, COM [-.04235785,0,.24891909], diag I [0.2389734,0.2460270,0.1301238]. Computed from original evidence; not measured load motion.
- LiDAR z=.121m model, tray z=.43, upper envelope 1.1425; scan cannot observe high-only collisions, S7 stack six elevated cylinder collisions not intersecting scan plane. Project all static collision geometry, including high obstacles. Dynamic/real environment overhang detection not guaranteed.
- Candidate square ±.28 + .01 padding = ±.29m, full-yaw radius sqrt(2)*.29=.410122m; static grid adds half diagonal .035355 => .445477m. 10mm geometric margin before padding, 20mm after. No claim of adequacy under tilt/slip. Keep geometry and conservative footprint.
## Actual CI
489d2014fbb532c4c285f61869761428c3abf26b / [45954975000](https://github.com/silverbjin/samsung_AXI/actions/runs/45954975000) geometry job 140359230292 SUCCESS; 3 L0 tests, actual fixed upstream + S7 generated robot/world. Artifact 15178590920 ZIP sha256 dd0aefc3f007f4574b5a69e4d7b0efa0969bae0d9b9c758c8b58153c422f00c0; actual downloaded TAR sha256 d7054598dfe83dfad47e513ec172e7baf4242e57af032900e6e9ce4c125649a9, 12 internal SHA256SUMS entries verified. geometry.json robot sha d5488e7fac7e0b6e6d41851ed63bc7049e488f641d4aaec4cc05136d83010573, world sha 914e09c51c55a8f531eb8b95b977def9ed1508cf6d608212f64aabdf5e31a8ff.
## REVIEW
Actual static SDF calculation PASS, no Gazebo collision contact or motion. Need live published footprint/TF, actual path and dynamic contact/pose monitoring. Existing S7 geometry/source unchanged. E owns release.
