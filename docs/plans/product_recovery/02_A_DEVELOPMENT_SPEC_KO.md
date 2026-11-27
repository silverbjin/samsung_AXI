# A 담당 — 실제 식기 배치·로봇 트레이·물리 적재/하역 명세
[공통 계약](00_COMMON_CONTRACT_KO.md) 필수. 브랜치 feat/smartdish-a-product-collection: E 공통 seed에서만 분기. 기존 A14~18 데이터 연구 브랜치와 분리.
## A-PROD-00 읽기 전용 감사
PR #35 S7 시작 식기, #45 A11~13 main 병합 완료. scripts/s7_scene.py, scripts/s6_scene.py, navigation.launch.py(world_file), scripts/smartdish_tray_camera.py, scripts/smartdish_tray_world.py, config/smartdish_tray_bridge.yaml, smartdish_robot/navigation_adapter.py, table_poses.yaml 재사용. A11 optional robot SDF는 camera-only prototype; 실제 tray 설치 및 시야 미검증. A14~18 추가 물리 연구는 필요한 검증된 함수만 E 승인 후 최소 이식(일괄 merge 금지).
## A-PROD-01 시작 식기
원본 restaurant.sdf 및 지도 변경하지 않고 generated world_file을 생성. S7 table_3/fixture 좌표와 실제 Gazebo 엔티티/시야 검증. stacked=1 stack, empty=0 negative test. S7 static fixture는 초기 시각 상태에 한정; 동적 식기 형상으로 전환 시 동일 stack_id/수량/영수증. 중복 스폰 금지. L0 XML/hash + L2 actual startup entity/PNG.
## A-PROD-02 장착 트레이 및 카메라
공식 Waffle SDF의 opt-in 제품 오버레이 생성; tray visual/collision/inertia 및 카메라 mount는 robot-relative, 실제 640x480 5Hz top-view. 기존 collision/inertia 원본 보존, 신규 부품 물리값/충돌·footprint/CM 영향 기록(변경 필요 시 E 승인 및 회귀). Gazebo sensor render→ROS bridge actual rgb8/bgr8 RELIABLE. 실제 robot 움직임에도 tray/camera 상대 pose 유지, 식기가 FOV에 포함되는 CI evidence PNG/geometry; 사용자 육안 최종 QA. /clock 1, independent station 금지.
## A-PROD-03 실제 적재/하역 및 캡처
별도 A 소유 controller (후보 smartdish_robot/dish_transfer_node.py, tray_capture_node.py, product SDF generator). D 요청 수신, 실제 Nav2 terminal+stop receipt 확인 후 가상 직원 transfer: Gazebo entity pose/attach 또는 제거+생성 트랜잭션. 동적 식기가 로봇에 따라 이동해야 함; 고정/attach 구현이면 실제 흔들림 검증이 아니라 고정 적재 시뮬레이션이라고 표기. 단순 visual teleport만으로 ACK 금지. LOAD 확인: table_count=0, tray_count=원본 수량, relative pose/vel 검증; UNLOAD 확인: tray_count=0, 반환 위치/제거 receipt, 동일 stack_id. 실패 중간상태 journal 및 복구, 재요청 idempotent, 신규 goal 금지. A만 cancel exact UUID 및 stop 검증. D의 capture_request 뒤 min_sim_stamp_ns보다 새로운 frame을 선택하고 actual PNG/RGB hash receipt 발행. A는 AI 결과/라벨 생성 금지.
## 검수/인계
L0 SDF/좌표/transaction/cancel/ID tests; L1 actual DDS ACK/duplicate/failure; L2 단일 world 실제 LOAD→이동→UNLOAD 및 capture 1, empty/stop/load/camera/unload fault. 테스트용 엔티티 API 실제 성공 및 pose 관측 필수. 실제 Nav2 이동 중 상대 pose 확인은 E 통합과 공동. CI only, owner 재실행 요구 금지. 결과 SDF manifest, transfer/capture receipt, actual pose time series, PNG SHA, run_id/source SHA, PR head 및 교육 MD를 B/C/D/E에 전달. 본문 경로 후보는 기존 패키지 구조 검토 후 확정.
