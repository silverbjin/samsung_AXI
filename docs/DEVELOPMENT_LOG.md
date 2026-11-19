# 개발·디버깅 교육 로그

## Cycle 01 — S0 재사용 점검 → S1 최소 월드 소스 (2026-11-19)

**목표:** AXIA 본류에 영향 없이 레스토랑 World·Waffle Pi를 독립 실행하도록 구성.

**근거:** 공식 ROBOTIS Jazzy `model.sdf`는 `gpu_lidar` + RGB `camera`이며, 브리지 `/cmd_vel`은 `TwistStamped`. 공식 Nav2 Jazzy는 기본 `Twist`; Navigation launch가 Velocity Smoother와 Collision Monitor를 포함함. 기존 AXIA D06 설정은 격리 시험 토픽으로 실제 사용 금지.

**실패 경계(정적 조사):** AXIA D05의 이전 `feature/d05-mounted-rgbd-actor-live-20261113` ref를 재조회했으나 `404 No commit found for ref` 응답. 기존 Branch가 존재한다는 가정으로 설치 스크립트를 작성하지 않고, 조회 가능한 AXIA D08 `rgbd_camera` 구조만 참조하여 독립 로컬 overlay를 설계함.

**최소 조치:** 독립 `restaurant.sdf`와 세 ROS package 구조, 단일 /cmd_vel Bridge YAML 생성. 기본 World는 공식 Waffle Pi SDF 파일을 직접 사용; S2부터만 RGB-D overlay를 생성하는 방식으로 분리. Nav2/SLAM 및 Waffle Pi 바퀴 물리 코어는 개발하지 않음.

**현장 검증:** 이 작성 환경에 ROS 2 Jazzy와 Gazebo 실행 파일 없음. 따라서 World가 WSLg에 렌더링되는지, 실제 주행 성공 여부는 **미검증**. Python 문법 및 SDF XML·토픽 계약의 작은 정적 검사는 `tests/`에 분리.

**다음 경계:** 강사 WSL2에서 `./scripts/restaurant_demo.sh world`를 1회 실행해 S1 GUI+LiDAR+odom을 확인. 실패 시 `logs/world_*.log`에서 첫 에러만 좁혀 수정, S1 성공 전 S2/3 결과를 PASS로 기록하지 않음.

## Cycle 02~ — 현장 최초 실패/수정 내역

아직 없음. 새 레스토랑 Gazebo 실주행 증거가 없어 추정 오류/성공을 기록하지 않습니다.

## Cycle 02 — CI 준비 후보 (2026-11-19)

신규 GitHub `silverbjin/samsung_AXI`의 empty 상태를 GitHub 연결로 조회했다. 현재 로컬 파일에 Actions workflow `restaurant-ci.yml`, 실제 ROS/Gazebo 메시지를 구독하는 `ci_gazebo_smoke.py`, 생성 오버레이 검증 `ci_check_generated.py`를 추가했다. L0 local pytest 5개 및 workflow YAML 파싱은 통과했다. **원격 push/Actions Run은 아직 하지 않았으므로 CI GREEN 증거는 없다.** Headless RGB-D/scan 렌더링은 GitHub runner에서 처음 실측해야 하는 경계다.

## 공통 정책·보고서 색인

| 날짜 | 작업 ID | 보고서 | 검증 범위 |
|---|---|---|---|
| 2026-11-19 | DOC-01 | [공통 보고서 정책 도입](reports/tasks/2026-11-19_DOC-01_reporting_policy_setup.md) | 문서 정적 확인 / GitHub 원격 반영 NOT_RUN |
