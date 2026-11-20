# S5-PERF-01 — 강사 WSL2 라이브 RTF 성능 계측·최소 RGB-D 후보 개발 보고서

## 1. 고정 기준선

- Repo `silverbjin/samsung_AXI`, 출발 main `25ae7963f36405cbc3dd6ab7aa78e12efea54231`.
- 기존 `S5_LIVE_FUNCTION_L3=ACCEPTED` 원본: `samsungaxi_gui_20261120T062446Z-5175.zip`, SHA256 `ae9079c0e921a4b64e78fbf15cd50b1628a93c06ef6d6ecdda10ade3aa66761d`.
- 동일 현장 라이브 ZIP 실제 RTF 100개: median `0.8439`, p10 `0.4030`, 90% 이상 44개. 이전 NO_GOAL GUI ZIP `samsungaxi_gui_20261120T035159Z-2823.zip`은 median `0.9992`, p10 `0.6996`. 측정 시점 및 활동 단계가 다르므로 차이를 Gazebo/GPU/CPU의 단일 근본 원인으로 단정하지 않음.
- 현재 `S5_LIVE_RTF_MEDIAN_GE_90_PERCENT=HOLD`와 `S5_SHUTDOWN_CLEAN=HOLD`는 유지. 본 PERF 작업은 종료 경고를 별도 이슈로 보존.

## 2. 첫 관찰 및 가설 제한

- 기존 강사 원샷은 실행 후 약 40초 경과 때 Gazebo Stats를 짧게 100개 수집. 실제 테이블3 왕복의 어느 단계가 얼마나 느렸는지 알려 주지 않음. 따라서 **먼저 시간·주행 단계별 실제 RTF와 CPU/GPU를 동시 계측**하도록 한정.
- 오픈소스 Gazebo Sensors 문서는 `update_rate`가 센서 갱신 빈도를 조정한다고 명시. 기존 S5 리소스에서 Waffle Pi LiDAR는 공식 10Hz, 별도 등록 RGB-D는 **5Hz**이며, 실제 S5 안전정지는 **LiDAR→Collision Monitor** 계약으로 수행. RGB-D의 5→2Hz 하향은 **가설 검증용 후보**이지 성능 향상 확정 수단 아님.
- 기존 출시 맵, AMCL, Nav2, Collision Monitor, 속도 정책, 물리 엔진, 보행자/YOLO/모터 코드는 미변경.

## 3. 개발 결과

1. `scripts/s5_perf_profile.py`: read-only `gz topic -e -t /world/restaurant/stats` 스트리밍에서 주행 단계 마커를 같은 `run.log`로 연결, 약 1Hz 실 RTF·시간·단계별 CSV. `ps` CPU/RSS를 5초마다, 가능한 `nvidia-smi` 값을 15초마다 **참고용**으로 기록. 종료 신호에서 요약 JSON 보존. 값 누락은 추정이나 PASS 처리하지 않음.
2. `scripts/prepare_waffle_rgbd.py`: 기존 5Hz 기본 유지, **명시적인 `--rgbd-rate-hz 2` 후보** 추가. 기존 등록 RGB-D의 이미지 크기·LiDAR·TF/bridge/월드·구동 모델 불변.
3. `scripts/restaurant_demo.sh`: S5 라이브에서만 `SAMSUNGAXI_S5_PERF_MODE=rgbd2`면 후보 2Hz, 미지정·baseline이면 기존 5Hz. 일반 `world`, `mapping`, `navigation`, 교육용 demo의 소스/동작 유지.
4. `scripts/samsungaxi_wsl2_gui_acceptance_once.sh`: `--perf-baseline` / `--perf-rgbd2` 명시 A/B, 기존 Goal 2중 승인·run-id·단일 ZIP 보존. 프로파일러도 정확히 고정된 GitHub RAW SHA에서 다운로드. 기존 `--s5-live --approve-goals`는 기본 5Hz 변경 없음.
5. `tests/test_s5_perf01.py`: 주행 단계 구분, 실제 스크립트 subprocess/가상 gz stats 및 Ctrl+C 증거 출고, RGB-D 5/2Hz XML, 10Hz 공식 LiDAR 보존, 표본 부족 시 90% PASS 차단과 기존 S5 승인 계약 확인.
6. `.github/workflows/restaurant-s5-perf-ci.yml`: 공개 L0 + 공식 ROS Jazzy/Nav2/Gazebo Harmonic 실제 L2. RGBD2 후보에서 **원래의 12초 TTY 지연 승인과 S5 두 Action·Odom 속도·물리 CM STOP을 단일 세션에서 확인**.

