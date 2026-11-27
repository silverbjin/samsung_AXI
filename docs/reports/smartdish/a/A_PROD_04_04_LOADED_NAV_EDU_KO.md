# A-PROD-04-04 — 무부하 및 적재 주행 검수 상태

판정: A_CLEARANCE_HOLD / OWNER_L3_NOT_RUN. 실제 NavigateToPose 검수 0건. 무부하/적재 주행과 접촉/최소 clearance/속도 최적화는 NOT_RUN. 기존 A-PROD-00~03 정지 적재/하역 실제 L2 (45949123061, SHA 218ce2bf70cdd21cc4ed47cf4bb70715b6e36684, Artifact 15175289984)만 재사용한다. A-PROD-04에서 재검증하거나 이동 PASS로 확대하지 않는다. 
선행 gate: 실제 CM graph GREEN, 원본 또는 E 승인 후보 지도 실제 ComputePathToPose 성공과 보수적 swept clearance 양수, live TF/world 등록 근거 및 여유, 초기 entity/RGB/clock/odom/scan/AMCL, 실제 이동 중 전 구간 위치/접촉 증거 계획. 동적 접시 고정 금지.
후속 순서: CI 격리 환경의 빈 tray 3구간, 이어 실제 LOAD→이동→UNLOAD. A 기존 physical/Action UUID handle/stop routines 및 wait 10/5s, deadline 20/20s 유지. 각 leg UUID terminal, displacement >.25m, AMCL error ≤.8m, terminal 뒤 1s linear≤.01/angular≤.02; 실제 world pose, relative pose 및 tilt, entity IDs와 unload, 속도/가감속, swept minimum, contact pair/시각/coverage. Contact 센서가 접촉 때만 발행한다면 silence는 0건 증거가 아니다. 실제 환경 장애물 접촉과 접시/트레이 및 바닥/바퀴 의도된 접촉을 구분하고 미관측은 HOLD. A14 연구 코드·branch 변경 없음. D/C 제품 기능 증거 아님.
