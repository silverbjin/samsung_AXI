# SmartDish S5-LIVE-01 — 강사 WSL2/WSLg 실제 라이브 L3 최종 기능 인수 보고서

- 인수일: **2026-11-20 KST**.
- 인수 범위: **레스토랑 자율주행 라이브 기능 L3 (수동 TTY 승인 → NORMAL 배달 → SOUP 복귀 → 실제 Collision Monitor STOP)**.
- 최종 기능 판정: **`S5_LIVE_FUNCTION_L3=ACCEPTED`**.
- 전체 성능/운영 무조건 완료 아님: **`S5_LIVE_RTF_MEDIAN_GE_90_PERCENT=HOLD`**, **`S5_SHUTDOWN_CLEAN=HOLD`**. 이 두 항목은 아래 후속 과제로 분리.
- 실제 실행 코드 SHA: `c59dd030b2f70351b06eae39e3b3bfeb7ed4b128`. 공개 CI [#44686196254](https://github.com/silverbjin/samsung_AXI/actions/runs/44686196254)에서 12초 지연 승인 실 Gazebo L2 PASS, [PR #20](https://github.com/silverbjin/samsung_AXI/pull/20)으로 main 병합.
- 제출 ZIP 원본은 강사 시스템 정보가 있으므로 **공개 GitHub에는 업로드하지 않음**. 검증된 SHA256과 요약치만 보고서에 기록.

## 원본 증거 및 무결성

| 증거 | 파일명 | SHA256 | 결과 |
|---|---|---|---|
| NO_GOAL Preflight | `samsungaxi_gui_20261120T062445Z-5135.zip` | `65c9e647944c477e1931d5b2431682c998964c53476b54dfe7841cc1d65e6051` | `RUN_RC=0`, `VERDICT=PREFLIGHT_PASS_NO_GOAL`; `GOAL_SENT=FALSE` |
| 실제 S5 라이브 | `samsungaxi_gui_20261120T062446Z-5175.zip` | `ae9079c0e921a4b64e78fbf15cd50b1628a93c06ef6d6ecdda10ade3aa66761d` | 라이브 전체 성공 표식 확인; `RUN_RC=130`는 종료 `Ctrl+C` |

Preflight: `S5_RUN_ID_CONTRACT_PASS`, `S5_OWNER_CORE_PREFLIGHT_PASS_NO_GOAL`, `S5_OWNER_PREFLIGHT_PASS_NO_GOAL` 모두 존재. 실제 세션은 `FIRST_FAILED_PHASE=NONE`, `FIRST_FAILED_MARKER=NONE`, `GOAL_AUTHORIZED=TRUE`, `GOAL_SENT=TRUE`. RUN_ID `20261120T062446Z-5175`.

## 실제 현장 S5 통합 기능 증거

| 항목 | 라이브 현장 측정/로그 | 판정 |
|---|---|---|
| 공개 소스 SHA | `c59dd030b2f70351b06eae39e3b3bfeb7ed4b128` | PASS |
| 개선 S2-MAP-03 지도 | `maps/candidates/s2_map03/restaurant_map.yaml`, 202×185셀, PGM SHA256 `aedaed8f89e703f33ef22f9cf0c9d8f77b11763157d6e3a61c839a58fe871f00`; 원본 Free 연결성 검증 | PASS |
| 수동 Pose Estimate 없는 AMCL | `S3_AMCL_AUTO_INITIAL_POSE_REAL_GAZEBO_PASS_NO_MANUAL_PUBLISH`, 지도 TF·Nav2 Lifecycle ACTIVE | PASS |
| 강사 TTY 실제 지연 승인 | `S5_OWNER_GOALS_AUTHORIZED WAIT_SEC=24.149` | PASS |
| 승인 후 신규 Scan/Odom | `S5_OWNER_FRESH_SCAN_ODOM_AFTER_APPROVAL_PASS`, Scan age 0.004초, Odom age 0.0초, 두 메시지 수신 수 각각 +1 | PASS |
| NORMAL 테이블 3 배달 | `S3_NAV02_GOAL_SUCCEEDED=TABLE_3`, Action status 4 (SUCCEEDED), 실제 Odom 거리 5.144m, AMCL 도착 오차 0.209m | PASS |
| SOUP 픽업 복귀 | `S3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN`, status 4, Odom 거리 5.074m, AMCL 오차 0.133m | PASS |
| 메뉴별 속도 | Odom p75 NORMAL 0.23m/s / SOUP 0.11m/s, 1,172 / 2,812 표본, p75 차 0.12m/s | PASS |
| 실제 LiDAR 장애물 | 물리 Gazebo 원통, 실제 Scan STOP 폴리곤 29점 | PASS |
| Collision Monitor | `cm_state=STOP`, `upstream_positive_command_seen=true`, 필터 하류 `cmd_vel` 최대 절댓값 0.0m/s, 실제 Odom 이동량 0.0m | PASS |
| 통합 현장 결과 | `RESTAURANT_S3_NAV02_REAL_GAZEBO_DELIVERY_RETURN_PASS`, `RESTAURANT_S4_MENU01_REAL_GAZEBO_PASS`, `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS`가 동일 세션에 기록 | **ACCEPTED** |
| 현장 GPU | `D3D12 (NVIDIA GeForce RTX 3060)`, `Accelerated: yes` | PASS |

구조상 STOP은 실제 배달 완료 후 **별도 물리 장애물 정지 검증**이며, 주행 중 실시간 사람 회피 또는 경로 재계획 검증으로 확대 해석하지 않음.

## 미해결·비차단 항목 (후속 작업으로 분리)

### P1 — 이동 중 RTF 목표 미달

- 원본 `rtf_report.txt`: `RTF_SAMPLE_COUNT=100`, `RTF_MEDIAN=0.8439`, `RTF_P10=0.4030`, `RTF_AT_LEAST_90PCT=FALSE`.
- `rtf_samples.txt` 100개를 독립 집계: 평균 약 78.55%, **90% 이상 44/100개**, 최솟값 약 17.63%; 단발성 프레임 드롭과 구분한 원인 추적이 필요.
- 이전 **NO_GOAL GUI** 세션의 RTF 중앙값 99.92%와 조건이 다르므로, 직접 비교만으로 GPU/WSLg·Nav2·센서 중 어떤 것이 원인인지 단정 금지.
- **판정:** S5 기능 L3 인수는 승인하되, 별도 목표인 **동일 라이브 시나리오 RTF 중앙값 ≥90%**는 미달로 HOLD. 현재 성능을 90% 달성으로 서술하면 안 됨.

### P2 — Ctrl+C 후 종료 경고

- `RUN_RC=130`, `SHELL_RC=130`: 사용자의 Ctrl+C와 일치, 본 시연은 모든 주행·STOP 성공 메시지 발생 후 운영자가 종료.
- 단, `owner_tails.txt`에는 성공 이후 `RESTAURANT_S3_AMCL_L2_BLOCKED=failed to create timer: the given context is not valid ... rcl_shutdown() was called`가 남음.
- 이는 **시연 최초 실패가 아니지만** 종료 처리의 콜백·컨텍스트 순서 문제가 남아 있을 수 있음을 나타냄. `SHUTDOWN_CLEAN=PASS`로 승격하지 않음. 성공한 로봇 기능 증거 보존.

### P3 — Evidence JSON 필드 명확화

- 최종 root `goal_sent=true`, `real_nav_legs` 2개 status 4로 실제 Goal 송신 및 성공을 증명.
- 하위 `s5_owner_approval.goal_sent=false`는 **승인 직후 사전 Goal 상태의 스냅샷**이며 최종 상태를 나타내지 않음. 현장 승인 로그와 함께 보관하고, 후속 보고/진단에서는 해당 필드를 `goal_sent_at_approval` 등으로 명확히 구분할 필요. 과거 원본 JSON을 소급 수정하지 않음.
- 진단 `error_clues.txt`가 PASS 표식까지 포함하므로 오류/경고 분리 필터 개선은 우선순위 낮음.

## 후속 우선순위 및 완료 경계

1. **S5-PERF-01 (최소 범위):** 성공한 소스를 고정, 동일 라이브 주행에서 Gazebo stats RTF·CPU/GPU·실시간 센서 전송 빈도·Nav2 프로세스 부하를 동시 측정. 원인별 한 가지 최소 변경만 비교하고 현장 **중앙값 90% 이상** 목표 판단. 신규 알고리즘 금지.
2. **S5-SHUTDOWN-01 (최소 범위):** Ctrl+C 후 ROS context 사용 경계가 이미 shutdown된 시점과 겹치는지 최초 예외만 추적, graceful teardown 회귀 1회; 주행 기능 재개발 금지.
3. **S5-EVIDENCE-01 (선택적 소규모):** `goal_sent_at_approval`과 `goal_sent_final` 의미 정리, ZIP 내 성공/경고 구분. 기능 수정을 위한 새 게이트로 확대하지 않음.
4. **MVP 인수 패키징:** 본 L3 서명 증거, 이전 S2/S3/S4 CI 및 GUI L3, S5 원샷과 강사용 교육 가이드를 단일 상태표로 묶음. 위 성능/종료 항목을 완료했을 때만 **모든 성능·운영 인수**를 완료로 승격.

최종 상태:

```text
S5_LIVE_FUNCTION_L3=ACCEPTED
S5_LIVE_RTF_MEDIAN_GE_90_PERCENT=HOLD
S5_SHUTDOWN_CLEAN=HOLD
S5_FULL_PERFORMANCE_AND_OPERATIONS_ACCEPTANCE=HOLD
```
