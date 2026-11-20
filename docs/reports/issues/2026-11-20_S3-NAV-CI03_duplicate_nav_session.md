# S3-NAV-CI03 — 연속 Nav2 두 세션에서 두 번째 Action 서버 준비 타임아웃

- 기록: 2026-11-20 KST
- 최초 RED [Run #44644596110](https://github.com/silverbjin/samsung_AXI/actions/runs/44644596110), 소스 SHA `593d141a4b0a7165fcff48b1f423563929dc1cac`.
- 기존 성공 증거 [Run #44564927414](https://github.com/silverbjin/samsung_AXI/actions/runs/44564927414)의 5.185m 배달/5.214m 복귀와 Action SUCCESS는 독립 원본으로 보존.

## 현상과 근거
- CI 한 Job에서 S3 AMCL NO-GOAL 전체 Gazebo launch를 실행한 뒤, 종료하고 NAV-02 전체 Gazebo launch를 다시 실행하는 중복 구조.
- 첫 launch: 실제 지도 MapServer/AMCL/TF/Action ready PASS.
- 두 번째 launch: `S3_AMCL_TF_OR_NAV2_ACTION_NOT_READY` timeout 160초. AMCL=(-0.01227,0.02584), map→odom=true, odom→base=true, 실제 Scan=123.
- Action 준비 전 차단이므로 Goal 전송이나 물리 주행 실패라고 해석하지 않음. 종료 시 SIGINT로 발생한 exit -2는 후행 프로세스 종료 로그임.

## 원인 분리와 제한
- 지도 SHA, 저장 Map, 실제 Scan, AMCL Pose 및 TF가 정상이라는 증거로 Map 손상·SLAM 실패 가설은 배제.
- 두 번 연속 Nav2 실행에 따른 종료·DDS 발견·Lifecycle 경합은 가능한 원인이지만, 기존 증거에서 정확히 어떤 Nav2 내부 전환이 정체되었는지는 확정되지 않음.
- 두 차례 Launch는 제품 요구사항이나 S3-NAV-02 인수 기준에 필요하지 않은 **중복 CI 세션**이라는 구조적 비효율.

## 최소 변경
- NAV-02 및 main에서는 단일 `ci_s3_amcl_smoke.py --exercise-goals` 세션 안에서 Map/AMCL/TF/Action 사전검사, 5개 Lifecycle ACTIVE, TABLE3 배달, 픽업 복귀까지 수행.
- 독립 NO-GOAL 모드는 S3-AMCL 전용 브랜치 조건으로 유지. SLAM, Nav2 Planner, Collision Monitor, Robot SDF, 저장 지도 및 물리 안전 기준은 변경하지 않음.
- 향후 문제가 발생하면 Lifecycle 최근 전환을 `NAV2_TRANSITIONS_LAST_60` 항목으로 남기도록 축약 로그 개선.

## GREEN과 결과
- [Run #44646024902](https://github.com/silverbjin/samsung_AXI/actions/runs/44646024902): L0/L1/L2 PASS. 실제 배달 Action SUCCEEDED / Odom 5.232m / 오차 0.198m; 복귀 SUCCEEDED / 5.244m / 0.026m.
- [Run #44646848087](https://github.com/silverbjin/samsung_AXI/actions/runs/44646848087): main 동일 통합 PASS. 배달 5.257m / 0.132m; 복귀 5.219m / 0.126m.
- PR #10 병합 SHA `e2e7cf04e281866fec123629d0b90a1191359c22`, 사건 해결 판정은 **불필요한 중복 기동 제거 + 한 세션 반복 실증 GREEN**.

## 교육용 교훈
- CI 재현성 문제를 SLAM/경로 알고리즘 문제로 확장하지 않습니다. 먼저 한 테스트가 몇 개의 ROS launch·DDS 세션을 열고 종료하는지 확인합니다.
- 원인을 확정하지 못했다면 가설로 기록하고, 불필요한 세션 구조를 제거한 뒤 실제 센서·Action·Odom 증거로 새 회귀를 검증합니다.
