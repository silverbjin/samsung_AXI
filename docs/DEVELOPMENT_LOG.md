# 개발·디버깅 교육 로그

## Cycle 01 — S0 재사용 점검 → S1 최소 월드 소스 (2026-11-19)

**목표:** AXIA 본류에 영향 없이 레스토랑 World·Waffle Pi를 독립 실행하도록 구성.

**근거:** 공식 ROBOTIS Jazzy `model.sdf`는 `gpu_lidar` + RGB `camera`이며, 브리지 `/cmd_vel`은 `TwistStamped`. 공식 Nav2 Jazzy는 기본 `Twist`; Navigation launch가 Velocity Smoother와 Collision Monitor를 포함함. 기존 AXIA D06 설정은 격리 시험 토픽으로 실제 사용 금지.

**실패 경계(정적 조사):** AXIA D05의 이전 `feature/d05-mounted-rgbd-actor-live-20261113` ref를 재조회했으나 `404 No commit found for ref` 응답. 기존 Branch가 존재한다는 가정으로 설치 스크립트를 작성하지 않고, 조회 가능한 AXIA D08 `rgbd_camera` 구조만 참조하여 독립 로컬 overlay를 설계함.

**최소 조치:** 독립 `restaurant.sdf`와 세 ROS package 구조, 단일 /cmd_vel Bridge YAML 생성. 기본 World는 공식 Waffle Pi SDF 파일을 직접 사용; S2부터만 RGB-D overlay를 생성하는 방식으로 분리. Nav2/SLAM 및 Waffle Pi 바퀴 물리 코어는 개발하지 않음.

**현장 검증:** 이 작성 환경에 ROS 2 Jazzy와 Gazebo 실행 파일 없음. 따라서 World가 WSLg에 렌더링되는지, 실제 주행 성공 여부는 **미검증**. Python 문법 및 SDF XML·토픽 계약의 작은 정적 검사는 `tests/`에 분리.

**다음 경계:** 강사 WSL2에서 `./scripts/restaurant_demo.sh world`를 1회 실행해 S1 GUI+LiDAR+odom을 확인. 실패 시 `logs/world_*.log`에서 첫 에러만 좁혀 수정, S1 성공 전 S2/3 결과를 PASS로 기록하지 않음.

## Cycle 02~ — 현장 최초 실패/수정 내역

아직 없음. 새 레스토랑 Gazebo 실주행 증거가 없어 추정 오류/성공을 기록하지 않습니다.

## Cycle 02 — CI 준비 후보 (2026-11-19)

신규 GitHub `silverbjin/samsung_AXI`의 empty 상태를 GitHub 연결로 조회했다. 현재 로컬 파일에 Actions workflow `restaurant-ci.yml`, 실제 ROS/Gazebo 메시지를 구독하는 `ci_gazebo_smoke.py`, 생성 오버레이 검증 `ci_check_generated.py`를 추가했다. L0 local pytest 5개 및 workflow YAML 파싱은 통과했다. **원격 push/Actions Run은 아직 하지 않았으므로 CI GREEN 증거는 없다.** Headless RGB-D/scan 렌더링은 GitHub runner에서 처음 실측해야 하는 경계다.

## 공통 정책·보고서 색인

| 날짜 | 작업 ID | 보고서 | 검증 범위 |
|---|---|---|---|
| 2026-11-19 | DOC-01 | [공통 보고서 정책 도입](reports/tasks/2026-11-19_DOC-01_reporting_policy_setup.md) | 문서 정적 확인 / GitHub 원격 반영 NOT_RUN |
| 2026-11-19 | INFRA-01 | [컨테이너 GitHub DNS 접근 실패](reports/issues/2026-11-19_INFRA-01_container_github_dns.md) | 로컬 Git 사용 가능 / 원격 Push HOLD |

- 2026-11-19 · **PUBLISH-01 / 원격 GitHub 게시 완료**: [경과 보고서](reports/tasks/2026-11-19_PUBLISH-01_github_initial_import.md), [INFRA-01 해결 경로](reports/issues/2026-11-19_INFRA-01_container_github_dns.md). 원격 소스 50개·Tree SHA 일치, 최초 CI L0 PASS. L1/L2는 Actions Run #44443691545로 추적.

