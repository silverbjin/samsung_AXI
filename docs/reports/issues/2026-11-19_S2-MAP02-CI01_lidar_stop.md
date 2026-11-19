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

## Cycle 02 — 안전 정지 2회 반복 / 실제 Odom·Range 확인
- RED: [Run #44546324681](https://github.com/silverbjin/samsung_AXI/actions/runs/44546324681), L0/L1/S1 L2/S2-MAP-01 L2 PASS; 새 탐색 waypoint1·2 PASS, waypoint3 LiDAR 0.40m 가드 안전 정지.
- 오류 실측: `ODOM=(-1.126,3.924,1.582)`, `TARGET=(-1.15,6.11)`, 남은 거리 2.186m, `FRONT_MIN_M=0.394`, Scan 각도 0..6.28rad, 각도 증가 0.01749.
- SDF 기하학상 waypoint3 경로를 더 넓힌 뒤에도 동일 정지. 따라서 단순한 테이블 근접/목표 허용오차 가설은 충분하지 않음.
- 다음 원인 분리: 실제 장애물까지의 SDF 예상 거리와 스캔 최소 빔 상대각, Odom 원점 기반 실제 World 좌표 추정치를 동일 오류에 기록. **정지 임계값 0.40m는 변경하지 않음.**
- 동작 범위: CI 검수용 스크립트의 읽기 전용 장애 원인 계측만 추가, robot/SLAM/SDF/Map Saver 및 기존 PASS 변경 없음.
- 실제 GREEN 전에는 `S2_MAP02=HOLD`.

## Cycle 03 — LiDAR 빔과 SDF 예상 장애물 거리 불일치
- [Run #44547524892](https://github.com/silverbjin/samsung_AXI/actions/runs/44547524892): 기존 L0/L1/S1 L2/S2-MAP-01 L2 모두 PASS, S2-MAP-02 경유점 3 안전 정지 반복.
- `ODOM=(-1.126,3.943,1.582)`, world 추정=(-3.726,1.743), SDF 최근접 `table_4` 0.755m.
- 실제 LiDAR 전방 최소 0.375m, beam index337, azimuth -0.388rad(오른쪽22.2도). 최소거리와 SDF 기하학 거리 차이 약 0.38m.
- 추측 가능한 원인: 물리 본체 실제 Pose와 휠 Odom 차이, 센서 좌표 정합 오차, 추가 월드/로봇 충돌 지오메트리. 아직 확정할 수 없음.
- 다음 단일 계측: Gazebo Harmonic SceneBroadcaster `/world/restaurant/pose/info`에서 `waffle_pi` 실제 모델 Pose를 읽기 전용으로 수집해 동일 시각 Odom 추정치와 비교.
- 본체 Pose가 차이나면 CI 고정 탐색용 위치 피드백을 실제 모델 Pose 기반으로 바꾸는 최소 수정 검토(지도 센서/SLAM은 실제 데이터 유지). 차이가 없으면 스캔 프레임/장착 위치를 별도로 조사.
- S2-MAP-02가 완료되지 않은 동안 S3 AMCL/Nav2는 NOT_RUN. 기존 S2-MAP-01 PASS 유지.

## Cycle 04 — 실측 World Pose 기반 CI 탐색 피드백으로 수정
- [Run #44548621304](https://github.com/silverbjin/samsung_AXI/actions/runs/44548621304) RED: Gazebo 실제 Pose `(-3.186499,1.855990)` vs wheel Odom 기반 World 추정 `(-3.725,1.595)`, 약 0.60m 오차. 해당 위치에서 LiDAR 0.389m 안전 정지는 정상.
- 최소 수정: `s2_map02_gt_pose.py`로 실시간 `/world/restaurant/pose/info`의 실제 모델 Pose를 읽어, **CI 전용 고정 경로 추종**에서만 목표 좌표와 yaw 피드백 사용. 지도 검증 위치는 동시 관측된 Gazebo Pose·Odom·map→odom TF로 정합.
- /scan, /odom, /tf, SLAM Toolbox 입력은 원본 그대로. Gazebo GT를 SLAM 입력/Map으로 발행하지 않음. LIDAR 0.40m STOP, 불신/지연 시 종료 유지.
- Pytest 계약에 Gazette Pose_V 파싱 및 다른 모델 거부 회귀 추가. 실제 Gazebo GREEN 전까지 미해결.

## Cycle 05 — 실제 LiDAR +inf 무반사와 센서 오류를 구분
- [Run #44550663776](https://github.com/silverbjin/samsung_AXI/actions/runs/44550663776): GT 기반 제어 후 첫 경유점에서 `FRONT_MIN_M=0.0`, `MIN_BEAM_INDEX=-1`, SDF 최근접 kitchen_counter 약 0.736m, Gazebo 실제 모델과 Odom은 같은 좌표로 정합.
- 원인 경계: 전방 ±0.40rad에서 유효 **유한** LaserScan 거리값이 하나도 없어 기존 CI 전용 `front_distance`가 0.0m 안전정지를 발행함. 이 로그만으로 모든 빔이 +inf인지 확정하지 않음.
- 후보 최소 수정: ROS LaserScan의 정상 범위 밖 no-return **양의 Infinity**와 잘못된 NaN/0/음수 구분. 전방 빔 10개 이상 중 80% 이상이 거리 유한값 또는 양의 Infinity일 때만 처리하고, Infinity만 있을 때는 `range_max`를 clear distance로 해석. 유한 장애물값이 하나라도 있으면 최소거리로 안전 정지 판단.
- NaN, 0, 불충분한 전방 빔 및 통신 지연은 계속 STOP. 기존 0.40m 정지 임계값 변경 없음. 다음 실제 Run에서 전방 빔 수·finite/+inf/invalid를 출력해 확인.
- 선행 S1·S2-MAP-01 실제 Gazebo PASS는 유지. 실제 지도 생성 GREEN 전 S2-MAP-02는 HOLD.

## RESOLVED (2026-11-20 KST)
- Real Gazebo 33.3m route and 12/12 waypoints / quality / SaveMap / reload PASS: Run #44551738811, #44551726313. Odom-based CI waypoint coordinates were replaced only in CI route follower by Gazebo actual model pose, and no-return +inf LaserScan distinguished from invalid NaN/0. Front 0.40m STOP preserved.
- Linked final map: maps/restaurant_map.yaml and .pgm in main via PR #8. Incident closed without changing official SLAM Toolbox or World geometry.
