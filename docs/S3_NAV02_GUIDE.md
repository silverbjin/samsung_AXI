# S3-NAV-02 — 실제 출고 지도 기반 Nav2 배달·복귀 실증 가이드

## 검증 범위와 기준
- 기준 로봇: 공식 TurtleBot3 Waffle Pi / ROS 2 Jazzy / Gazebo Harmonic / 공식 Nav2.
- S2-MAP-02에서 출고된 실제 지도 maps/restaurant_map.yaml + .pgm을 재사용하며 WSL2 재매핑하지 않습니다.
- 목표 map 좌표: Pickup (0.00,0.00), Table3 (5.25,0.38), 복귀 (0.00,0.00). 기존 restaurant_world/config/tables.yaml의 Gazebo World 좌표는 Nav2 Goal로 직접 사용하지 않습니다.
- 공식 NavigateToPose Action과 AMCL, TF, 실제 Scan/Odom을 계측. Collision Monitor 등 Nav2 5개 핵심 Lifecycle ACTIVE를 검증한 뒤 Goal 전송.

## CI 검수 파이프라인과 실제 근거
- L0: 출고 YAML/PGM/World SHA256 + 좌표 계약 + 점유 지도 자유 영역 연결 검사.
- L1: 공식 Jazzy/ROBOTIS 소스 고정 핀 + Nav2 파라미터 Overlay 및 ROS 빌드.
- L2: 한 번의 실제 Gazebo launch → MapServer → AMCL/TF/Scan → Lifecycle ACTIVE → TABLE_3 → PICKUP_RETURN. 매 Leg Action status=4, 실제 Odom 이동과 AMCL 목표 오차·Scan 증가를 증거로 기록.
- [S3 최신 main GREEN #44646848087](https://github.com/silverbjin/samsung_AXI/actions/runs/44646848087): TABLE3 Odom 5.257m / 오차 0.132m, Pickup 복귀 Odom 5.219m / 오차 0.126m.
- [S1/S2 main 회귀 GREEN #44646848122](https://github.com/silverbjin/samsung_AXI/actions/runs/44646848122).
- 결과 ZIP: `samsungaxi-s3-amcl-verified-44646848087`, 내부 `generated/s3/nav_delivery.json` 및 `logs/ci-s3-summary.txt`. 원본 Run/SHA를 보고서에 기록해 재현성 확보.

## RED→GREEN 문제 해결 흐름
- 첫 Goal 거절: 액션 서버 발견과 Nav2 Lifecycle ACTIVE는 다름 → 핵심 노드 GetState ACTIVE 검사 추가. [CI01](reports/issues/2026-11-20_S3-NAV-CI01_goal_rejected_lifecycle.md).
- JSON 메타데이터 오류: goal_sent=true인데 kind=no_navigation_goal → 완료 후 종류 식별자 교정. [CI02](reports/issues/2026-11-20_S3-NAV-CI02_evidence_kind.md).
- CI 이중 Gazebo 실행: 첫 AMCL PASS 후 두 번째 실행의 action readiness timeout → 동일 세션에서 pregoal+Goal 결합, 성공 재검. [CI03](reports/issues/2026-11-20_S3-NAV-CI03_duplicate_nav_session.md).

## SAMSUNGAXI WSL2 현장 최종 검수 경계
- 본 단계에서 재매핑, 새 Planner 개발, 로봇 물리 파라미터 최적화는 하지 않습니다.
- CI가 승인한 코드와 YAML/PGM 파일을 동일 SHA로 체크아웃한 뒤 현장 GUI와 실제 이동을 최종 확인합니다.
- 안전한 사전 확인 예: `python3 scripts/s3_map_contract.py .`로 저장 지도의 해시/좌표 검증; `bash scripts/restaurant_demo.sh doctor`로 ROS/Gazebo 의존성 진단.
- 강사 WSL2에서의 GUI 배달 데모, NORMAL/SOUP 실제 속도 정책, 식기 회수 인터랙션은 **아직 별도 현장 인수**가 필요하므로 이 단계의 CI PASS만으로 완료됐다고 표시하지 않습니다.

## 완료/미완료
- S3-NAV-02 실제 Gazebo 저장 지도 기반 Nav2 배달·복귀: CI PASS, main 병합 완료.
- SAMSUNGAXI 전용 WSL2 GUI 최종 인수: NOT_RUN.
- 메뉴별 실제 속도 정책과 서비스 동작: NOT_RUN.