- 2026-11-19 · **CI-01 / Jazzy setup nounset 충돌**: [경과 보고서](reports/tasks/2026-11-19_CI-01_actions_nounset_recovery.md), [문제 해결 보고서](reports/issues/2026-11-19_CI-01_nounset_ros_setup.md), 최초 [Actions Run #44443691545](https://github.com/silverbjin/samsung_AXI/actions/runs/44443691545) L1 실패, 로컬 최소 회귀 6 PASS, CI 재검 필요.

- 2026-11-19 OWNER-01: pinned GitHub WSL2 one-shot + uniform RGB-D world path. Static 10 PASS, PR CI and WSL2 NOT_RUN: [task report](reports/tasks/2026-11-19_OWNER-01_wsl2_one_shot_predeployment.md).
- 2026-11-19 CI-02: setup-ros bootstrap long-running; isolated CI container candidate, root cause tentative, retest pending: [issue report](reports/issues/2026-11-19_CI-02_setup_ros_bootstrap_stall.md).
- 2026-11-19 OWNER-01 released: PR #1 → main `f211d04` after L0/L1/L2 NO_GOAL GREEN Run #44447853175; WSL2 L3 NOT_RUN: [report](reports/tasks/2026-11-19_OWNER-01_wsl2_one_shot_predeployment.md).

- 2026-11-19 HW-02: [기기 분리 진단](reports/tasks/2026-11-19_HW-02_samsungaxi_profile.md) 및 [GPU-01 llvmpipe](reports/issues/2026-11-19_GPU-01_wslg_llvmpipe.md): 기록 완료, D3D12 현장 개선 NOT_RUN.

- 2026-11-19 GPU-02: [실기 D3D12 GLX 경로 확인·국소 실행기](reports/tasks/2026-11-19_GPU-02_glx_route_verified.md) / [GPU-01 원인 분리](reports/issues/2026-11-19_GPU-01_wslg_llvmpipe.md): GLX PASS, Gazebo 개선 NOT_RUN.

- 2026-11-19 GPU-02-EXPORT: [원격 스크립트 이스케이프 결함·Blob SHA 일치 복구](reports/issues/2026-11-19_GPU-02_transport_escaping.md) — 배포 전 검출 및 수정 PASS.

- 2026-11-19 EVD-01: [Gazebo 경량 ZIP/RTF 진단 경과](reports/tasks/2026-11-19_EVD-01_compact_evidence_bundle.md) / [사용가이드](EVIDENCE_BUNDLES.md): 정적·모의 5 PASS, 강사 자동 ZIP NOT_RUN.

- 2026-11-19 P0: [S1 최적화/PC분리/경량 증거 통합](reports/tasks/2026-11-19_P0_S1_verified_baseline.md). PR#3 GREEN #44483609465, PR#2 최신 CI cancelled → 통합 HEAD L2 재검 필수.

- 2026-11-19 S2-MAP-01: [실제 SLAM Map Save/Reload 통합 실증](reports/tasks/2026-11-19_S2-MAP-01_real_slam_save_reload.md) — L0/L1/L2 새 CI 수행 전 NOT_RUN; 강사 전체 매장 지도 별도.

- 2026-11-19 S2-CI-01: [L0 nounset source 개별 보호 실패 및 수정](reports/issues/2026-11-19_S2-CI-01_nounset_source_contract.md), 최초 #44488381423 L0 RED, 실제 L2 미진입.

- 2026-11-19 P0 확정: PR #4 → main `c124d3d`, [L0/L1/실제 Gazebo L2 GREEN #44486003784](https://github.com/silverbjin/samsung_AXI/actions/runs/44486003784). S1 고정, S2는 별도.
- 2026-11-19 S2-MAP-01 완료(파이프라인): PR #5 → main `344dacb`, [Run #44488688236](https://github.com/silverbjin/samsung_AXI/actions/runs/44488688236) L0·L1·L2 실제 SLAM /map, Odom 0.381m, Map Saver YAML/PGM, Map Server 재로딩 PASS. [작업 보고서](reports/tasks/2026-11-19_S2-MAP-01_real_slam_save_reload.md). 전체 매장 지도·AMCL은 NOT_RUN.
- 2026-11-19 S2-CI-01 종결: [문제 해결 보고서](reports/issues/2026-11-19_S2-CI-01_nounset_source_contract.md) L0 nounset RED→최소 수정→Run #44488688236 GREEN.

- 2026-11-19 S2-CI-02: [main 병합 후 APT HTTP 80 저장소 연결 타임아웃](reports/issues/2026-11-19_S2-CI-02_ubuntu_apt_network.md), Run #44520735057 L0 PASS / 런타임 설치 실패; 실패 Job만 1회 재검.
