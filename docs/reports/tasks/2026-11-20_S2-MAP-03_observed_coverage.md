# S2-MAP-03 — 회색 unknown 영역 실제 관측 확대, 교육용 검증 보고서

- 작성: 2026-11-20 KST
- 범위: 첨부 WSL2 RViz의 저장 지도 unknown(205) 감소. 추가 실제 Gazebo LiDAR/SLAM 관측을 사용하며 synthetic OccupancyGrid 보정은 금지.
- 기존 성공 기준선: S2-MAP-01/02, 저장 지도 PGM SHA256 `b20bebc872145fa674315757c61e5bb10444eb4c5067ac34d5948d679157e8d8`, S3-AMCL-01/S3-NAV-02 PASS 보존. main 지도/manifest 파일 변경 없음.

## 최초 계측

PGM binary P5 원본 분석: 201x180=36180셀, known=26399(72.965%), free=24811, occupied=1588, unknown=9781(27.035%). S2-MAP-02의 기존 33.3m/12-waypoint 성공은 Map Save/Reload/필수 경로 연결 성공이지 구석 관측 완료를 의미하지 않습니다.

## 개선 방법

기존 SURVEY 경로는 불변. `--enhanced-survey` 옵션에서만 추가 관측 위치를 운용. 신뢰할 수 있는 Gazebo SDF의 실제 장애물 모서리 기준 정적 최단 간격 약 0.48m, 실제 Scan stale/정지 안전 기준 유지. 기존 Waffle Pi LiDAR와 SLAM Toolbox /map, Map Saver /save_map, Map Server 재로딩 재사용. 새로운 planner, supervisor, 모터 제어, World 수정, WSL2 재매핑 없음.

## Cycle 01 — 경로 증강/실제 Map L2

- 실행 SHA `26c2a07f397755f7d188cf3813b96cc3a7e02c8f`
- [실제 Gazebo GREEN #44662701035](https://github.com/silverbjin/samsung_AXI/actions/runs/44662701035), 48.34m, 21구간, 2771 Scan.
- 결과: known=27701 / 36582 = 75.723%, free=26060, occupied=1641, known area 69.2525m², free connected PASS, 저장/재로딩 PASS.
- Artifact #14596865816, SHA256 ZIP `d395fce56ec6a4ca6ee6df30c3fa550b038c277059211c7f5d094315620be6a3`. 이 ZIP은 당시 소스 SHA의 후보 증거일 뿐 main 출고 지도는 아님.

## Cycle 02 — 중앙 오른쪽 잔여 unknown 분리, 회귀 RED → GREEN

- 최초 후보 `ad4d96d5eb858352b20b76074fc8bd163d1326a6`에서 문자열 치환이 원래 SURVEY에도 적용되는 회귀 발생: Run #44663909233 L0 실패, Gazebo L2 SKIPPED. 실제 지도를 잘못 출고하지 않았음.
- 최소 수정 `ea78fe457e7cfc88754a88f788e08eabd098d766`: 기존 33.3m SURVEY 원상복구, OBSERVATION_SURVEY에만 동측/중앙 관측 위치 추가. 별도 실제 Gazebo L2 수행.
- [실제 Gazebo GREEN #44664079567](https://github.com/silverbjin/samsung_AXI/actions/runs/44664079567): 58.14m/27구간, 실제 3354 Scan, GT 20032회, SLAM SaveMap+Reload PASS, pickup→table3 free-connected true.
- 새 PGM: 202×185=37370셀, known=30394(81.333%), free=28653, occupied=1741, unknown=6976. 지도 프레임 origin [-2.379,-2.440,0], resolution 0.050m.
- 기존 26,399→30,394 known (+3995셀), known area 65.9975→75.985m² (+9.9875m²). 관측률 약 72.97→81.33%(+8.36%p). 기준선보다 PGM 격자 크기도 바뀌었으므로 비율과 실제 면적을 함께 보고.
- Map PGM SHA256 `aedaed8f89e703f33ef22f9cf0c9d8f77b11763157d6e3a61c839a58fe871f00`; YAML SHA256 `378b22b3af4baa7ec78373a5a6095350d7447ea2907d7dcd9682aba03b41fceb`.
- [Compact Artifact #14596882850](https://github.com/silverbjin/samsung_AXI/actions/runs/44664079567/artifacts/14596882850), ZIP SHA256 `a9c55ae94fc652cd0c8bf4d3afc1e152f8123d2efec88634451a5d2949dfb798`.
- 월드 SDF collision 내부, 가구/카운터 차폐 영역은 LiDAR로 직접 Free 판정할 수 없음. 회색을 흰색으로 조작하지 않음.

## 출고 판정

- `S2_MAP03_REAL_GAZEBO_MAPPING_QA_PASS`: YES, 후보 지도를 CI에서 실제 관측·저장·재로딩 검증.
- `S2_MAP03_MAP_IN_MAIN`: NO. 현재 main의 원본 지도 및 기존 S3 해시 계약은 불변.
- `S3_AMCL_NAV2_WITH_NEW_MAP`: NOT_RUN (새 202×185 후보를 S3 기존 released-map SHA 계약에 묶기 전).
- `WSL2_GUI_WITH_NEW_MAP`: NOT_RUN.
- Draft PR #13의 지도 확대 코드는 리뷰 후보. 실제 PGM은 별도 Actions Artifact에 출고됐으나, S3 호환성 실증·영구 저장소 게시가 완료되기 전에는 main으로 지도 변경을 병합하지 않음.
- 요청된 다음 단계: 2D Pose Estimate 자동화, 마지막 단계 RTF >=90%. 1단계 지도 후보 main 출고 확인 전 2/3 실구현은 순서 정책상 보류.

## Cycle 03 — 실제 AMCL·Nav2 개선 지도 호환성 CI GREEN

- 지도 영구 보존: [GitHub Publisher Run #44665906184](https://github.com/silverbjin/samsung_AXI/actions/runs/44665906184) PASS, `maps/s2-map03-release-20261120` 브랜치의 `maps/candidates/s2_map03/{restaurant_map.pgm,restaurant_map.yaml,restaurant_map_quality.json,restaurant_map_manifest.json}` 출고. 기존 main `maps/restaurant_map.*` 보존.
- `validate_s2_map03_candidate()`는 Run #44664079567, source SHA `ea78fe457e7cfc88754a88f788e08eabd098d766`, Map PGM/YAML/quality 파일 SHA256, 원본 World, known fraction >=.81, pickup↔Table3 connected를 검사.
- [후속 S3 후보 L2 GREEN Run #44666192437](https://github.com/silverbjin/samsung_AXI/actions/runs/44666192437): L0 PASS, ROS Jazzy/Nav2/Gazebo Harmonic L1 PASS, 실제 저장 지도 기반 AMCL·TF 및 두 개의 NavigateToPose Action SUCCEEDED.
- TABLE_3: Odom 5.204m, AMCL 도착 오차 0.113m; PICKUP_RETURN: Odom 5.294m, AMCL 도착 오차 0.021m.
- [S3 개선지도 compact evidence #14598031271](https://github.com/silverbjin/samsung_AXI/actions/runs/44666192437/artifacts/14598031271), ZIP SHA256 `478e4a29e750c7fb762d9b6dfb24d648e95ecf167bb4c7fd20d4953cfda4d7d9`.
- **판정: S2-MAP-03 지도 관측 확대/실제 Gazebo 저장 및 재로딩 = PASS, S3 후보 지도 AMCL/Nav2 실제 왕복 = PASS.** 강사 WSL2 GUI 인수 및 자동 initial pose와 RTF 개선은 별도 미실시.
