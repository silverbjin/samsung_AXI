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
