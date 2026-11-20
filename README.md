# Restaurant Robot MVP — 강사 독립 실습 기준선 (개발 후보)

**2026-11-20 최신 인수 판정: `OWNER_WSL2_WSLG_GUI_L3=ACCEPTED`, `RTF_MEDIAN_GE_90_PERCENT=PASS`, `RESTAURANT_ROBOT_MVP=PARTIAL`.** 강사 WSL2/WSLg 실제 GUI에서 개선 지도 S2-MAP-03, AMCL 자동 위치 초기화, Nav2 ACTIVE, Gazebo/RViz 동시 표시, D3D12 RTX 3060 가속을 확인했습니다. 실제 Gazebo RTF 100표본 중앙값 99.92%(p10 69.96%)로 90% **중앙값 목표**를 충족했습니다. S3 배달·복귀 및 S4 메뉴 속도·Collision Monitor 안전 STOP은 각각 실제 Gazebo **CI PASS**를 보존하며, 강사 WSL2 라이브 GOAL 시연(L3)은 **NOT_RUN**입니다. 따라서 전체 `DEMO_PASS`는 아직 아닙니다. [실제 L3 인수 보고서](docs/reports/tasks/2026-11-20_OWNER_WSL2_GUI_L3_FINAL_ACCEPTANCE_KO.md).

목표는 단 하나: **Waffle Pi가 레스토랑에서 픽업(1) → 테이블(3) → 픽업(1)을 실제 이동하고, 메뉴 정책과 장애물 대응을 확인한 후 개발 종료**. 도면 원본이 현재 첨부되지 않았으므로 SDF는 임시 10×9m 배치입니다. `docs/WORLD_LAYOUT.md` 참고.

## 강사 WSL2 원격 원샷 (출고 전 CI 검증 대상으로 추가됨)

강사 Ubuntu 24.04 WSL2/WSLg 터미널에서 **검증 완료된 원격 커밋 SHA**를 지정해 실행합니다. ROS 2 Jazzy가 먼저 설치되어 있어야 하며, 누락된 개별 apt 의존성만 `sudo`로 보완합니다.

```bash
# SHA에는 GitHub Actions L0+L1+L2가 통과한 samsung_AXI 커밋의 40자 SHA 입력
SHA="<GREEN_COMMIT_40CHAR>"
SCRIPT="$(mktemp --suffix=.sh)"
trap 'rm -f "$SCRIPT"' EXIT
curl -fL --retry 3 --connect-timeout 10 \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/${SHA}/scripts/owner_wsl2_once.sh" \
  -o "$SCRIPT"
bash -n "$SCRIPT" && bash "$SCRIPT" world --ref "$SHA"
```

기본 `world`는 Gazebo 물리 World + Waffle Pi + 등록 RGB-D + LiDAR만 시작하고 **Goal을 보내지 않습니다**. 첫 실행에서 모델이 실제 보이고 `/scan`·`/odom`·Depth가 유효한지 확인하십시오. 로그: `$HOME/samsung_AXI/logs/owner_world_*.log`와 해당 `world_*.log`.

같은 진입점에서 `mapping`, `navigation`, `demo NORMAL`, `demo SOUP`, `doctor` 모드를 사용할 수 있지만 실제 map이 만들어지기 전 `demo`는 차단됩니다. `Ctrl+C`는 스크립트가 소유한 데모 종료에 사용합니다. 원격 코드·환경 불일치 때 강제 덮어쓰기나 글로벌 `pkill`을 수행하지 않습니다.

**상태:** 위 원샷은 CI 및 WSL2 실제 검수 완료 전까지 후보입니다. Actions 검증 없이 `DEMO_PASS`를 주장하지 않습니다. 개발·검수 과정: [`OWNER-01`](docs/reports/tasks/2026-11-19_OWNER-01_wsl2_one_shot_predeployment.md).

## 1. Windows WSL2 Ubuntu 24.04 — 준비

```bash
# Ubuntu 터미널; ROS 2 Jazzy / Gazebo Harmonic 설치된 WSL2
sudo apt update
sudo apt install -y git python3-colcon-common-extensions python3-yaml \
  ros-jazzy-ros-gz ros-jazzy-ros-gz-image \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-slam-toolbox ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-robot-state-publisher ros-jazzy-tf2-ros
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=58  # 기본 격리 도메인; 다른 AXIA 세션과 섞지 않기
export GZ_PARTITION=restaurant_mvp
```

압축을 해제하거나 **신규 독립 Git 저장소**에 이 폴더를 두고 아래 명령을 실행합니다. 기존 AXIA 저장소는 사용/수정하지 않습니다. 공식 `turtlebot3_gazebo`가 없으면 실행기가 `ROBOTIS-GIT/turtlebot3_simulations`의 `jazzy` 브랜치만 `src/upstream`에 복제합니다.

