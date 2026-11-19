# OWNER-01 — 강사 WSL2 원샷 실행기 개발·출고 전 검수

- 날짜: 2026-11-19 KST
- 범위: 신규 공개 저장소 `silverbjin/samsung_AXI`의 S1 월드·센서 강사 실행 경로. S2/S3/S4는 기존 모드만 연결하고 실제 완주를 주장하지 않음.
- 원격 기준선: `main` `1ab3d310c50dadb406f7a5964f3ab8641c9a2f2a` (검토 시점)
- 변경: `scripts/owner_wsl2_once.sh`, `scripts/restaurant_demo.sh`, `tests/test_owner_wsl2_once.py`, CI L0 테스트 선택, README.

## 왜 필요했나?

기존 `restaurant_demo.sh`는 **작업공간을 사용자가 준비한 경우**만 바로 실행 가능했고, S1 `world` 모드는 RGB-D overlay를 생성하지 않아 L2와 WSL2 시작 경로에 차이가 있었다. 교육 현장에서는 매번 다른 버전을 실행하는 일을 피하기 위해 SHA 고정된 단일 진입점이 필요하다.

## 관찰 → 분석 → 최소 변경

1. 공식 `world.launch.py`에는 `robot_sdf` 인자가 있으나 기존 S1 실행기에서 제공하지 않음. L2 CI는 생성된 RGB-D 모델을 지정해 사용함.
2. 업스트림 `turtlebot3_simulations`의 Jazzy HEAD가 갱신될 수 있어 CI와 현장 원본이 달라질 수 있음.
3. 단일 원샷을 추가해 GitHub 저장소에서 **정확한 SHA**를 가져온 후 기존 실행기만 호출함. 현장 스크립트와 CI의 ROBOTIS PIN을 동일한 `45633014a14e8f438495b532a723e4ad45cbbd31`로 고정함.
4. 실행 모드 `world`에서도 RGB-D overlay를 생성하도록 한 군데 수정. 별도 Planner, AI, 제어기 구현은 추가하지 않음.
5. 작업공간 오염·오류 origin·비WSL·비Ubuntu24.04·ROS 미설치·GUI 미설정 상태는 명확한 `BLOCKED`로 종료하도록 함. 남의 프로세스를 죽이는 `pkill`은 사용하지 않음.

## 사전 검증

- `bash -n scripts/*.sh` 및 개별 원샷/핵심 실행기 Bash syntax 확인: **PASS**.
- `python3 -m compileall -q scripts src tests`: **PASS**.
- `python3 -m pytest -q tests`: **10 passed** (ROS 없는 정적/계약 검사; 아래 L1/L2와 혼동 금지).
- World SDF XML parse: **PASS**.
- 실제 GitHub Actions PR L0/L1/L2: **NOT_RUN** (PR 게시 및 Run URL 확인 이후 기입).
- 강사 WSL2 Gazebo/WSLg/주행: **NOT_RUN**.

## 검수 범위 및 남은 판정

**`OWNER-01_STATIC_PASS; OWNER-01_REMOTE_CI_PENDING; RESTAURANT_ROBOT_MVP=NOT_RUN`**.
L0/L1/L2가 정상 완료되기 전에 원샷을 공식 `main` 출고본으로 홍보하지 않는다. L2는 NO_GOAL로, 실제 배달·복귀의 근거가 될 수 없다. GUI 최종 인수는 Owner WSL2에서 1회 수행한다.

## 교육용 회고

이 단계에서는 신규 기능 자체보다 **CI에서 검사한 입력과 강사 PC에서 실행하는 입력이 동일한가**가 중요하다. 한 번 검증한 소스 SHA를 고정하면 현장 오류가 로봇 코드인지 실행 환경인지 범위를 좁힐 수 있다. 정적 PASS를 Gazebo 실제 PASS로 승격하지 않는 것이 교육에서 요구사항과 증거의 차이를 설명하는 핵심이다.

## CI 환경 이슈 추적

PR L0가 PASS인 동안 L1의 setup-ros 초기화가 장시간 미완료되어, 공식 권장 ROS base container 전환을 **동일 검증 Job의 최소 환경 수정**으로 적용했다. 원인 확정 및 GREEN 증거는 [CI-02](../issues/2026-11-19_CI-02_setup_ros_bootstrap_stall.md)에서 별도 추적한다.
