# S3-AMCL-01 — 검증된 실제 지도 기반 AMCL·Nav2 사전검사

## 선행 S2 인수
S2-MAP-02의 실제 Gazebo SLAM 33.3m/12개 waypoint와 지도 품질 검사 완료.
maps/restaurant_map.yaml, maps/restaurant_map.pgm, map manifest와 품질 JSON이 main에 출고되었습니다.
WSL2에서 수동 지도 생성은 수행하지 않습니다.

## 프레임 정합
기존 tables.yaml에 기록된 픽업(-2.60,-2.20)과 테이블3(2.65,-1.82)는
실제로는 Gazebo World 좌표이며, S2 SLAM 저장 지도의 map 원점과 동일하지 않습니다.
잠정 SLAM map pickup=(0,0), table3 접근=(5.25,0.38).
실제 PGM에서 두 지점의 알려진 자유 영역 연결과 AMCL 초기 위치를 확인해야 합니다.

## S3-AMCL-01 검증
1. L0: World / 지도 YAML·PGM / 품질 JSON / SHA256 매니페스트 검증
2. L1: 공식 ROS Jazzy / Gazebo Harmonic / Nav2 패키지 빌드
3. L2: 실제 Gazebo 센서, 저장 Map Server, AMCL pose, map→odom TF, NavigateToPose 액션 서버 준비 확인
4. 아직 navigation goal은 전송하지 않습니다. Goal 없이 준비 조건을 검증한 후 다음 단위에 진행합니다.
5. 성과물: AMCL preflight JSON, 축약 로그, 교육용 최초 실패 경계 보고서

성공 메시지: RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL

강사 WSL2는 CI GREEN을 확인한 동일 소스/지도를 가져와 GUI에서 최종 인수만 수행합니다.
