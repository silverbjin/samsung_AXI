# E-R4 DBG-03 — docking_server가 CM을 우회하는 실제 DDS graph 결함
## RED 원인 확정
- [Run 45937930562](https://github.com/silverbjin/samsung_AXI/actions/runs/45937930562), SHA 1615ade32f7bedb9f756d6152ac9e57e0c89c4e8, artifact 15170859887, ZIP SHA256 `e343e1cdffb64475c5e972c825522d883c3d027c6253f171979df6fc314d2861` 검증 완료.
- CM/BT ACTIVE. /cmd_vel publisher endpoint: collision_monitor, docking_server, 모두 geometry_msgs/msg/Twist. 구독자는 ros_gz_bridge 한 개. /cmd_vel_nav: controller + behavior -> velocity_smoother. /cmd_vel_smoothed: velocity_smoother -> CM.
- Artifact의 실제 /opt/ros/jazzy Nav2 navigation_launch.py: Node/ComposableNode opennav_docking remappings=remappings만 있고 cmd_vel_nav remap 없음. 실제 도킹 목표/속도가 발행된 것은 아니나 bypass 가능성이 있는 구조다. Goal=0으로 차단.
## 최소 안전 수정
- E-only generated launch overlay. 기존 A/S7 navigation, /opt/ros/jazzy 및 main 변경 없음. 설치된 upstream launch를 복사하고 AST로 docking_server 2개 선언의 remappings에 ('cmd_vel','cmd_vel_nav')만 추가. upstream drift 시 중단. 원본/생성 SHA와 변경 범위를 receipt에 기록.
- A restaurant navigation 및 official bringup의 nav2 share 참조만 generated overlay로 변경; 그 외 기존 world/map/params/stagger, controller/behavior, CM 설정 유지. 실제 ROS launch는 generated path. 
- 실제 /cmd_vel sole CM, bridge subscriber, docking 포함 cmd_vel_nav -> smoother -> cmd_vel_smoothed -> CM 전체 endpoint를 시작/종료 검사. 허용 목록 완화 없음. 도킹 동작 자체는 본 MVP 범위 밖.
## 검증
L0 overlay shape/fail-closed 테스트 + 실제 동일 R4 3-leg Gazebo CI. 새 SHA에서 graph와 주행 증거가 모두 있어야 PASS. 기존 AI OFF L3 증거를 수정하거나 재평가하지 않는다. 현재 발견은 최신 CI Jazzy 설치 구성에 한정하며 과거 WSL2에 같은 endpoint가 있었다고 주장하지 않는다.
