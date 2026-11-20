# S5-LIVE-01 — 공개 CI + 강사 WSL2 단일 세션 통합 라이브 개발

- 기준 main: `b478e8508d60e74e701f347e54b8ba0ec1724cbc`.
- 원본 성공 보존: S2-MAP-01/02, S2-MAP-03 81.33% 실제 SLAM 지도, 새 지도 S3-AMCL/Nav2 배달·복귀, S4 메뉴 속도/Collision Monitor STOP, 강사 NO_GOAL GUI L3.
- 이번 단계는 이미 성공한 각각의 기능을 다시 구현하지 않고 **동일한 실제 Gazebo 세션**에서 연결합니다.

## 설계

1. 개선 지도 원본 SHA/World SHA/Free 연결성 검사 및 공식 AMCL 자동 초기 위치. `/initialpose` 수동 발행 금지.
2. 기존 `ci_s3_amcl_smoke.py`를 `--s5-integrated`로 재사용: 실제 센서·Nav2 Lifecycle 확인 뒤 NavigateToPose TABLE_3 (NORMAL)와 PICKUP_RETURN (SOUP), 실제 Odom 속도 비교.
3. 동일 세션에서 기존 S4 물리 원통 장애물 STOP, `/scan`→`CollisionMonitorState.STOP`→`/cmd_vel` 0→`/odom` 정지.
4. 강사 GUI에서 `owner_wsl2_once.sh live` 재사용. Goal 안전 승인 2단계: `--approve-goals` CLI + 터미널 `YES-S5-LIVE-GOALS`; 실패/취소 시 Goal 없음.
5. 기존 RTF/GPU 계측과 단일 진단 ZIP에 S5 JSON 및 최초 실패 요약 추가. GUI는 실제 실행 후 Ctrl+C까지 유지.

## 검증/출고 게이트

- L0: Python/Bash 계약 및 승인 차단 RED→GREEN.
- L1: 공개 CI 공식 Jazzy/Harmonic/ROBOTIS Waffle Pi/Nav2 빌드.
- L2: **같은 실제 Gazebo 세션**의 두 Nav2 Action, 메뉴별 실제 Odom 속도, 물리 장애물 CM STOP·필터·Odom 정지. 모든 증거가 증명됐을 때만 `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS`.
- 강사 WSL2 GUI L3: 사용자 현장에서만 검사. CI GREEN을 GUI L3 PASS라고 주장하지 않음.
- 스크립트 외 새 Planner·SLAM·Supervisor·안전 알고리즘/드라이버는 없음.

## 개발 이력

- S5 브랜치 `feature/s5-live01-integrated-20261120` 생성. 원샷·원본 S3/S4 실증 실행기 재사용, 실증 코드·CI·안전 승인 회귀·가이드만 최소 수정.
- 첫 CI 판정은 `S5_CI=HOLD`이며 실제 L0/L2 결과를 이 보고서에 추가한 뒤 승인/병합 결정.