```bash
cd ~/restaurant_robot_mvp  # 압축 해제 위치에 맞게 변경
./scripts/restaurant_demo.sh doctor
```

## 2. S1 — 먼저 Gazebo에서 매장과 로봇을 확인 (최우선 첫 실행)

```bash
cd ~/restaurant_robot_mvp
./scripts/restaurant_demo.sh world
```

**정상 관찰:** Gazebo 안에서 벽, 조리대, 5개 테이블, 사람 프록시와 실제 Waffle Pi가 함께 보입니다. *창만 열리고 월드가 비어 있으면 실패입니다.* ROS2 다른 터미널에서 다음으로 점검합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/restaurant_robot_mvp/install/setup.bash
export ROS_DOMAIN_ID=58
export GZ_PARTITION=restaurant_mvp
ros2 topic list | grep -E '^/(clock|scan|odom|tf)$'
ros2 topic echo /scan --once
ros2 topic echo /odom --once
ros2 topic info -v /cmd_vel
```

`Ctrl+C`로 실행 종료합니다. 로그는 `logs/world_YYYYMMDD_HHMMSS.log`에 남습니다. 오류가 나면 `tail -n 60 logs/world_*.log | tail -n 60`으로 첫 오류를 확인합니다. GUI와 WSLg 렌더링 문제는 `docs/DEMO_GUIDE.md`에 있습니다.

## 3. S2 — 실제 LiDAR로 지도 생성 (S1 성공 후)

**아직 현장 미검증 후보 구성입니다.** 공식 Waffle Pi를 유지하고 RGB-D만 로컬 SDF 사본에 장착합니다. 원본 공식/AXIA 소스는 변경하지 않습니다.

```bash
# 터미널 A (Gazebo + 공식 SLAM Toolbox)
cd ~/restaurant_robot_mvp
./scripts/restaurant_demo.sh mapping
```

```bash
# 터미널 B (map 모드에서만 운영자가 감독하며 수동 주행)
source /opt/ros/jazzy/setup.bash
source ~/restaurant_robot_mvp/install/setup.bash
export ROS_DOMAIN_ID=58
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

```bash
# 터미널 C — 실제 /map이 퍼블리시될 때 1회 저장
cd ~/restaurant_robot_mvp
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=58
export GZ_PARTITION=restaurant_mvp
ros2 topic echo /map --once | head -n 16
ros2 run nav2_map_server map_saver_cli -f "$PWD/maps/restaurant_map"
ls -l maps/restaurant_map.yaml maps/restaurant_map.pgm
ros2 topic echo /restaurant/rgbd/depth_image --once | head -n 16
ros2 topic echo /restaurant/rgbd/points --once | head -n 16
```

주행 영역이 보이는 지도를 실제로 생성해야 합니다. 조리대와 테이블 사이를 로봇이 통과할 수 없다면 **새 알고리즘이 아니라 SDF 배치를 최소 조정**합니다. S2의 원샷은 지도 생성까지 자동 완주시키지 않으며, 한 번 저장할 때만 운영자의 수동 주행을 허용합니다.

## 4. S3 — 저장 지도 + AMCL + 실제 배달/복귀 (S2 성공 후)

```bash
# GUI 검토용: 내비게이션만 실행, Goal 자동 발행 없음
./scripts/restaurant_demo.sh navigation

# GUI 점검이 끝난 다음: 한 번의 실제 배달/복귀 (별도 실행)
./scripts/restaurant_demo.sh demo NORMAL
```

시연 관리자는 첫 `/scan`/`/odom` 수신, AMCL 활성화, `/speed_limit` 구독 확인 전 Goal을 발행하지 않습니다. 테이블 도착을 알린 후 강사에게 **Enter로 수령 확인**을 요청하고 원점으로 복귀합니다. Nav2 Action Result, 물리 `/odom` 움직임, Gazebo GUI 세 근거를 확인해야 S3 후보 성공입니다. 맵이 없다면 `BLOCKED` 메시지와 함께 시작 전 종료합니다.

## 5. S4 — 메뉴 및 한 개 물리 장애물 (S3 완주 후)

```bash
# 같은 시뮬레이터를 재시작하여 SOUP 저속 설정 확인
./scripts/restaurant_demo.sh demo SOUP
```

`menu.yaml`에 NORMAL=0.23 m/s, SOUP=0.11 m/s가 예시로 설정되어 있고, 배송 관리자는 **공식 `/speed_limit`**으로만 제한을 전달합니다. 새로운 `/cmd_vel` 퍼블리셔를 만들지 않습니다. 실제 제어 반영 여부는 ROS 주행으로 확인해야 합니다.

