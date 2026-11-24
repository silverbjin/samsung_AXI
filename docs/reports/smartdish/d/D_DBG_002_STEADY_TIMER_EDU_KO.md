# D-DBG-002 — ROS timer와 실제 사용자 대기시간의 시계 분리

- 날짜: 2026-11-23
- 발견 방법: **정적 리뷰/잠재 오류 예방**. 실제 WSL2 RTF 실패나 Gazebo STOP을 재현했다는 주장이 아닙니다.
- 이전 코드: \`manager_node.py\`는 \`time.monotonic()\` 기반 FSM을 0.2초 ROS Node timer로 호출했습니다.
- 조건: E 통합에서 \`use_sim_time:=true\`를 함께 쓰는 경우 ROS clock의 정지/RTF 변화가 타이머 콜백 스케줄 자체를 늦출 가능성.
- 불변 요구: 식기 적재 10초·반납 5초는 Gazebo 시간 아닌 직원이 실제 기다리는 **단조 증가 시간** 기준이어야 합니다.

## 1. 왜 FSM의 time.monotonic만으로 부족할 수 있나?
\`\`\`text
ROS timer(주기적으로 tick 호출) ──> FSM.tick() ──> time.monotonic() 마감 계산
             ↑
  timer 스케줄이 /clock에 종속된다면
  /clock이 멈출 때 FSM.tick도 호출되지 않습니다.
\`\`\`

따라서 마감 계산뿐 아니라 콜백 스케줄도 STEADY_TIME에 고정해야 합니다. ROS 공식 rcl의 RCL_STEADY_TIME은 monotonic clock으로 정의됩니다.
참고: https://api.nav2.org/jazzy/html/time_8h.html

## 2. 최소 변경
\`manager_node.py\`
\`\`\`python
from rclpy.clock import Clock, ClockType
self.create_timer(0.2, self.on_timer,
                  clock=Clock(clock_type=ClockType.STEADY_TIME))
\`\`\`

FSM의 \`clock\`은 기존 \`time.monotonic\`을 그대로 유지합니다. Nav2 실주행, QoS, S7, A/B/C 코드는 변경하지 않았습니다.

## 3. 재현/검증 경계
- L0 정적 회귀: \`test_manager_callback_timer_is_monotonic_not_ros_sim_time\`
- L1 실제 ROS Jazzy 컨테이너: \`rclpy.init()\` → \`create_node()\` → \`create_timer(... ClockType.STEADY_TIME)\` → 삭제/종료 검사
- \`SMARTDISH_D_L1_STEADY_TIMER_API_PASS_NO_GOAL\` 출력 여부를 GitHub Actions 로그로 확인
- Gazebo RTF를 인위적으로 정지시킨 실험은 **NOT_RUN**이며 요구되지 않는 별도 성능 게이트로 승격하지 않습니다.

## 4. 교육용 원인 분석 체크리스트
1. 로그에서 '요청 수신', 'Goal 성공', 'WAIT_LOADING 진입', 'tick 반복', 'TO_RETURN 발행' 각각의 경계를 확인합니다.
2. ROS timer가 멈췄는지와 FSM deadline이 틀린 것인지 구별합니다.
3. 기능 요구와 관련된 가장 작은 코드만 바꿉니다.
4. L0 정적 검사와 L1 실제 API 시험을 구별하고, Gazebo 인수는 E 단계로 남깁니다.