## 4. 공개 CI 결과 — 실제 증거

- **[GREEN #44692959074](https://github.com/silverbjin/samsung_AXI/actions/runs/44692959074)**, 검증된 소스 `666da599e0af1ef866c9d29bec073a1462ca5756`, L0 **30/30 PASS**, L2 **실제 Gazebo 성공**.
- ROBOTIS Waffle Pi 등록 RGB-D `update_rate=2` / 기존 GPU LiDAR `update_rate=10` 확인: `S5_PERF_RGBD2_OVERLAY_WITH_OFFICIAL_LIDAR_10HZ_PASS`.
- 실제 pseudo-TTY 승인 12.02초 지연→신규 Scan age 0.000초 / Odom age 0.011초.
- NORMAL TABLE_3 Nav2 Action SUCCEEDED, 물리 Odom **5.115m**, AMCL 오차 0.220m.
- SOUP PICKUP_RETURN SUCCEEDED, 물리 Odom **5.072m**, AMCL 오차 0.090m.
- 실제 Odom 속도 p75 **0.23/0.11m/s**, 물리 LiDAR STOP 폴리곤 29점, 공식 CollisionMonitorState.STOP·cmd_vel 0·물리 Odom 정지 **PASS**.
- `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS`, `S5_OWNER_DELAYED_TTY_REAL_GAZEBO_L2_PASS`, `S5_PERF_RGBD2_REAL_GAZEBO_FUNCTIONAL_L2_PASS_NOT_GPU_RTF`.
- Compact artifact [#14609536772](https://github.com/silverbjin/samsung_AXI/actions/runs/44692959074/artifacts/14609536772), 7,046 bytes, SHA256 `aae8bf7cbfe483102285a5b5312d40d5c5cd3d69ace7d04e837268509ef736a1`.

## 5. 인수 경계 및 다음 단계

- `S5_PERF01_CODE_AND_CI_L2=PASS`: 프로파일러·S5 전용 2Hz 후보의 소스/실제 Gazebo 기능 호환 검증은 완료.
- `S5_LIVE_FUNCTION_L3=ACCEPTED`: 이미 성공한 강사 GUI 배달·복귀·안전정지 기준선 보존.
- `S5_PERF01_WSLG_RT_F_90_PERCENT=NOT_VERIFIED`: 실제 NVIDIA D3D12 GUI에서 5Hz baseline/2Hz 후보의 동일 경로를 각각 실행해야 한다. 기존 84.39%를 후보 2Hz 성공이라고 승격 금지.
- 비교: 전체 실 RTF 표본 ≥50개 + NORMAL/SOUP 이동 구간 ≥25개 및 **두 중앙값 모두 ≥0.90**. 동일 PC/GUI/지도/주행 상태를 비교하고 기능/안전 PASS를 유지. rgbd2가 개선을 확인하지 못하면 baseline 유지.
- 성능 원인이 실제 RGB-D가 아닌 경우 `s5_perf_timeline.csv`의 단계별 RTF·CPU/GPU 값을 바탕으로 **최초로 확인된 병목만** 검토. 임의의 물리 step, Nav2 속도, Collision Monitor 또는 LiDAR 주기를 바꾸지 않음.
- 강사 실행 및 증거 ZIP: [S5-PERF-01 Owner A/B 가이드](../../S5_PERF_01_OWNER_AB_GUIDE_KO.md). 성능 WSL2 인수 완료 전까지 `S5_FULL_PERFORMANCE_AND_OPERATIONS_ACCEPTANCE=HOLD`.
