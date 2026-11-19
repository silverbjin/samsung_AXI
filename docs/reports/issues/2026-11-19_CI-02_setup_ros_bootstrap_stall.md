# CI-02 — GitHub Actions ROS 환경 초기화 장기 대기 (진행 중인 문제)

- 날짜: 2026-11-19 KST
- 저장소: `silverbjin/samsung_AXI`
- 영향 범위: L1+L2 Job의 *사전 환경 초기화* (로봇 코드나 Gazebo 실행 이전)
- 상태: **해결안 구현·재검 대기**, 원인 확정 전 PASS 금지

## 현상과 증거

- 이전 main Run [#44444854114](https://github.com/silverbjin/samsung_AXI/actions/runs/44444854114)의 L0는 PASS인데 L1 Job은 `Install ROS 2 apt sources (Ubuntu 24.04)`(setup-ros action) 단계에서 장시간 `in_progress`.
- OWNER-01 PR Run [#44447412014](https://github.com/silverbjin/samsung_AXI/actions/runs/44447412014)에서도 L0 PASS, L1은 동일 초기화 단계에 진입한 이후 완료 미확인.
- 이 시점까지 L1 `colcon`이나 L2 Gazebo는 실제 시작되지 않았으므로 로봇 소스 실패라고 판정할 증거가 없음.

## 진단 가설과 공식 근거

[ros-tooling/setup-ros](https://github.com/ros-tooling/setup-ros) 공식 문서에는 **bare-metal GitHub apt mirror의 `apt-get update` 불안정성**과 **ROS가 사전 설치된 Docker 컨테이너 사용 대안**이 명시되어 있다. 해당 원인이 이번 현상의 *가능한 원인*이지만 실제 stderr 로그/완료 결과는 확인하지 못해 확정하지 않는다. 공식 Docker Hub `ros:jazzy-ros-base-noble` 이미지도 확인했다.

## 최소 해결안 (새 개발 기능 없음)

L1+L2 Job만 공식 `ros:jazzy-ros-base-noble` 컨테이너로 실행하고 `setup-ros` action을 제거한다. Python/ROS/Nav2/Gazebo 테스트·코드·검증 표식은 그대로 유지하며, 컨테이너가 root로 실행되는 apt 명령에만 `sudo`를 제거한다. L0는 기존 호스트 runner를 유지한다.

## 검수와 판정

- Workflow YAML 및 정적 테스트: **검사 예정**.
- 컨테이너에서 ROS deps 설치/L1/L2 실제 성공: **NOT_RUN** (신규 Actions Run 판정 필요).
- WSL2 Owner GUI: **NOT_RUN**.

정량 성능 검증이나 별도 Docker 이미지 빌드를 추가하지 않는다. 외부 컨테이너는 CI *실행 환경*만 바꾼다.
