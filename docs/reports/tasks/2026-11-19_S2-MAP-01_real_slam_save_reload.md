# S2-MAP-01 — 실제 SLAM Toolbox 지도 저장·재로딩 개발 경과
- 작성: 2026-11-19 KST
- 기준: P0 S1 검증 HEAD 3beb04483ea57bdded06178f99cf70dce542d910
- 목적: 임의의 가짜 지도 없이 Gazebo 물리 LiDAR Scan/Odom/TF→SLAM Toolbox OccupancyGrid→Nav2 SaveMap→Map Server 재로딩 실증.
- 설계: 기존 world/SLAM 공식 구현을 재사용. +x 방향 0.3m 짧은 실제 /odom 이동, Nav2 Goal 사용 없음.
- CI: L0 계약 테스트; L1 colcon; L2 real Gazebo 지도 생성·저장·재로딩 추가.
- 지도 파일 및 ROS 로그: Actions artifact로 저장; 성공 판정은 실제 Run 확인 후 업데이트.
- 제한: 지도 파이프라인 PASS와 전체 레스토랑 지도 완주/AMCL/S3 배달 인수는 별개.
- 오류 발생 시 docs/reports/issues 문제 해결 보고서 작성·최초 실패 경계 좁혀 재검.

## 첫 CI 실패·수정 (S2-CI-01)
- [Run #44488381423](https://github.com/silverbjin/samsung_AXI/actions/runs/44488381423): L0 24 PASS/1 FAIL, nounset source setup 위치 계약. 실제 Gazebo 테스트는 시작되지 않음.
- `set +u`를 각 ROS `source` 주변에만 분리해 최소 수정. [이슈 보고서](../issues/2026-11-19_S2-CI-01_nounset_source_contract.md). 재검 전 GREEN 주장 금지.

## 최종 공개 CI GREEN 및 main 출고 (2026-11-19 KST)
- P0-S1 기준선: PR #4 → main `c124d3d83f323c56a0cc14497314a0e3e5af437d` / L0·L1·L2 GREEN [#44486003784](https://github.com/silverbjin/samsung_AXI/actions/runs/44486003784).
- S2 최초 실패(계약): [Run #44488381423](https://github.com/silverbjin/samsung_AXI/actions/runs/44488381423) L0 1 FAIL, 실제 Gazebo 시작하지 않음. ROS setup의 nounset 복구 범위 한정 수정.
- S2 최종 GREEN: [Run #44488688236](https://github.com/silverbjin/samsung_AXI/actions/runs/44488688236), commit `0ed197d9bcfcff74868798d6afd7f18d5db21ecd`. L0·L1·L2 센서·실제 Gazebo SLAM·저장·재로딩 모두 success.
- **실제 런 증거**: `S2_REAL_GAZEBO_SCAN_MAP_TF_RECEIVED`; `S2_REAL_ODOM_DISPLACEMENT_M=0.381`; `S2_OFFICIAL_SAVE_MAP_PASS=.../restaurant_map.yaml`; `RESTAURANT_S2_L2_REAL_GAZEBO_SLAM_SAVE_RELOAD_PASS_NO_NAV_GOAL`.
- 성공 아티팩트: `restaurant-s2-real-map-44488688236`, ID `14510624983`, `restaurant_map.yaml` + `.pgm` + 축약 로그; 2026-11-24까지 5일 보관 예정. 장기 보관할 교육용 지도를 만든 것이 아니며 그 조건에서 생성한 CI **부분 지도**임.
- PR #5 → main 병합 SHA `344dacbd47760c32898dffdc6ad43ec21cb9f0c5`.
- **판정:** `S2_MAP_PIPELINE_CI=PASS` / `S2_WHOLE_RESTAURANT_MAP=NOT_RUN` / `AMCL=NOT_RUN` / `S3_NAV=NOT_RUN`. CI 내 짧은 0.381m의 물리 이동을 매장 전체 탐색으로 승격하지 않음.
- 다음으로 현장에서 동일 공식 SLAM Toolbox를 통해 실제 매장 영역을 충분히 탐색하고 `scripts/s2_save_map_candidate.sh`로 후보 저장 → RViz 확인 후 최종 지도 채택. 이 단계가 끝나야 S3 AMCL/Goal에 진입.
