# D02 — ROS 2 전송 어댑터 및 A·C 계약 학습 보고서

## 구현 단위와 재사용
- 구현: \`manager_node.py\`, \`setup.py\`, \`package.xml\`, \`smartdish_service.launch.py\`, 7개 JSON fixture.
- 재사용: ROS 2 Jazzy \`rclpy\`, \`std_msgs/msg/String\`, 공식 QoS. S7 소스·Nav2 구성·LiDAR CM 수정 없음.
- 버전: 공통 계약 v1.0. ROS 토픽은 별도 커스텀 메시지 없음.

## ROS 통신 데이터 파이프라인
\`\`\`mermaid
sequenceDiagram
 participant U as D UI
 participant M as D ROS Adapter + 순수 FSM
 participant A as A Adapter
 participant C as C 추론(선택)
 U->>M: /collection/request
 M->>A: /collection/nav_goal
 A-->>M: /collection/nav_result (실제 완료)
 M-->>U: /collection/status
 M-->>C: /collection/ai_check_request (AI ON)
 C-->>M: /collection/stability (AI ON)
 U-->>M: /collection/staff_confirm (AI ON)
\`\`\`

## 스키마(7개) 및 메시지 예시
- \`docs/integration/smartdish_d_contract_fixtures_v1.json\`에 모든 topic의 유효 JSON 객체 예시가 있습니다.
- \`RELIABLE / VOLATILE / KEEP_LAST(10)\`.
- 단 하나의 ACTIVE 요청. 다른 요청에는 기존 상태를 보존하면서 거절용 \`ERROR,reason=BUSY\` 통지.
- 시작 전 Navigation Adapter 구독자가 하나도 없으면 \`ERROR,reason=ADAPTER_NOT_READY_NO_GOAL\`이며 주행 명령을 내지 않습니다.
- 토픽 이름, \`request_id\`, \`leg\`와 \`destination_id\`를 예시와 비교합니다.
- D는 \`/cmd_vel\`, \`/navigate_to_pose\`를 발행하지 않습니다.

## 실행 가이드 (Ubuntu 24.04 / Jazzy)
\`\`\`bash
set +u
source /opt/ros/jazzy/setup.bash
colcon build --packages-select smartdish_service --symlink-install
source install/setup.bash
ros2 pkg executables smartdish_service
ros2 launch smartdish_service smartdish_service.launch.py ai_available:=false
\`\`\`
A가 실제로 \`/collection/nav_goal\`을 구독하고 \`/collection/nav_result\`를 발행하는 상태에서 실행해야 합니다. UI에서 시작 요청을 보내기 전에 \`ros2 topic info -v /collection/nav_goal\`을 확인합니다. 임의 SUCCEEDED를 터미널에서 주입한 결과는 시연 인수로 사용할 수 없습니다.

## 테스트 경계
- 순수 FSM 계약 테스트: \`MOCK_ONLY\`.
- 패키지 빌드/ROS 구독 연결: Jazzy 현장/CI 환경에서 별도 검증 필요.
- A Gazebo 3-leg 실주행: E 통합창에서 \`Nav2 SUCCEEDED + /odom + UI COMPLETED\` 확보 전 \`NOT_RUN\`.

## 교육용 디버깅 질문
1. \`VOLATILE\` 구독자가 늦게 붙으면 과거 요청이 왜 전달되지 않습니까?
2. 토픽 이름이 같고 메시지 타입도 같아도 필드 불일치가 치명적인 이유는?
3. RMW 문제와 상태 머신 버그를 구분할 때 각각 어떤 로그가 필요합니까?
