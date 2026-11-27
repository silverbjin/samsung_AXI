# E-DBG-002 — ROS 관측자가 A Adapter 준비를 가장한 오진

- 최초 RED: https://github.com/silverbjin/samsung_AXI/actions/runs/45928898785, L0 126 PASS, Jazzy L1 3패키지 빌드 PASS 및 C threshold 0.65/0.90 ACK·0.49 거부 PASS, D 준비 확인 단계 FAIL.
- 첫 오류: D Owner Manager가 A가 없는 DDS에서도 /collection/nav_goal 구독자 1개(테스트 관측자)를 보고 state=TO_TABLE을 발행.
- 원인: 기존 get_subscription_count()>0은 토픽을 보는 observer/rosbag/rqt와 실제 Navigation Adapter를 구별하지 않습니다. 이 테스트는 관측자라는 별도 노드를 만들었기 때문에 준비된 것처럼 보였습니다.
- 조치: E Owner 통합 모드에서만 get_subscriptions_info_by_topic('/collection/nav_goal')에서 node_name == smartdish_navigation_adapter를 추가 검사. 실제 A Node 명칭은 A 소스 BasicNavigator(node_name='smartdish_navigation_adapter') 근거.
- 중간에 A Adapter가 사라져도 후속 Goal을 발행하지 않도록 flush 단계에서 한 번 더 검사하고 ERROR ADAPTER_DISCONNECTED_NO_GOAL로 전이. 기존 AI OFF 동작은 변경하지 않음.
- 주의: ROS graph node_name은 인증·서명이 아니므로 악의적 publisher/participant에 대한 보안 보증이 아님. 실물 적용 시 DDS 신원/권한 검사 별도 필요.
- 재검: 실제 Jazzy DDS에서 관측자만 있을 때 D는 ADAPTER_NOT_READY_NO_GOAL, 추가 Nav Goal 0건이어야 함. CI 성공을 실제 A/Gazebo L3로 승격하지 않습니다.
