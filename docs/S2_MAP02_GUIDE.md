# S2-MAP-02 — CI 기반 레스토랑 전체 지도 생성·품질 검증·출고

## 선행 검증
S2-MAP-01은 실제 Gazebo/SLAM Toolbox/SaveMap/Map Server 재로딩이 PASS입니다.
Run #44488688236의 0.381m 짧은 탐색과 부분 지도는 그대로 보존합니다.

## S2-MAP-02 작업 목표
GitHub Actions에서만 레스토랑 SDF의 고정 탐색 경로를 따라 실제 Waffle Pi가 이동하고,
LiDAR로 생성한 ROS OccupancyGrid를 공식 SLAM Toolbox에서 받아 YAML+PGM으로 저장합니다.
다른 로봇 프로젝트와 하드웨어 프로파일을 공유하지 않습니다. 강사 WSL2 재매핑은 **금지**합니다.

### CI 탐색
- 생성 코드: `scripts/ci_s2_map02.py`, 경로/품질 계약: `scripts/s2_map02_contract.py`
- 경로: 시작 (-2.60,-2.20)에서 북·서·동·남쪽 영역을 순회하는 약 31.35m 고정 경로
- 월드의 벽·테이블·의자·사람형 모델과 최소 0.27m 중심 간격의 충돌 가능성을 정적 검사
- 실제 Odom 위치/회전과 LiDAR 전방 장애물에 따라 속도 명령을 제한/정지
- 계획 알고리즘을 교체하지 않으며 별도의 Nav2 Goal을 보내지 않음

### 실제 지도 품질 게이트
- Scan/Odom/TF와 SLAM `/map` 관찰, 각 waypoint 실제 도달
- 최소 관측된 지도 가로 7.0m, 세로 6.0m, 자유 1,500셀, 점유 120셀, 알려진 2,400셀
- 픽업 → 3번 테이블 접근 위치까지 지도상 **실제 관측된 자유 영역으로 연결**
- 공식 Nav2 `/map_saver/save_map`으로 YAML·PGM을 저장하고 독립 Map Server Lifecycle 재로딩
- 위 검증을 모두 만족한 경우에만 `RESTAURANT_S2_MAP02_L2_FULL_COVERAGE_PASS`를 출력
- 이 계측은 MVP 전체 이동 통로 관측 기준이며 모든 픽셀의 참값 보장/AMCL 성공은 별개

### 지도 출고 — GitHub만 사용
- Actions artifact `restaurant-s2-map02-full-<Run ID>`: 지도 2파일·품질 JSON·축약 로그
- 성공한 feature 브랜치의 push 실행에서 SHA256/원본 world SHA를 확인한 뒤
  `maps/s2-map02-<Run ID>` **지도 후보 브랜치**를 자동 생성
- 후보에는 `maps/restaurant_map.yaml`, `.pgm`, `restaurant_map_quality.json`,
  `restaurant_map_manifest.json`을 포함
- 지도 후보 브랜치 PR을 검수해 main 병합. Actions가 main을 자동 변경하지 않음
- 지도 검증이 끝나면 AMCL/Nav2 S3는 이 커밋을 재사용하며 WSL2 수동 지도 생성 불필요

### 미완료/이슈 구분
- ROS/Gazebo 및 공식 패키지 CI는 GitHub Ubuntu APT 미러 접속 장애가 관찰되어 있습니다.
- 외부 APT 실패를 SLAM 실패로 보고하지 않고 `docs/reports/issues` 문제 해결 보고서로 보존합니다.
- 실제 Run L2 성공 및 지도 아티팩트 확인 전까지 `S2_MAP02=HOLD`, S3=NOT_RUN.
- 성공한 S2-MAP-01의 PASS는 유지합니다.

참고: Nav2 Jazzy 공식 Map Saver 및 SLAM Toolbox 문서
https://api.nav2.org/nav2-jazzy/html/md_nav2_map_server_README.html
https://ros-navigation.github.io/mkdocs.nav2.org/lyrical/tutorials/general_tutorials/navigation2_with_slam/navigation2_with_slam/
