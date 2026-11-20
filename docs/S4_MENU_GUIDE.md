# S4-MENU-01 — 교육용 데이터 흐름 및 CI 검수

```text
NORMAL/SOUP menu.yaml → nav2_msgs/SpeedLimit → /speed_limit
                                   ↓
                 Nav2 Controller Server (MPPI)
                                   ↓
                        /cmd_vel_smoothed
                                   ↓
                    Nav2 Collision Monitor
                       ↑ /scan (Gazebo)
                       ↓ /cmd_vel (filter output)
                   Gazebo Waffle Pi /odom
```

기준: NORMAL 0.23m/s, SOUP 0.11m/s. 실제 ROS Controller Server 속도 토픽은 overlay에서 명시 지정합니다.
안전: Collision Monitor의 기존 FootprintApproach를 보존하고 정면 STOP 구역을 최소 추가합니다.
CI는 같은 출고 지도에서 Navigation Action 실제 주행 Odom 속도 차이와 시험 fixture의 실제 LiDAR 안전 정지 증거를 확인합니다.
본 단계에서 WSL2 수동 지도 생성, 새 Planner/모터 제어/YOLO 학습은 하지 않습니다.

## 검증 관찰 포인트
- 단순 `SpeedLimit` 메시지 발행만으로 PASS 불가. `/odom` 실측 p75 NORMAL>SOUP, 상한 허용오차 내.
- 단순 스캔에 가까운 점이 있다고 PASS 불가. 공식 `CollisionMonitorState.STOP`와 CM 출력 `/cmd_vel` 제로, 로봇 Odom 정지까지 필요.
- 최종 `S4_MENU_NORMAL_SOUP_REAL_ODOM_SPEED_PASS`와 `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS`를 **실제 L2 로그/JSON**에서 확인해야 함.
- 원본을 수정하지 않는 단일 CI fixture이고 성공/실패 증거를 압축 보존합니다.

참고: https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/controller_server/
참고: https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/collision_monitor/configuring_collision_monitor_node/
