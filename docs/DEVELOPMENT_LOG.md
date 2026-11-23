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

- 2026-11-19 S2-CI-02 최종 HOLD: HTTP 80 / GitHub mirror+file 503 / HTTPS 443 연결 실패 재현. [문제 보고서](reports/issues/2026-11-19_S2-CI-02_ubuntu_apt_network.md). PR #6은 미검증으로 main 미병합, PR #5 실제 Gazebo GREEN과 메인 핵심 소스 Blob 일치 보존.

- 2026-11-19 S2-MAP-02: [CI 전체 지도 탐색·품질·아티팩트 출고](reports/tasks/2026-11-19_S2-MAP-02_ci_full_map.md) — 실제 HEAD L2 검증 전 후보; S2-MAP-01 PASS 고정.

- 2026-11-19 S2-MAP02-CI01: [새 지도 탐색 첫 L2 LiDAR 안전 정지](reports/issues/2026-11-19_S2-MAP02-CI01_lidar_stop.md), [Run #44544900046](https://github.com/silverbjin/samsung_AXI/actions/runs/44544900046) waypoint 1·2 PASS→waypoint 3 STOP. 보수적 회랑 보정·계측 후 재검.

- 2026-11-20 S2-MAP02-CI02: [Gazebo 전체 지도 L2 GREEN, Git 출고 차단](reports/issues/2026-11-20_S2-MAP02-CI02_map_gitignore.md). 최종 YAML/PGM 두 파일만 Git 추적 예외로 추가, 재검 전 출고 HOLD.

- 2026-11-20 **S2-MAP-02 릴리스 최종 PASS**: PR #7 source main 39213564, PR #8 map-only main d4fd5f19, actual Gazebo 33.3m/12/12/Scan1842, YAML/PGM SHA256 + SaveMap reload. [보고서](reports/tasks/2026-11-19_S2-MAP-02_ci_full_map.md). WSL2 지도 재생성 금지, 다음 S3 AMCL/Nav2.

- 2026-11-20 **S3-AMCL-01 PASS**: [Run #44561573820](https://github.com/silverbjin/samsung_AXI/actions/runs/44561573820) 저장 지도 201×180, AMCL pose/TF, Nav2 action READY/NO GOAL 검증. PR #9 main 2e0b1459. [보고서](reports/tasks/2026-11-20_S3-AMCL-01_real_map_preflight.md). 다음 S3 Goal/물리 주행은 별도.

- 2026-11-20 S3-NAV-02 착수: 기존 S3-AMCL-01 L2 GREEN 재사용, 실제 map 좌표 pickup(0,0)/table3(5.25,0.38)로 Nav2 NavigateToPose Action 배달·복귀 시험. 2구간 action status·AMCL·물리 odom 증거 필요. [작업 보고서](reports/tasks/2026-11-20_S3-NAV-02_delivery_return.md).

- 2026-11-20 S3-NAV-CI01 해결: [실제 Gazebo L2 Run #44564927414](https://github.com/silverbjin/samsung_AXI/actions/runs/44564927414) Goal 전 Nav2 Lifecycle ACTIVE→TABLE_3/RETURN 물리 Odom 5.185m/5.214m, AMCL 오차 0.192m/0.066m, 2회 Action SUCCEEDED. [보고서](reports/tasks/2026-11-20_S3-NAV-02_delivery_return.md).
- 2026-11-20 S3-NAV-CI02: [배달 성공 증거의 kind 명칭 불일치](reports/issues/2026-11-20_S3-NAV-CI02_evidence_kind.md) 교정, main S3 CI 실제 주행 게이트 유지.

- 2026-11-20 S3-NAV-CI03: [연속 Nav2 2세션의 두 번째 Action 서버 타임아웃](reports/issues/2026-11-20_S3-NAV-CI03_duplicate_nav_session.md), Run #44644596110 RED. 한 세션으로 중복 제거하여 Run #44646024902 GREEN, 같은 센서/SLAM 유지.
- 2026-11-20 **S3-NAV-02 CI·main PASS**: [PR #10](https://github.com/silverbjin/samsung_AXI/pull/10) main e2e7cf04; [Run #44646848087](https://github.com/silverbjin/samsung_AXI/actions/runs/44646848087) 배달 Odom 5.257m / 오차 0.132m, 복귀 5.219m / 오차 0.126m, Nav2 Lifecycle/2 Action SUCCESS. S1/S2 회귀 [Run #44646848122](https://github.com/silverbjin/samsung_AXI/actions/runs/44646848122) GREEN. [최종 보고서](reports/tasks/2026-11-20_S3-NAV-02_delivery_return.md). WSL2 GUI 및 메뉴별 속도는 별도 인수.

- 2026-11-20 S4-MENU-01 착수: 기존 정상 S2 지도·S3 실제 Nav2 배달/복귀 재사용. `/speed_limit` 토픽 Nav2 Controller 정합, NORMAL 0.23/SOUP 0.11m/s 실제 Odom 속도 비교, 공식 Collision Monitor LiDAR 기반 STOP 및 물리 Gazebo 단일 fixture L2. [작업 보고서](reports/tasks/2026-11-20_S4-MENU-01_speed_safety.md). 아직 CI 실제 GREEN 미확정.

## SmartDish B 담당 데이터 개발 색인 (2026-11-23)
- B-01 라벨/이용조건/스키마 계약: [작업 보고서](reports/tasks/2026-11-23_B-01_label_source_contract.md) — 문서 확인 PASS / 실제 데이터 0건.
- B-02 수집기/형식 검증: [작업 보고서](reports/tasks/2026-11-23_B-02_collect_ingest.md) — 로컬 fixture 테스트 PASS / Gazebo 트레이 NOT_RUN.
- B-03 그룹 분할·C 핸드오프: [작업 보고서](reports/tasks/2026-11-23_B-03_group_split_handoff.md), [디버깅 B-DEBUG-01](reports/issues/2026-11-23_B-DEBUG-01_validation_error_priority.md) — pytest 10/10 PASS, 실제 데이터 NOT_RUN.
- B-04 데이터 계약 CI: [작업 보고서](reports/tasks/2026-11-23_B-04_ci_contract_gate.md) — GitHub Actions 실제 Run 결과는 보고서에서 추적.

- 2026-11-23 **B-06 / 물리 근거 파일 무결성 RED→GREEN**: [작업 보고서](reports/tasks/2026-11-23_B-06_physics_evidence_integrity.md), [B-DEBUG-02](reports/issues/2026-11-23_B-DEBUG-02_unverified_evidence_reference.md) — 미존재 증거 이전 오수용 재현, 최소 수정·로컬 재검 PASS, 물리 라벨 NOT_RUN.
- 2026-11-23 **B-05 / 트레이 RGB 무라벨 캡처 도구**: [작업 보고서](reports/tasks/2026-11-23_B-05_tray_rgb_readonly_capture.md), [초심자 실행 가이드](../ai/docs/B_TRAY_CAPTURE_GUIDE_KO.md) — RGB/BGR 이미지 계약 테스트 PASS, 실제 ROS/Gazebo 카메라 NOT_RUN.

- 2026-11-23 **B-07 물리 증거 재검/DRIFT 차단**: [개발 보고서](reports/tasks/2026-11-23_B-07_evidence_reaudit.md), [RED→GREEN B-DEBUG-03](reports/issues/2026-11-23_B-DEBUG-03_evidence_drift.md). 로컬 19 PASS, 실제 트레이 NOT_RUN. GitHub CI 결과는 PR #37에서 추적.

- 2026-11-23 **B-08 원자적 수집/CSV 롤백**: [작업 보고서](reports/tasks/2026-11-23_B-08_atomic_intake.md), [B-DEBUG-04](reports/issues/2026-11-23_B-DEBUG-04_orphan_ingest.md). 로컬 23 PASS, 실제 Gazebo/모델 NOT_RUN. 원격 CI는 PR #37에 기록.
