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

## Cycle 01 — L0 RED→GREEN 후보
- RED: [Run #44560051088](https://github.com/silverbjin/samsung_AXI/actions/runs/44560051088), pytest 1 FAIL / 4 PASS. 실패 원인은 table3 좌표 y=0.3800000000000001과 0.38의 Python 부동소수점 정확 비교. 지도 SHA·PGM 연결·출고 조건 검사는 성공.
- 최소 수정: 해당 좌표 단정문 하나만 1e-9 오차 비교로 수정. World→map 변환, MAP YAML·PGM·manifest 및 Nav2 변경 없음.
- 실제 L0 재검 GREEN과 L2 AMCL 증거 전에는 S3=NOT_VERIFIED.

## Cycle 02 — S3 L2 RED: Nav2 PythonExpression lowercase false
- [Run #44560469349](https://github.com/silverbjin/samsung_AXI/actions/runs/44560469349): L0 saved-map/PGM/manifest SHA PASS, L1 Jazzy Nav2 build PASS, 실제 Gazebo S3 Launch 시작 직후 Exit 1.
- 축약 원본 `ci-s3-summary.txt` 증거: `[ERROR] [launch]: Caught exception in launch ... name 'false' is not defined`.
- 공식 Nav2 Jazzy `nav2_bringup/launch/bringup_launch.py`가 `IfCondition(PythonExpression(['not ', slam, ' and ', use_localization]))`로 bool을 PythonExpression에 넣는 사실 확인. 기존 `navigation.launch.py`는 `slam:'false'`, `use_composition:'false'` 등 소문자 전달로 NameError 가능.
- 최소 수정: 해당 launch_arguments bool 문자열만 Python의 `False`/`True`로 교정. World/SLAM/Map/AMCL/ROS 물리 패키지 수정 없음.
- 재검 전 S3 AMCL L2=NOT_VERIFIED, S2 MAP02 main PASS 유지.

## Final AMCL-01 GREEN (2026-11-20 KST)
- [Actions #44561573820](https://github.com/silverbjin/samsung_AXI/actions/runs/44561573820) L0 released-map PGM/SHA/frame PASS, L1 Jazzy official Nav2 build PASS, L2 actual Gazebo Map Server+AMCL+TF+NavigateToPose action server readiness **PASS/NO GOAL**.
- Evidence artifact `samsungaxi-s3-amcl-verified-44561573820`: map PGM sha256 b20bebc872145fa674315757c61e5bb10444eb4c5067ac34d5948d679157e8d8, 201×180 cells, scan_count=11, amcl_pose_xy=(0.0068173,0.0366831), covariance diagonal=(0.132142,0.146656,0.082378), map→odom and odom→base TF true, Nav2 NavigateToPose server true, goal_sent=false.
- Result marker `RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL` verified in actual log.
- PR #9 source merged main SHA `2e0b145983b621a3061cca5085fa5b88c87332f7`.
- **S3_AMCL_01=PASS**, S3 actual NavigateToPose+physical Odom delivery and return remain NOT_RUN; local WSL2 only final GUI acceptance after CI.
