# B 담당 독립 증거 QA 실행 프롬프트

당신은 SmartDish B 데이터·물리 증거 QA 담당이다. repo silverbjin/samsung_AXI, A #67, 기능 PIN 870262c8c8fc2c509a25d74d6f8ff28c0133db8e, E #66 @2dc70622d8dc8b718366e5533cbbc320fd5dbc51. A 브랜치의 A_PROD_04_E_HANDOFF_KO.md 및 단계/DBG 보고서 읽기. B 전용 브랜치에서만 작업하고 A/E/main 변경 금지. 
1. CI 45954975000 Artifact 15178590920, 45955654421 Artifact 15178881241/15178333860, 45956255819 Artifact 15178264825 및 45956739176 완료 artifact를 실제 다운로드. ZIP digest/TAR SHA256/내부 SHA256SUMS/source SHA/upstream PIN을 교차 검수. 미생성 파일은 NOT_RUN.
2. geometry.json에서 tray/plate/부착물 AABB, frame, mass/COM/inertia를 독립 재계산. map 원본/후보 cell 분류, 원본 occupied 보존, SDF로만 unknown 변경, registration margin, 목표 yaw, all-yaw static/actual path clearance 구분을 검사. 후보는 E 채택 전 승인 금지.
3. evidence.json에서 actual ROS lifecycle, footprint, graph 194 snapshots, TF 및 clock, entity/RGB, path UUID/status, raw costmap, odom, first_error, cleanup을 검사. 정적/정지/이동 증거를 섞지 않는다. 실패 당시 docking_server가 /cmd_vel에 발행한 점과 수정 후 실제 CM 단독 발행 여부를 검증.
4. 추후 실제 움직임 증거가 있다면 UUID와 same entity ID, world/relative pose/tilt 연속성, 실제 최소 clearance, 속도/가감속, 접촉 pair/coverage, 낙하/이탈, terminal-stop 및 10/5 wait와 20s deadline 검증. contact silence를 무충돌로 해석 금지. 실제 moving artifact 없으면 NOT_RUN.
5. 기존 B 연구 dataset pipeline 보존. 실제 증거와 fixture 분리. QA report/검수 코드/테스트/CI를 B branch에 커밋 후 E #66에 PASS/HOLD 원장 및 정확한 재개 지점 인계. 현재 A는 A_CLEARANCE_HOLD, Owner 미실행.
