# S2-MAP-02 — CI 전체 레스토랑 지도 생성 개발 경과

- 일자: 2026-11-19 KST
- 코드 시작점: main 7b141f4c9670afc04ec4caa69a532a43cc5f25b6
- 선행 S2-MAP-01: 실제 Gazebo SLAM→Map Saver→Map Server 재로딩 Run #44488688236 PASS (유지)
- 문제: 0.381m 짧은 실제 로봇 이동은 전체 매장 픽업→테이블3 지도를 보장하지 않음.
- 재사용: 현재 SDF World와 ROBOTIS Waffle Pi, ros_gz_bridge, SLAM Toolbox, Nav2 Map Saver/Map Server; 새로운 SLAM/Planner·Safety Supervisor는 개발하지 않음.
- 신규 코드: 고정 사전검증 경로 (약 31.35m), Odom·LiDAR 안전 확인, 실제 Map 범위 및 Free 연결 품질검사, 지도 저장·재로딩, SHA256 JSON.
- 출고 방식: CI가 YAML/PGM을 Artifact에 저장하고 GREEN 시 지도 후보 브랜치를 생성; 자동 main 병합 금지.
- ROS CI 테스트: 기존 S2-MAP-01 센서 L2 유지, 별도 map02 실제 Gazebo L2 추가. L0에서는 SDF 장애물 경로·가짜 지도 거부·Free 연결 정적 계약.
- 위험/한계: 고정 경로는 미검증 상태에서 실제 주행을 시작하지 않으며 /scan 품질·전방 안전이 실패하면 STOP + HOLD. 지도 품질의 임계값은 MVP 탐색 증거로서 임의 고정이며 실측 후 조정 여부 판단.
- 성공 판정: 실제 Actions L0/L1/L2, 탐색 완료, 지도 품질+재로딩, 지도 후보 SHA 검증까지 확보해야 MAP02 PASS.
- 현 상태: **실제 L2 검증 전까지 NOT_VERIFIED**. WSL2 재매핑 금지. AMCL/Nav2 S3은 실 지도 승인 이후.
- CI 외부 인프라: S2-CI-02 APT 포트 80/443 실패는 별도 이슈이며, 로봇 알고리즘 실패로 취급하지 않음.
