# S2-MAP02-CI01 — 실제 Gazebo 전체 지도 탐색 중 LiDAR 안전 정지

- 날짜: 2026-11-19 KST
- 상태: **RED 확인 / 수정 후보 검증 전**
- 최초 실패: Run #44544900046, L0 30 PASS, L1 ROS 빌드 PASS, S1 실제 센서 L2 PASS, S2-MAP-01 실 SLAM·저장·재로딩 L2 PASS.
- 현상: S2-MAP-02 경유점 1과 2까지 실제 이동, 3번으로 이동하는 도중 `RESTAURANT_S2_MAP02_BLOCKED=LIDAR_FORWARD_CLEARANCE_BLOCKED_3`.

## 증거에 근거한 최초 실패 경계
- ROS/Gazebo 설치·Scan/SLAM 기동은 정상. **새로운 자동탐색의 전방 LiDAR 충돌 예방 조건**에서 안전 정지.
- 기존 경로의 SDF 정적 장애물 최단 중심 거리 약 0.32m, CI LiDAR 전방 정지 임계값 0.40m. waypoint 허용오차 0.16m를 고려하면 여유가 부족할 수 있음.
- 실제 실패 순간 Odometry 좌표·각도·거리값이 초회 로그에 없어, 정확히 어떤 가구를 감지했는지는 미확정. 안전 정지를 무시하지 않음.

## 최소 재검 후보
- 정적 장애물과 충분히 떨어진 서측·동측 주행 회랑으로 경로 보정, 왕복 33.3m. 사전 기하학적 최소 중심 여유 약 0.48m.
- 경유점 완료 허용 오차 0.09m로 축소해 코너커팅 억제.
- STOP 임계값 0.40m와 실제 LiDAR 기반 차단 기능은 그대로 유지.
- 같은 현상 재발 시 `ODOM`, `TARGET`, `REMAINING_M`, `FRONT_MIN_M`, `SCAN_ANGLE_MIN`, `SCAN_ANGLE_INCREMENT`를 로그로 남겨 추가 원인 분리.
- 실제 Actions 통과 전까지 `S2-MAP-02=HOLD`. S2-MAP-01 PASS 유지.

## 교육용 교훈
충돌 가능성이 보이면 안전 가드를 삭제하거나 임계값을 낮춰 GREEN을 만들어서는 안 됩니다. 로봇 위치·가구 배치·목표 허용오차·센서 실제 데이터를 결합하여 안전한 경로를 보완한 뒤 실제 Gazebo에서 다시 검증해야 합니다.
