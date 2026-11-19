# S2-MAP-02 — CI 전체 레스토랑 지도 생성 개발 경과

- 일자: 2026-11-19 KST
- 코드 시작점: main 7b141f4c9670afc04ec4caa69a532a43cc5f25b6
- 선행 S2-MAP-01: 실제 Gazebo SLAM→Map Saver→Map Server 재로딩 Run #44488688236 PASS (유지)
- 문제: 0.381m 짧은 실제 로봇 이동은 전체 매장 픽업→테이블3 지도를 보장하지 않음.
- 재사용: 현재 SDF World와 ROBOTIS Waffle Pi, ros_gz_bridge, SLAM Toolbox, Nav2 Map Saver/Map Server; 새로운 SLAM/Planner·Safety Supervisor는 개발하지 않음.
- 신규 코드: 고정 사전검증 경로 (약 33.3m), Odom·LiDAR 안전 확인, 실제 Map 범위 및 Free 연결 품질검사, 지도 저장·재로딩, SHA256 JSON.
- 출고 방식: CI가 YAML/PGM을 Artifact에 저장하고 GREEN 시 지도 후보 브랜치를 생성; 자동 main 병합 금지.
- ROS CI 테스트: 기존 S2-MAP-01 센서 L2 유지, 별도 map02 실제 Gazebo L2 추가. L0에서는 SDF 장애물 경로·가짜 지도 거부·Free 연결 정적 계약.
- 위험/한계: 고정 경로는 미검증 상태에서 실제 주행을 시작하지 않으며 /scan 품질·전방 안전이 실패하면 STOP + HOLD. 지도 품질의 임계값은 MVP 탐색 증거로서 임의 고정이며 실측 후 조정 여부 판단.
- 성공 판정: 실제 Actions L0/L1/L2, 탐색 완료, 지도 품질+재로딩, 지도 후보 SHA 검증까지 확보해야 MAP02 PASS.
- 현 상태: **실제 L2 검증 전까지 NOT_VERIFIED**. WSL2 재매핑 금지. AMCL/Nav2 S3은 실 지도 승인 이후.
- CI 외부 인프라: S2-CI-02 APT 포트 80/443 실패는 별도 이슈이며, 로봇 알고리즘 실패로 취급하지 않음.

## Cycle 01 — RED → 최소 진단·회피 경로 수정
- 첫 공개 Actions L0 30 PASS / L1 Jazzy + S1 L2 + S2-MAP-01 L2 PASS, S2-MAP-02 첫 실주행 실패.
- RED: [Run #44544900046](https://github.com/silverbjin/samsung_AXI/actions/runs/44544900046); 경유점 1·2 실제 Odom 도달 후 3번으로 이동하면서 `LIDAR_FORWARD_CLEARANCE_BLOCKED_3` 안전 정지.
- 실패 경계: 지도 생성·저장 이전의 실제 주행 안전 정지. 이를 SLAM 품질 오류나 APT 인프라 문제로 판정하지 않음.
- 정적 경로는 장애물 중심 거리 최솟값 약 0.32m였고, 실제 전방 LiDAR 정지 임계값은 0.40m. 목표 도착 허용 오차 .16m 때문에 이론적 여유가 부족할 수 있다는 단일 가설 설정.
- 최소 수정: 북서측 경로를 서쪽으로 0.20m, 동측 회랑을 동쪽으로 이동하고 테이블에서 멀리 떨어진 y=1.20m 경로 사용. 대각선 복귀 대신 직교 복귀, 도착 허용 오차 0.09m. 기하학적 정적 최단 여유 약 0.48m.
- 안전 임계값 0.40m·LiDAR 실측·로봇 물리·SLAM 설정은 그대로 유지. 재발 시 Odom·Target·최소 전방 Range·Scan 각도를 오류에 출력하여 직접 원인 확인.
- 이 수정은 **GREEN 확인 전 후보**입니다. 지도 품질 PASS로 임의 승격하지 않습니다.

## Cycle 02 — 안전 정지 원인 분리
- [Run #44546324681](https://github.com/silverbjin/samsung_AXI/actions/runs/44546324681): waypoint1·2 통과, waypoint3 Odom(-1.126,3.924), yaw1.582, 전방 0.394m < 0.400m로 안전 정지.
- 다음 사이클에서는 SDF 예상 거리/실제 최소 빔 각도/월드 좌표를 읽기 전용 계측. 정지 기준 완화 없음. [이슈](../issues/2026-11-19_S2-MAP02-CI01_lidar_stop.md).

## Cycle 03 — 실제 물리 Pose와 Odom 불일치 원인 분리
- Run #44547524892의 LiDAR 전방 0.375m와 Odom 기반 SDF 최근접 0.755m 불일치. Gazebo SceneBroadcaster 원본 모델 Pose를 **읽기 전용**으로 단일 계측한 뒤 수정 여부 판단. 보고서: [S2-MAP02-CI01](../issues/2026-11-19_S2-MAP02-CI01_lidar_stop.md).

## Cycle 04 — CI 경로 추종에서 GT/Odom 차이 수정
- 실제 모델 위치와 휠 Odom 추정 간 약 0.60m 차이를 직접 계측. **CI survey control에만** Gazebo 실 Pose 사용하고 원래 LiDAR/SLAM/Odom 데이터로 OccupancyGrid 생성.
- 물리 안전 가드 동일, GT stale시 STOP/HOLD. 저장 지도/AMCL S3는 별도 인수. 실제 Run GREEN 전 S2-MAP-02 완료 주장 금지.
