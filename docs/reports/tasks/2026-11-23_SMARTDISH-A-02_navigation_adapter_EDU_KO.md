# SmartDish A-02 — 공식 Nav2 Navigation Adapter 구현 (주니어 개발 보고서)

- 날짜: 2026-11-23 KST
- 베이스: A-01 `9542cf265265652a6910f04b660eacca35b632f7`
- 단위 구현: `src/smartdish_robot/` ROS 2 `ament_python` 패키지·Adapter·NO_GOAL launch
- 검증 상태: **L0 25 PASS / ROS Jazzy L1 PASS** — [GitHub Actions #45118875792](https://github.com/silverbjin/samsung_AXI/actions/runs/45118875792), SHA `e069a134117fbc52718260a56eb7ac2ebd7d7885`; 실제 Gazebo L2 NOT_RUN
- 커밋: 본 파일과 구현 소스·L0 테스트를 함께 포함하는 커밋

## 1. 요구사항과 데이터 흐름

```text
D Manager -- /collection/nav_goal (std_msgs/String JSON)
    ↓ parse_goal / table_poses.yaml / sensor-fresh gate / operator TTY
A NavigationAdapter -- BasicNavigator.goToPose(PoseStamped, map)
    ↓ official Nav2 → existing Collision Monitor → Gazebo Waffle Pi
A NavigationAdapter ← isTaskComplete() / getResult() + /odom
    ↓ result_json (same request_id + leg)
D Manager ← /collection/nav_result (std_msgs/String JSON)
```

A는 UI 타이머/임무 FSM을 만들지 않습니다. D의 `request_id`·`leg`를 유지합니다. 기존 S7 Nav2/AMCL·Collision Monitor·속도 브리지를 건드리지 않고 `goToPose`만 호출합니다.

## 2. RED → GREEN / 재현 가능한 코드 읽기

| RED·예외 경계 | 구현한 보호 | 기대 관찰 |
|---|---|---|
| 잘못된 JSON·leg | `parse_goal` | 거부, Nav2 Goal 없음 |
| 좌표 null | `resolve_pose` | `FAILED/UNCONFIGURED_DESTINATION` |
| 스캔/odom 수신 불량 | `sensor_ready()` | Goal 없음 또는 FAILED |
| 다른 명령 중첩 | active/pending+중복 key | `BUSY` 또는 중복 무시 |
| Nav2 Task 실패·취소 | `getResult()` | 정확히 `FAILED/CANCELED` |
| Action만 성공, odom 이동 미관찰 | segment trace | `FAILED/ODOM_MOVEMENT_NOT_PROVEN` |
| 실 TTY 승인 전 | `approve_in_tty` | `/collection/nav_goal` 구독하지 않음 |

0.05m는 정밀 도착 성능 기준이 아니라 **로봇이 실제 조금이라도 움직였다는 최소 관측 보호장치**입니다. 임무 전체 PASS는 단위 성공이 아닌 같은 request_id에서 3개 결과+UI COMPLETED가 필요합니다.

## 3. 안전 우선 실행 명령

```bash
# 기존 S7 환경에서, source /opt/ros/jazzy/setup.bash (set +u)
colcon build --symlink-install --packages-select smartdish_robot
source install/setup.bash
python3 -m pytest -q tests/test_smartdish_a_contract.py tests/test_smartdish_a_package.py

# Nav2/AMCL/Gazebo 기동 및 초기 위치 준비 후: 목표 발행하지 않는 사전검사
ros2 launch smartdish_robot smartdish_robot.launch.py

# 실제 주행은 별도 터미널에서만, 원본 S7의 승인 습관 유지
ros2 run smartdish_robot navigation_adapter --ros-args \
  -p goals_enabled:=true -p set_initial_home:=true
# 실제 TTY에 YES-SMARTDISH-A-GOALS 수동 입력
```

`set_initial_home:=true`는 **실제 스폰 HOME을 확인한 경우에만** 사용합니다. 그렇지 않으면 false로 두고 Nav2/AMCL 초기 위치를 기존 방식으로 설정합니다. 실행 명령은 ROS 설치된 환경에서만 유효하며 작성 시 **L1/L2 NOT_RUN**입니다.

## 4. 설계 이유와 배제한 대안

- Nav2 Simple Commander는 S3/S7에서 이미 사용했습니다. 새 Planner, Navigation Action Server, ROS custom msg를 다시 만들지 않았습니다.
- `BasicNavigator`를 하나의 ROS node로 사용하고 `spin_once()` 루프 밖에서 Goal을 전송하여 구독 콜백에서 중첩 blocking Action을 보내지 않습니다.
- 버튼/타이머는 D가 소유하고 A는 물리 이동 판정만 담당합니다. 따라서 A의 L0 mock은 SmartDish 실제 완주 증거가 아닙니다.

## 5. 검증 범위 및 다음 작업

- 기대: Python syntax/계약 unit → ROS L1 package discovery → 실제 Gazebo 3-leg L2.
- 관찰: [#45118875792](https://github.com/silverbjin/samsung_AXI/actions/runs/45118875792) L0 25 passed; L1 `Starting >>> smartdish_robot`, `Finished <<< smartdish_robot`, `smartdish_robot navigation_adapter`, `SMARTDISH_A_L1_BUILD_NO_GOAL_PASS`. A-DBG-01 수정 뒤 L0 26 PASS([#45119133312](https://github.com/silverbjin/samsung_AXI/actions/runs/45119133312)); 실제 Goal/Gazebo는 NOT_RUN.
- 기존 S7 L3 PASS는 본 신규 패키지 L2 PASS를 증명하지 않습니다.
- 다음 A-03: 현장 실행·좌표 확정·팀 D 인계 문서 및 CI 상태 기록.
