# samsung_AXI — 단일 GitHub Actions CI / Owner WSL2 최종 인수 정책

**작성:** 2026-11-19. **현재 사실:** 저장소 로컬 기준선은 `efe657d`; GitHub 원격은 업로드 전 조회 당시 **empty**. 이 문서는 CI 구성이 작성되었다는 뜻이지 Actions GREEN이나 Gazebo 구동 성공 증거가 아니다.

## 환경

- CI: GitHub-hosted `ubuntu-24.04`, ROS 2 Jazzy apt, Gazebo Harmonic via official `ros-jazzy-ros-gz`, ROBOTIS `jazzy` SHA `45633014a14e8f438495b532a723e4ad45cbbd31`.
- 최종 현장: Windows WSL2 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / WSLg GUI.
- **공통 코드:** `restaurant_bringup/world.launch.py`, `restaurant.sdf`, Waffle Pi generated overlay, 같은 브리지/토픽 설정 사용. CI는 `gui:=false`; 현장은 GUI `true`.
- CI의 software rendering(xvfb/llvmpipe)과 현장 WSLg GPU는 다를 수 있으므로 CI만으로 GUI 정상 렌더링까지 주장하지 않는다.

## 파이프라인 및 증거

| Job / gate | 실제 확인 | 성공 표식 | 해당되지 않는 주장 |
|---|---|---|---|
| L0 static | compileall, bash -n, xmllint, pytest 5 | `RESTAURANT_CI_L0_STATIC_PASS` | ROS 빌드/GUI/주행 |
| L1 ROS build | 공식 Jazzy 설치, ROBOTIS 핀, colcon build, 패키지 검색, 생성된 SDF/Nav2 설정 계약 | `RESTAURANT_CI_L1_BUILD_PASS` | Gazebo 실기동 |
| L2 Gazebo no-goal | GUI 없는 **실제 Gazebo**에 원본과 같은 World/robot/Bridge 실행, `/clock /scan /odom /tf`, RGB-D depth/points에서 유효 메시지 각 1회 | `RESTAURANT_CI_L2_GAZEBO_SENSORS_PASS_NO_GOAL` | 지도·AMCL·Nav2 Goal·안전 정지·GUI·완주 |
| L2 Nav2 주행 (후속) | 실제 SLAM 지도 또는 적격 map 생성·재로딩, 실제 NavigateToPose→odom/Result, 복귀 | 현재 `NOT_RUN` | map 없이 fake PASS 금지 |
| L3 Owner (최종) | 강사 WSL2 GUI에서 M1~M8 실제 완주 1회 및 종료 | `RESTAURANT_ROBOT_MVP=DEMO_PASS` | CI 결과만으로 PASS 금지 |

L2가 GPU headless 환경에서 실패하면 Gazebo 센서 실패 / 그래픽 환경 실패를 첫 로그로 구별하고 **FAIL/HOLD** 처리한다. 테스트를 skip하거나 가짜 메시지를 publish해 GREEN으로 바꾸지 않는다.

## 실패 처리

`Actions → Restaurant Robot MVP CI → 해당 Run → 첫 실패 Step`에서 시작한다. 실패 시 `restaurant-ci-first-failure-<run>` 아티팩트에는 `ci-gazebo-summary.txt` 소형 요약만 저장된다. `logs/ci-gazebo.log` 원본은 runner에 생성되지만 업로드하지 않는다. 필요할 때만 첫 실패 로그를 추가한다. 성공한 L0/ L1을 불필요하게 반복시키기보다 실패한 job/경계에만 최소 수정한다. 원인이 upstream 변경이면 위 명시된 PIN과 설치된 버전 먼저 비교한다.

## 실행/출고 규칙

1. 신규 빈 저장소: `main` 최초 bootstrap 한 번. 이후 `feature/` 또는 `fix/` 브랜치 → PR → Actions 증거 → main 병합.
2. CI가 GREEN일 때도 **증거 범위를 표시**한다. `L2_SENSORS_PASS_NO_GOAL`을 `NAV2_PASS`로 격상하지 않는다.
3. S1–S3가 필수 동작을 확보하기 전 새 Planner/AI 모델/성능 목표/10회 반복 시험/상용 안전 인증을 추가하지 않는다.
4. S5 최종 인수 전에는 무분별한 `/cmd_vel` 직접 발행으로 Collision Monitor를 우회하지 않는다. 월드 매핑의 지도 생성 목적 수동 제어는 별도로 통제한다.
5. 실 배달 완주를 검증할 때는 Nav2 Action Result + `/odom` 위치 변화 + Gazebo/RViz 관찰 근거를 모두 기록한다.

## 공식 근거

- ROS 2 Jazzy / Ubuntu 24.04: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html
- Gazebo Harmonic: https://gazebosim.org/docs/harmonic/
- Gazebo ROS 2 vendor packages: https://gazebosim.org/docs/harmonic/ros2_gz_vendor_pkgs/
- `ros-tooling/setup-ros`: https://github.com/ros-tooling/setup-ros
- Actions runner Ubuntu 24.04: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
