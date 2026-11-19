# S3-AMCL-01 — 출고된 실제 SLAM 지도 기반 AMCL/Nav2 개발 경과

- 시작일: 2026-11-20 KST
- 기준 main: 53c34a7e99606b903ee1e2920560a72ae34e3711
- 선행 게이트 S2-MAP-01 실제 SLAM/저장 재로딩 PASS; S2-MAP-02 실제 33.3m/12waypoint 지도 YAML+PGM·SHA256 PR #8 main 병합 PASS.
- 금지: WSL2 재매핑, 별도 SLAM/Planner 개발, 테스트용 가짜 Map을 Nav2로 주입, Goal 전 안전·좌표 무시.
- 최초 핵심 위험: src/restaurant_world/config/tables.yaml은 Gazebo **World** 좌표를 frame: map이라 표기했으나 S2 SLAM 실제 저장 지도는 최초 로봇 스폰을 (0,0) map으로 해석하는 별도 좌표계를 사용.
- SDF world pickup (-2.60,-2.20), table3 접근 (2.65,-1.82) → 잠정 SLAM map pickup (0,0), table3 (5.25,0.38). 이는 저장 PGM free 연결과 실제 AMCL/Gazebo에서 확인되어야 하는 계약이며 단순 명칭 변경으로 성공 주장하지 않음.
- 개발: 지도 YAML/PGM 원본 및 출고 manifest SHA256 검증 + 실제 P5 OccupancyGrid Free 연결·좌표 계약 검사.
- 이어질 검증: 공식 Nav2 Map Server→AMCL→map→odom 동적 TF→Nav2 NavigateToPose 액션 준비 확인. 1차는 NO GOAL, 그 후 배달·복귀는 별도 증거 게이트.
- 현재 단계: 지도 프레임 계약 L0 후보. 실제 Gazebo AMCL은 NOT_RUN.
- 교육 메모: Gazebo World frame과 ROS SLAM map frame을 동일시하면 지도는 있어도 AMCL 초기 위치와 Nav2 Goal이 잘못될 수 있으므로, 출고 지도 좌표·SHA·Free 연결을 먼저 확인해야 함.

## 구현 단계 1 — 전용 S3 CI 사전검사
- S3 전용 브랜치/워크플로로 L0·L1·L2를 검사하여 이미 성공한 S2 전체 33.3m 지도 생성을 재반복하지 않습니다.
- Nav2 헤드리스 런치와 실제 Gazebo Map Server/AMCL/TF/Action 서버 준비 상태를 읽기 전용으로 확인하고 NO GOAL 정책을 준수합니다.
- 현재 실제 Actions 통합 검증 결과 전까지 S3-AMCL=NOT_VERIFIED.