`human_proxy`는 기본적으로 통로 밖에 있습니다. 실제 정지/우회 시연에서만 **Gazebo GUI의 모델 이동 도구로** 통로에 가져왔다가 다시 제거합니다. LiDAR `/scan`과 RGB-D `/restaurant/rgbd/points`가 주행 안전 경로에 연결되는지 확인하고, 충돌이 보이면 중단합니다. **자동 재개가 불확실하면 Goal을 취소하고 운영자 판단하에 새 실행으로 재개합니다.** 원격 pose 조작의 자동화는 아직 제공하지 않습니다.

## 6. 최종 인수

`docs/DEMO_GUIDE.md`의 M1~M8 체크리스트를 강사 **실제 WSL2에서 1회** 수행한 후에만 `DEMO_PASS` 판단이 가능합니다. 성공 시 태그를 강사가 생성하며, 본 패키지에 가짜 인수 태그를 포함하지 않았습니다.

ROS/Gazebo/GUI가 없는 환경에서 확인한 것은 Python 문법, SDF XML 형식, 작은 상태 정책 테스트뿐입니다. 자세한 출처와 제한: `docs/REUSE_NOTES.md`, `docs/DEVELOPMENT_LOG.md`.

## CI / GitHub 원격 관리

정식 원격 저장소는 `https://github.com/silverbjin/samsung_AXI`입니다. 업로드 전에 `git remote -v`로 기존 remotes를 확인하고, **force push 없이** 현재 트리 전체를 초기 `main`에 올리세요. `.github/workflows/restaurant-ci.yml`이 최초 push에서 자동 실행됩니다. `docs/CI_PIPELINE.md`는 L0/L1/L2(NO_GOAL)와 최종 L3의 차이를 설명하고, `docs/CI_AUTONOMOUS_MASTER_PROMPT_KO.md`는 시니어 에이전트에게 전체 개발·검증·인계를 위임하기 위한 실행 프롬프트입니다.

**주의:** L2는 현재 센서 no-goal 범위입니다. 저장 SLAM 지도와 Nav2 실제 이동이 검증되기 전에는 CI GREEN만으로 `DEMO_PASS`를 선언하지 않습니다.


## 개발 경과·디버깅 보고서

모든 작업이 끝날 때 `docs/reports/tasks/`에 경과 보고서를 남깁니다. 실제 오류가 발생했다면 `docs/reports/issues/`에 원인 분석·수정·동일 경계 재검을 기록합니다. 자세한 규칙과 훈련생 해설 양식은 [`AGENTS.md`](AGENTS.md), [`docs/REPORTING_POLICY.md`](docs/REPORTING_POLICY.md)를 확인하십시오.

## P0 S1 기준선
- SAMSUNGAXI PC i7-11700F / RAM 16GB / RTX3060 8GB 전용. 다른 AXIA 환경 가정 금지.
- 생성 Waffle Pi SDF에서만 기본 RGB 30Hz 중복을 제거하고 RGB-D 5Hz와 LiDAR 10Hz는 유지.
- D3D12 GPU 최적화 현장 RTF 99.89%는 단일 시점 확인값. [P0 경과 보고서](docs/reports/tasks/2026-11-19_P0_S1_verified_baseline.md).

## S2-MAP-01 — 실제 Gazebo 지도 생성·저장·재로딩
공식 SLAM Toolbox와 Nav2 Map Saver/Map Server를 재사용하는 L2 통합 검증. 짧은 물리 이동으로 생성한 지도의 저장·재로딩을 확인하며 전체 매장 탐색이나 AMCL 성공으로 혼동하지 않습니다. [S2 지도 가이드](docs/S2_MAP_GUIDE.md).

## 2026-11-19 P0/S2 최신 검증
- **P0 S1 main 확정**: PR #4 / GREEN #44486003784 / main `c124d3d`.
- **S2 실제 지도 파이프라인 구현 완료**: PR #5 / [GREEN #44488688236](https://github.com/silverbjin/samsung_AXI/actions/runs/44488688236) / main `344dacb`. 실제 Gazebo Scan→SLAM `/map`→0.381m `/odom`→SaveMap YAML/PGM→Map Server 재로딩 성공.
- **S2 전체 레스토랑 지도와 AMCL/배달**: 아직 미인수. 짧은 CI 이동의 부분 지도를 주행 완성 지도로 사용하지 말 것. [S2 안내](docs/S2_MAP_GUIDE.md).

## CI 기반 전체 지도 (S2-MAP-02)
[레스토랑 전체 지도 CI 생성/품질 확인/출고](docs/S2_MAP02_GUIDE.md)를 사용합니다. 검수된 `maps/restaurant_map.yaml` 및 `.pgm`은 CI에서 만들어 지도 후보 브랜치를 통해 승격하며, 강사 WSL2에서 재생성하지 않습니다.
