# SmartDish — A 담당 로봇·시뮬레이션 핸드오프

- 작성: 2026-11-23 · 대상: D Mission Manager 및 후속 E 통합 개발자
- 저장소: [silverbjin/samsung_AXI](https://github.com/silverbjin/samsung_AXI)
- 브랜치: `feat/smartdish-a-robot` (S7 main `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894` 기원)
- 상태: **A L0 29 PASS / ROS L1 PASS / Gazebo 실제 3-leg L2 PASS, D UI 통합 NOT_RUN**
- Draft PR: https://github.com/silverbjin/samsung_AXI/pull/36 (미병합)
- 기존 S7 L3 통과 소스 SHA: `097e5aca022f59b18f289e7d383a3a6b85a5da1a` (새 A 기능 검증 소스와 구분)

## 1. 재사용과 A 소유 산출물

기존 `src/restaurant_world/worlds/restaurant.sdf`, `restaurant_bringup/`, `maps/`, Nav2/AMCL/Collision Monitor와 Waffle Pi 공식 자산을 재사용합니다. **새 world 복사본이나 새 Planner는 만들지 않았습니다.** 기존 S7 TTY·/cmd_vel 경로도 건드리지 않습니다.

| A 소유 경로 | 목적 |
|---|---|
| `src/smartdish_robot/config/table_poses.yaml` | 단일 map Pose 원본 |
| `src/smartdish_robot/smartdish_robot/contract.py` | JSON 규격·좌표 방어 |
| `src/smartdish_robot/smartdish_robot/navigation_adapter.py` | 공식 BasicNavigator Action, /odom 증거 |
| `src/smartdish_robot/launch/smartdish_robot.launch.py` | No-Goal 사전검사 전용 |
| `tests/test_smartdish_a_*.py` | ROS 없는 L0 계약 테스트 |
| `.github/workflows/smartdish-a-ci.yml` | 별도 A L0/L1, **실 Gazebo L2 아님** |

## 2. 목적지와 선행 의존성

```yaml
frame: map
poses:
  HOME: {x: 0.0, y: 0.0, yaw: 0.0}
  T03: {x: 5.25, y: 0.38, yaw: -1.57079632679}
  DISH_RETURN: {x: -1.15, y: 1.60, yaw: -1.57079632679}
```

HOME은 기존 S3 `pickup`이며 **S7 `PICKUP_RETURN`은 SmartDish DISH_RETURN이 아니라 HOME**에 대응합니다. T03은 기존 S3 `table_3`입니다. `DISH_RETURN`은 S2-MAP-03 실제 방문 지점 World `(-3.75,-0.60)`에서 map `(-1.15,1.60)`으로 변환했으며, [실제 Gazebo/Nav2 3-leg CI #45124877004](https://github.com/silverbjin/samsung_AXI/actions/runs/45124877004)에서 도달 및 복귀 성공을 확인했습니다. 향후 YAML이 `null`로 잘못 바뀌면 여전히 `FAILED/UNCONFIGURED_DESTINATION`으로 차단합니다.

## 3. D 팀이 연결할 공식 토픽·QoS

모두 `std_msgs/msg/String`의 UTF-8 JSON이며 `RELIABLE / VOLATILE / KEEP_LAST(10)`입니다. D는 A의 Pose나 cmd_vel을 직접 다루지 않습니다.

```json
{"request_id":"REQ-001","leg":"TO_TABLE","destination_id":"T03"}
```
- **D→A:** `/collection/nav_goal`; 허용 조합 `TO_TABLE/T03`, `TO_RETURN/DISH_RETURN`, `TO_HOME/HOME`만.
- **A→D:** `/collection/nav_result`, 예: `{"request_id":"REQ-001","leg":"TO_TABLE","result":"SUCCEEDED","reason":""}`.
- 목표 구독은 **Nav2/AMCL ACTIVE + /scan·/odom 수신 + 실 TTY 승인 후** 생성합니다. 수신 노드가 준비되기 전 D는 goal을 발행하면 안 됩니다.
- 단일 active/pending, 이전 `request_id`/구간 중복 거부, 임의 재전송 없음. D는 자체적으로 현재 `request_id`·`leg`가 맞는 결과만 수용합니다.
- A의 SUCCEEDED는 공식 Nav2 완료와 실제 0.05m 이상 odom 관찰 이후에만 전송하며, D의 타이머는 A 성공 이후부터 시작합니다.

## 4. WSL2 **한 줄 배포·실행** — A-08 (최신 권장)

WSL2 Ubuntu 24.04 대화형 터미널에서 별도의 Git clone/checkout 없이 **한 줄**만 입력하십시오. 고정된 GitHub 커밋의 부트스트랩을 먼저 다운로드한 뒤 로컬 파일로 실행하여 TTY를 보존합니다.

```bash
curl -fsSLo "$HOME/smartdish_a_wsl2_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/cd99c59f90d26f80b247c2a3763b0b4a0ff981c2/scripts/smartdish_a_wsl2_bootstrap.sh" && bash "$HOME/smartdish_a_wsl2_bootstrap.sh" --headless
```

화면을 열어 확인하려면 끝의 `--headless`만 `--gui`로 바꿉니다. 이미 `~/samsung_AXI_A`가 있으면 **로컬 수정 없는 경우에만** Fast-forward 갱신하며, 절대 reset/삭제하지 않습니다. 실제 Goal은 사용자 터미널에서 `YES-SMARTDISH-A-GOALS`를 직접 입력할 때만 시작됩니다.

상세: [A-08 단일 명령 배포·교육 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-08_wsl2_bootstrap_release_EDU_KO.md). [출고 L0 45 PASS + ROS Jazzy L1 PASS #45129546662](https://github.com/silverbjin/samsung_AXI/actions/runs/45129546662). A의 실제 WSL2 L3는 **현장 증거 전까지 NOT_RUN**입니다.

## 4A. 기존 A-07 코드 다운로드 후 실행 (대안)

과거의 3터미널 수동 시연 대신 아래 단일 실행기를 권장합니다. **실제 사용자 승인**과 로그 저장을 포함합니다.

```bash
cd ~
git clone --single-branch --branch feat/smartdish-a-robot https://github.com/silverbjin/samsung_AXI.git samsung_AXI_A
cd ~/samsung_AXI_A
bash scripts/smartdish_a_wsl2_one_shot.sh --headless
# WSLg 시각 확인은 --gui (옵션)
```

Nav2/AMCL 사전검사 후 요청이 나타나면 `YES-SMARTDISH-A-GOALS`를 터미널에서 직접 입력합니다. 실패·성공 모두 `generated/smartdish_a_wsl2/<run_id>/smartdish_a_owner_evidence.tar.gz`가 생성됩니다. 성공은 `SMARTDISH_A_WSL2_OWNER_L3_PASS` **정확히 한 번**입니다. 자세한 해설: [A-07 원샷 사용·교육 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-07_wsl2_one_shot_EDU_KO.md). [A-07 GitHub L0 42 PASS + ROS L1 PASS #45127703923](https://github.com/silverbjin/samsung_AXI/actions/runs/45127703923); **사용자 WSL2 L3는 NOT_RUN**.

## 4A. 이전 3터미널 수동 실행 (참고용, 권장 아님)

S7에서 사용한 ROS 2 Jazzy, Gazebo Harmonic, Nav2와 공식 Waffle Pi 환경이 이미 설치된 WSL2를 전제로 합니다.

터미널 1 — 기존 S7 World/Map/Nav2 재사용 (주행 Goal 자동 전송 없음):

```bash
git clone -b feat/smartdish-a-robot https://github.com/silverbjin/samsung_AXI.git
cd samsung_AXI
export RESTAURANT_ROOT="$PWD"
# 기존 환경 스크립트가 Waffle 모델과 Map/Nav2 params를 생성함.
bash scripts/restaurant_demo.sh navigation
```

터미널 2 — A 패키지 설치 및 계약 테스트:

```bash
cd ~/samsung_AXI                      # 실제 clone 위치로 바꿉니다
set +u
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select smartdish_robot
source install/setup.bash
python3 -m pytest -q tests/test_smartdish_a_contract.py tests/test_smartdish_a_package.py tests/test_smartdish_a_tty.py tests/test_smartdish_a_return_candidate.py
ros2 pkg executables smartdish_robot
ros2 topic list -t | grep -E '/scan|/odom|/navigate_to_pose'
# NO_GOAL: 실제 이동 승인과 요청 수신을 하지 않고 종료
ros2 launch smartdish_robot smartdish_robot.launch.py
```

터미널 2 — 실제 목적지 이동을 허용할 때만, 해당 터미널에서:

```bash
# 실제 HOME 스폰 확인 시에만 -p set_initial_home:=true
ros2 run smartdish_robot navigation_adapter --ros-args \
  -p goals_enabled:=true -p set_initial_home:=false
# /dev/tty에서 YES-SMARTDISH-A-GOALS 수동 승인
# SMARTDISH_A_READY 출력 뒤 D 노드에서 요청 가능
```

`set_initial_home:=false`이면 AMCL 초기 위치는 기존 Nav2 설정/도구가 먼저 제공해야 합니다. 확인하지 않은 지도 좌표로 Goal을 발행하지 마십시오. A는 `/cmd_vel`을 직접 발행하지 않습니다.

터미널 3 — 운영자가 직접 승인한 상태에서 `T03` 한 구간만 시험할 때:

```bash
set +u
source /opt/ros/jazzy/setup.bash
source ~/samsung_AXI/install/setup.bash
ros2 topic echo /collection/nav_result std_msgs/msg/String
# 또 다른 터미널에서 발행할 JSON 예 (D Manager 준비 후에는 D만 발행)
ros2 topic pub --once /collection/nav_goal std_msgs/msg/String \
  'data: "{\"request_id\":\"REQ-A-01\",\"leg\":\"TO_TABLE\",\"destination_id\":\"T03\"}"'
```

**주의:** 위 수동 단일 Goal은 팀 D 전체 시연이 아니며, T03 직후 복귀를 자동 발행하지 않습니다. 일회성 테스트 중 로봇이 예상과 다르면 즉시 목표를 중단하고 안전 상태 확인이 우선입니다.

## 5. 실제 A 단독 Gazebo 3구간 L2 인수 결과

[Run #45124877004](https://github.com/silverbjin/samsung_AXI/actions/runs/45124877004), 실행 SHA `6d7e3508ea1f4a5d32ab257904b2335f859b3f0b`, 같은 `request_id=SMARTDISH-A-CI-L2-001`에서 공식 Nav2 Action 결과 3개를 관측했습니다.

| 구간 | 실제 Nav2 | /odom 시작점 기준 최대 변위 | AMCL 목표 위치 오차 |
|---|---|---:|---:|
| TO_TABLE / T03 | SUCCEEDED | 5.181m | 0.098m |
| TO_RETURN / DISH_RETURN | SUCCEEDED | 6.459m | 0.196m |
| TO_HOME / HOME | SUCCEEDED | 1.940m | 0.166m |

위 /odom 수치는 **누적 주행거리 아닌 시작점 대비 최대 변위**입니다. 프로젝트 JSON 두 토픽 및 기존 Map/AMCL/Collision Monitor 경로를 실제로 사용했습니다. D UI의 10초/5초 대기와 최종 `COMPLETED`는 **NOT_RUN**으로 구분하고 A/D 통합 단계에서 확인해야 합니다.

### 운영 YAML 직접 사용 최종 R04 실증

- [운영 SHA `5b063a0` 기반 Gazebo L2 Run #45125551884](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884) **PASS**: 3 Nav2 SUCCEEDED, odom 최대 변위 **5.148/6.462/1.958m**, AMCL 오차 **0.189/0.142/0.235m**.
- [R04 증거 Artifact #14795667913](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884/artifacts/14795667913): `l2_evidence.json`, `smartdish_a_gazebo.log`.
- [A-06 교육 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-06_return_pose_release_EDU_KO.md)에서 후보→운영 좌표 승격과 이력을 확인할 수 있습니다.
- D/E 통합자는 반드시 **A 브랜치의 실제 사용 SHA 및 `table_poses.yaml`**을 함께 고정하십시오. A 단독 실제 주행 성공은 D UI `COMPLETED`의 증거가 아닙니다.

## 6. 증거·디버깅·버전

```bash
git rev-parse HEAD
ros2 topic info -v /collection/nav_goal
ros2 topic info -v /collection/nav_result
ros2 action info /navigate_to_pose
ros2 topic echo /odom --once
```

전형적인 실패 경계는 `INVALID_GOAL_COMBINATION`, `UNCONFIGURED_DESTINATION`, `PREGOAL_SCAN_OR_ODOM_MISSING`, `NAV2_FAILED`, `ODOM_MOVEMENT_NOT_PROVEN`입니다. **최초 실패 로그 + 환경/SHA + 원인 가설 + 확인 사실 + 최소 수정 + 같은 경계 재검**을 `docs/reports/issues/`에 남기십시오. 시각 검수는 사용자 담당이며 이번 자동 게이트가 아닙니다.

## 7. 공개 CI 증거와 판정

- [원격 A L0 25 PASS + ROS Jazzy L1 PASS #45118875792](https://github.com/silverbjin/samsung_AXI/actions/runs/45118875792), 실행 SHA `e069a13`, `SMARTDISH_A_L1_BUILD_NO_GOAL_PASS`.
- [CLI 디버깅 수정 후 L0 26 PASS #45119133312](https://github.com/silverbjin/samsung_AXI/actions/runs/45119133312), 실행 SHA `bae0c36`. ROS Jazzy L1 빌드·실행 엔트리포인트 **PASS**. 후속 보고서 커밋은 문서만 변경됨.
- [후보 YAML 실제 L2 #45124877004](https://github.com/silverbjin/samsung_AXI/actions/runs/45124877004): `SMARTDISH_A_REAL_GAZEBO_3LEG_L2_PASS`, 3 × SUCCEEDED.
- [운영 YAML 실제 L2 #45125551884](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884): **최종 출고 SHA 5b063a0**, 3 × SUCCEEDED와 odom/AMCL, A `ROBOT_ONLY` PASS. D UI 완료만 **NOT_RUN**.

## 8. 보고서 이력과 남은 경계

- [A-01 계약·좌표 개발 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-01_contract_and_map_EDU_KO.md)
- [A-02 Nav2 Adapter 개발 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-02_navigation_adapter_EDU_KO.md)
- [A-03 출고·검증 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-03_ci_handoff_EDU_KO.md)
- [A-DBG-01 JSON 인코딩 오류 분석 및 L0 해결](../reports/issues/2026-11-23_SMARTDISH-A-DBG-01_cli_json_escaping_EDU_KO.md)
- [A-COORD-01 반납점 좌표 L2 해결](../reports/issues/2026-11-23_SMARTDISH-A-COORD-01_return_pose_HOLD_EDU_KO.md)
- [A-04 접근 좌표 선정](../reports/tasks/2026-11-23_SMARTDISH-A-04_return_pose_candidate_EDU_KO.md)
- [A-05 실제 3-leg Gazebo](../reports/tasks/2026-11-23_SMARTDISH-A-05_real_gazebo_3leg_EDU_KO.md)
- [A-06 운영 YAML 승격](../reports/tasks/2026-11-23_SMARTDISH-A-06_return_pose_release_EDU_KO.md)
- [TTY 오류 RED→GREEN](../reports/issues/2026-11-23_SMARTDISH-A-L2-DBG-02_tty_rplus_EDU_KO.md)

**핸드오프 판정:** A 담당 실제 3-leg Nav2+odom **ROBOT_ONLY L2 PASS**. 운영 `table_poses.yaml`에 검증된 접근 좌표를 확정했습니다. **D Manager+UI 통합·대기 타이머·COMPLETED는 NOT_RUN**이므로 전체 SmartDish MVP AI OFF PASS로 승격하지 않습니다.
