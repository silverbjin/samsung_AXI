# A-PROD-04 E 인계서 — 검토용 HOLD (merge/이동 금지)

기준: A ce26a41d0f5f9519b2983e78c7bd4e65d4ffa5cd, Seed 57c5f57b471a92ae11adf1d2432d44aa8640d2ad, E 검수 2dc70622d8dc8b718366e5533cbbc320fd5dbc51, 수정 기능 PIN 870262c8c8fc2c509a25d74d6f8ff28c0133db8e, Waffle upstream 45633014a14e8f438495b532a723e4ad45cbbd31. PR #67 A 전용. E/main/원본 지도/기존 launch/다른 담당 코드 변경 없음. E 승인 20s LOAD/UNLOAD 유지.

## 최초 문제 및 실제 원인 구분
1. E 보수적 검사 원본 map 3구간 HOLD. 실제 지도 픽셀과 SDF geometry audit: 원본 map free 24811 unknown 9781 occupied 1588. full-yaw 반경 0.445477m에서 HOME/T03/DISH_RETURN unknown 1/70/0. 실제 도착 yaw 580mm 정사각형 intersect unknown 0/39/0. 별도 기존 S2-MAP03는 0/10/0. T03 unknown은 회전 과보수만의 문제가 아님.
2. Nominal SDF 기반 후보: 모든 정적 collision geometry를 높이 무관 투영, .10m registration margin 및 셀 여유, 원본 occupied 보존, SDF predicate로만 unknown 변경. 원본 map 덮어쓰기 없음. 후보 free 28472 unknown 1443 occupied 6265; unknown→free 5782. full-yaw static 3구간 connected. 실제 live TF 및 Nav2 경로 확인 전 후보 승인 금지.
3. 실제 tray ±.27m, plate R .245 + .015m centering, 권고 footprint ±.28 + .01 padding. 실제 local/global published 580mm 확인. 로봇 정적 질량 2.0509kg, nominal 적재 2.7109kg, COM z .16796→.24892m, 높이 1.1425m, lidar z .121m, elevated collision 미감지 위험. 실제 이동 안정성 별도.
4. DBG01 lifecycle 순서 RED→GREEN. DBG02 publisher graph 실패; DBG03 실제 194/194 snapshots에서 collision_monitor+docking_server가 /cmd_vel 발행. Docking bypass 구조 확정. 신규 A04 opt-in launch overlay에서 docking remap 두 선언만 변경, installed/repo source 무변경, 45956739176 실제 재검수 결과 확인 필요.

## 증거 및 파일
- Geometry L0 3 tests/실제 SDF 생성: 489d2014fbb532c4c285f61869761428c3abf26b, Run 45954975000 Artifact 15178590920, ZIP dd0aefc3f007f4574b5a69e4d7b0efa0969bae0d9b9c758c8b58153c422f00c0, TAR d7054598dfe83dfad47e513ec172e7baf4242e57af032900e6e9ce4c125649a9. candidate PGM b73920d77e7e40577958b672dbf6a6fcc5e3bb1bcaeb4b018663bc5d101ef87a, YAML a151fcb5866ab592ee1f0d0d065c581a318d6d530e51900ad49217ef44839b37. 정적 회귀 Run 45956739185 success.
- NO_GOAL: 45955654421 Artifact 15178881241/15178333860 (7 ACTIVE, footprint, odom, scan, graph RED); 45956255819 candidate Artifact 15178264825 (actual bypass RED). SHA256 상세는 03_NO_GOAL/DBG03 보고서. Actual ComputePathToPose 및 moving clearance/contact/속도 검증 미완료.
- code: scripts/smartdish_a04_clearance.py, smartdish_a04_no_goal.py, smartdish_a04_launch_overlay.py, A04 전용 workflows/tests.
- B QA schema: a04/static/geometry.json, map_audit.json, world.sdf, overlay/robot.sdf, candidate.pgm/yaml, source_sha.txt, upstream_sha.txt, SHA256SUMS; a04_live/session/evidence.json, launch.log, static/live_nav2.yaml, static/launch_overlay/* manifest/diffs (새 PIN), path_*.json, global_costmap_*.npy, tray.rgb/png (생성된 경우만). 외부 TAR SHA256/ZIP digest/내부 파일 hash 검수.
- B/E 별도 프롬프트: A_PROD_04_B_QA_PROMPT_KO.md, A_PROD_04_E_REINTEGRATION_PROMPT_KO.md.

## 재개 지점
45956739176 완료 결과의 graph/diff/hash 확인. GREEN이면 실제 경로와 등록/지도/물리 여유 검토; 새로운 RED면 해당 첫 실패부터 수정. 모든 조건 충족 후 별도 A moving CI (빈 tray→적재), 실제 contact 관측 범위 및 relative pose 검증. 최종 E adoption 전 E 전용 source 변경/merge 금지. 움직임 승인/접촉 0/최소 clearance/최적 속도는 현재 NOT_RUN. A03 stationary evidence만 재사용. 최종 판정 A_CLEARANCE_HOLD / OWNER_L3_NOT_RUN.
