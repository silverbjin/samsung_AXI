# SmartDish — A 담당 로봇·시뮬레이션 핸드오프

- 작성: 2026-11-23 · 대상: D Mission Manager 및 후속 E 통합 개발자
- 저장소: [silverbjin/samsung_AXI](https://github.com/silverbjin/samsung_AXI)
- 브랜치: `feat/smartdish-a-robot` (S7 main `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894` 기원)
- 상태: **CONTRACT IMPLEMENTED / real Gazebo three-leg NOT_RUN**
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
  DISH_RETURN: {x: null, y: null, yaw: null}
```

HOME은 기존 S3 `pickup`이며 **기존 S7 `PICKUP_RETURN`은 SmartDish DISH_RETURN이 아닙니다.** T03은 기존 S3 `table_3`입니다. `DISH_RETURN` 미검증 → Goal 미전송 / `FAILED, reason=UNCONFIGURED_DESTINATION`. 실제 Gazebo에서 도달 가능한 통로의 `map` Pose를 확정할 때까지 필수 AI OFF 3-leg 인수는 **BLOCKED**입니다.

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

## 4. 초심자용 실제 실행 — WSL2 Ubuntu 24.04

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
python3 -m pytest -q tests/test_smartdish_a_contract.py tests/test_smartdish_a_package.py
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

## 5. 신규 반납점 확정·L2 인수 준비

1. Nav2/AMCL이 실제 `map`과 `map→odom→base` TF를 제공하는지 확인.
2. 기존 World에 이미 있는 주방 카운터 주변의 **충돌 없는 통로**를 지도/RViz에서 확인하고, 로봇 차체가 도달 가능한 위치(x,y,yaw)를 측정합니다. World SDF 픽셀/좌표를 직접 넣지 않습니다.
3. `table_poses.yaml`의 `DISH_RETURN`에 검증된 숫자만 추가합니다. `ros2 run`은 재시작하여 설치 YAML을 다시 읽습니다.
4. A 단독 L2는 3구간 `TO_TABLE/T03 → TO_RETURN/DISH_RETURN → TO_HOME/HOME`을 **동일 request_id**로 주행하고 Nav2 결과 + /odom 이동을 기록합니다. D가 연결되기 전 A 단독 성공은 `ROBOT_ONLY`입니다.
5. D 통합 시에만 10초/5초 대기 및 UI `COMPLETED`를 검수하고 `AI_OFF_REAL_RUN_PASS`를 선언합니다. 기존 S7 PASS를 새 PASS로 복제하지 않습니다.

## 6. 증거·디버깅·버전

```bash
git rev-parse HEAD
ros2 topic info -v /collection/nav_goal
ros2 topic info -v /collection/nav_result
ros2 action info /navigate_to_pose
ros2 topic echo /odom --once
```

전형적인 실패 경계는 `INVALID_GOAL_COMBINATION`, `UNCONFIGURED_DESTINATION`, `PREGOAL_SCAN_OR_ODOM_MISSING`, `NAV2_FAILED`, `ODOM_MOVEMENT_NOT_PROVEN`입니다. **최초 실패 로그 + 환경/SHA + 원인 가설 + 확인 사실 + 최소 수정 + 같은 경계 재검**을 `docs/reports/issues/`에 남기십시오. 시각 검수는 사용자 담당이며 이번 자동 게이트가 아닙니다.

## 7. 보고서 이력과 남은 경계

- [A-01 계약·좌표 개발 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-01_contract_and_map_EDU_KO.md)
- [A-02 Nav2 Adapter 개발 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-02_navigation_adapter_EDU_KO.md)
- [A-03 출고·검증 보고서](../reports/tasks/2026-11-23_SMARTDISH-A-03_ci_handoff_EDU_KO.md)

**핸드오프 판정:** 계약 및 기본 패키지 구현 완료. 실제 신규 DISH_RETURN 좌표·A 3-leg Gazebo/odom·D 통합은 NOT_RUN. AI OFF 발표 인수로 승격하지 않습니다.
