# S3-NAV-02 — 저장된 레스토랑 지도에서 실제 Nav2 배달·복귀

- 일자: 2026-11-20 KST
- 시작 main: 62bceefd26e11d9d5d1ecb3fe642cdd6afc0f974
- 선행 PASS: S2-MAP-02 실제 SLAM 33.3m 지도 출고, S3-AMCL-01 실제 MapServer/AMCL/TF/Action server NO-GOAL Run #44561573820.
- 목표: 공식 Nav2 NavigateToPose를 사용해 1번 픽업→3번 테이블→1번 복귀 실제 Gazebo 도착 및 물리 Odom 이동 입증.
- 교정할 기존 문제: delivery_manager.py가 World 좌표(-2.60,-2.20)를 map 좌표로 전달했음. 출고된 S2 map 원점을 사용해 새 s3_map_waypoints.yaml (pickup 0,0 / table3 5.25,0.38)을 별도로 사용.
- 검수: 지도 SHA/Free 연결, AMCL pose/TF, Nav2 액션 서버 준비를 먼저 확인한 다음에만 실제 Goal 시작; Goal status SUCCEEDED, AMCL 위치 오차, 실제 Odom 이동을 각 구간별 확인.
- 정책: WSL2 지도 재생성·CI 성공 우회 금지, 새로운 Planner/SLAM/Safety Supervisor 금지, 기존 Nav2·Collision Monitor와 LiDAR 안전 경계 보존.
- 시작 상태: S3-NAV-02 actual Goal NOT_RUN. 본 파일은 개발 시작 문서이며 결과에 따라 업데이트.
