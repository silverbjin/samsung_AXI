# S5-LIVE-01 — 강사 Gazebo·RViz 메뉴 배달·복귀 및 안전 STOP 라이브

## 범위
- 기존 실제 Gazebo S2-MAP-03 지도(81.33%), 공식 Nav2/AMCL, NORMAL/SOUP SpeedLimit 및 Collision Monitor를 재사용합니다.
- **동일한 Gazebo 세션**에서 픽업 → 테이블3(**NORMAL 0.23m/s**) → 픽업(**SOUP 0.11m/s**)을 실제 주행하고, 실제 물리 원통 fixture로 LiDAR Scan→CM STOP→최종 /cmd_vel 0→물리 /odom 정지를 검증합니다.
- 기존 `ci_s3_amcl_smoke.py --s5-integrated` 실증 경로 재사용. 새 Planner/SLAM/Supervisor/모터제어/YOLO 없음.
- 정지 시험에서는 **기존 S4 계약과 동일하게** Collision Monitor 상류 `/cmd_vel_smoothed`에 제한된 0.08m/s 시험 입력을 넣고, 최종 하류 `/cmd_vel`은 반드시 0이어야 합니다. 해당 테스트 직후 시험 입력은 0으로 복귀합니다.

## 강사 WSL2 GitHub 고정 SHA 원샷

**주의:** `PIN`은 S5 통합 공개 CI L0/L2 GREEN이 확인된 40자리 SHA여야 합니다. 인수 전에는 Goal 실행을 승인하지 마십시오.

```bash
(
  set -Eeuo pipefail
  PIN="c59dd030b2f70351b06eae39e3b3bfeb7ed4b128"
  SCRIPT="$(mktemp --suffix=.sh)"
  trap 'rm -f "$SCRIPT"' EXIT
  curl -fL --retry 3 --connect-timeout 10 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/samsungaxi_wsl2_gui_acceptance_once.sh" -o "$SCRIPT"
  bash -n "$SCRIPT"
  SAMSUNG_AXI_GUI_PIN="$PIN" bash "$SCRIPT" --self-test
  # ROS/Goal 없이 실제 원샷→Owner→Core Shell 경로 사전검사
  SAMSUNG_AXI_GUI_PIN="$PIN" bash "$SCRIPT" --s5-live --preflight-only
  # 위에서 S5_OWNER_PREFLIGHT_PASS_NO_GOAL 확인 후에만 현장 라이브 시작
  SAMSUNG_AXI_GUI_PIN="$PIN" bash "$SCRIPT" --s5-live --approve-goals
)
```

최초 CLI 승인 후에도 Goal은 전송되지 않습니다. Gazebo 화면에서 테이블 주변 안전 경로와 RViz Map·Robot TF·Navigation ACTIVE를 확인한 뒤, 실행 터미널의 질문에 정확히 **`YES-S5-LIVE-GOALS`**를 입력해야 합니다. 승인하지 않으면 NO_GOAL로 차단됩니다.

성공 후에도 Gazebo·RViz GUI를 유지합니다. 화면 확인 후 **Ctrl+C**로 종료하면 `~/samsungaxi_gui_evidence/`에 진단 ZIP 한 개를 보존합니다.

## 근거 및 판정

- `S3_NAV02_GOAL_SUCCEEDED=TABLE_3` 및 `PICKUP_RETURN`: 실제 Nav2 NavigateToPose Action Result와 물리 Odom 최소 이동거리, AMCL 도착 오차 검증.
- `S4_MENU_NORMAL_SOUP_REAL_ODOM_SPEED_PASS`: 각각 실제 Odom p75, 유효 샘플 수와 속도 차이.
- `S4_PHYSICAL_FIXTURE_LIDAR_POINTS` 및 `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS`: 물리 Gazebo fixture + 실제 LiDAR + Collision Monitor STOP + 필터 결과/물리 정지.
- `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS`: **동일 세션에서 모든 증거가 성공한 경우에만** 발행.
- JSON은 `generated/s5/<UTC-run-id>/s5_live_evidence.json`, 현장 ZIP에는 로그·RTF·GPU·ROS 정보·S5 JSON이 포함됩니다.

### 실패 시

`SAMSUNGAXI_DIAGNOSTIC_ZIP=...` 경로의 ZIP 한 파일을 첨부하십시오. `Ctrl+C`는 Goal 송신기의 ROS/Gazebo 자식 프로세스 그룹에 신호를 보내 정상 종료합니다. 강사 WSL2에서 실제 라이브 이동·정지·GUI 인수를 확인하기 전에는 `S5_LIVE_L3=NOT_RUN`입니다.

## 확정 CI 출고 증거 (현장 L3와 구분)

- [최종 통합 공개 CI #44673556772](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772), 검증 SHA `d0738c56716390c52710767e7a3ac7b42d1966b5`, L0/L1/L2 GREEN.
- 실 Gazebo TABLE_3 NORMAL Odom **5.194m**, AMCL 오차 0.138m; PICKUP_RETURN SOUP Odom **5.021m**, AMCL 오차 0.267m. 실제 Odom p75 NORMAL 0.23m/s, SOUP 0.11m/s.
- S4 기존 물리 원통과 실제 LiDAR 전방 29점, CM STOP 구역 29점, 공식 STOP 상태→/cmd_vel 필터 0→물리 /odom 정지 PASS.
- [Compact Artifact #14601770464](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772/artifacts/14601770464) (ZIP 4,718 bytes, SHA256 `b3fdf4eacd0e13eafd0660239e8f817e428fb89c710f7e4cf39027cdd4b868d7`).
- 새 경로의 소스는 L2에서 확인되었으나 **강사 WSL2의 실제 GUI 라이브 Goal은 NOT_RUN**입니다. ZIP에 기존 실행의 JSON이 혼입되지 않도록 S5 원샷은 UTC-run-id별 별도 증거 디렉터리를 사용합니다.

## 2026-11-20 출고 오류 근본 원인과 현장 Preflight

- 이전 SHA `d0738c56...`는 RUN_ID 뒤에 PID를 붙이는 `$$`가 단일 `$`로 저장돼 WSL2에서 `S5_BLOCKED_INVALID_RUN_ID` 발생.
- 새 SHA `340527bf81c3ad23fdef0279fbaf07314d242a0b`: 공통 `scripts/s5_run_id_contract.sh` 사용, 기존 정규식 유지, 실제 ROS 실행 전 RUN_ID 생성·검증.
- `--s5-live --preflight-only`: GitHub SHA에 고정된 공통 계약/Owner/Core를 동일 경로로 실행, **ROS·Gazebo·Goal을 시작하지 않고 종료**. 최초 실패/성공 모두 ZIP 1개로 기록.
- 기대 성공 문자열: `S5_RUN_ID_CONTRACT_PASS`, `S5_OWNER_CORE_PREFLIGHT_PASS_NO_GOAL`, `S5_OWNER_PREFLIGHT_PASS_NO_GOAL`. 실패 시 `S5_BLOCKED_...`, `FIRST_FAILED_PHASE`, `FIRST_FAILED_MARKER`, `GOAL_SENT=FALSE`를 ZIP의 `status.txt`에서 확인.
- 실제 Goal 실행은 별도 CLI `--approve-goals`와 대화형 터미널 `YES-S5-LIVE-GOALS`가 **모두 필요**하며, 무인 CI preflight는 Goal 송신을 승인하지 않습니다.
- [공개 최종 Owner L0 #44681029156](https://github.com/silverbjin/samsung_AXI/actions/runs/44681029156): 실제 Shell 회귀 21/21 PASS.
- [기존 S5 실제 Gazebo 통합 L2 #44673556772](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772): 독립 원본 증거로 보존, 이번 수정에서 주행 코드 변경 없음.
- 강사 WSL2 실제 라이브 L3는 재실행 전까지 `NOT_RUN`; 새 Preflight GREEN을 L3 GOAL PASS로 해석하지 마십시오.

## 2026-11-20 S5 Owner TTY 승인 지연·센서 신선도 수정 출고

- 기존 현장 원본 `samsungaxi_gui_20261120T053905Z-4185.zip`에서 `S5_OWNER_GOALS_AUTHORIZED` 직후 `NAV_PREGOAL_SENSOR_STALE_TABLE_3`로 종료, 최초 Goal은 발행하지 않음(`goal_sent=false`). Preflight ZIP은 PASS.
- 원인: 단일 ROS Executor의 `input()` 블로킹으로 승인 대기 중 /scan·/odom 콜백 처리가 중단됨.
- 수정: 기존 승인 문자열·2단계 승인을 보존하고 `select.select` 기반 비차단 TTY 폴링 중에 실제 `rclpy.spin_once`를 계속 호출. 승인 후 신규 /scan과 /odom을 모두 관찰한 경우에만 Goal 허용. **기존 8초 센서 신선도 기준은 완화하지 않음**.
- 사용자 승인 대기·센서 정체 시 NO_GOAL 차단을 유지. 승인 시간, 신규 센서 수, Scan/Odom age를 `s5_owner_approval` 증거 JSON과 터미널에 기록.
- [공개 RED #44685116880](https://github.com/silverbjin/samsung_AXI/actions/runs/44685116880): `input()` 정체 회귀 예상 실패.
- **[공개 최종 GREEN #44686196254](https://github.com/silverbjin/samsung_AXI/actions/runs/44686196254), 검증 SHA `c59dd030b2f70351b06eae39e3b3bfeb7ed4b128`:** 기존 L0 + 실제 Gazebo L2 성공. 12.026초 지연 후 pseudo-TTY로 YES 입력, 승인 후 Scan age 0.004초 / Odom age 0.000초, 실제 NORMAL Odom 5.109m, SOUP 4.985m, p75 0.23/0.11m/s, 물리 Collision Monitor STOP PASS.
- [Compact Artifact #14606188931](https://github.com/silverbjin/samsung_AXI/actions/runs/44686196254/artifacts/14606188931), 4,768 bytes, SHA256 `5fdc9dd07a974e11adb31de5fc26fbed04de856d2055bd995dd16744c3cf583c`.
- 현장 실행 전에는 이전 ROS/GUI 세션을 종료하고, **위 PIN이 포함된 원샷을 GitHub RAW에서 다운로드**하여 `bash -n` → `--self-test` → `--s5-live --preflight-only` → `--s5-live --approve-goals` 순으로 진행합니다. Gazebo/RViz에서 경로 확인 후 실제 TTY에서 `YES-S5-LIVE-GOALS`를 입력합니다. 입력까지 8초 이상 기다려도 콜백은 계속 처리되어야 합니다.
- 성공 시 예상: `S5_OWNER_GOALS_AUTHORIZED WAIT_SEC=...`, `S5_OWNER_FRESH_SCAN_ODOM_AFTER_APPROVAL_PASS`, `S3_NAV02_GOAL_SUCCEEDED=TABLE_3`, `S3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN`, `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS`, `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS`.
- Ctrl+C로 GUI를 종료하면 `SAMSUNGAXI_DIAGNOSTIC_ZIP=...` 경로에 진단 ZIP **한 파일**을 생성합니다. 오류 시 해당 ZIP만 전달하십시오. **실제 강사 WSL2 라이브 L3는 NOT_RUN**이며, CI에서 Windows GPU/WSLg 최종 성능을 주장하지 않습니다.

## 2026-11-20 강사 WSL2 라이브 기능 L3 최종 인수

- 현장 실제 S5 증거 ZIP: `samsungaxi_gui_20261120T062446Z-5175.zip` (SHA256 `ae9079c0e921a4b64e78fbf15cd50b1628a93c06ef6d6ecdda10ade3aa66761d`), 별도 NO_GOAL Preflight ZIP `samsungaxi_gui_20261120T062445Z-5135.zip` (SHA256 `65c9e647944c477e1931d5b2431682c998964c53476b54dfe7841cc1d65e6051`).
- 실제 강사 TTY 승인 24.149초 후 새 Scan/Odom 확인 PASS, NORMAL TABLE_3 Action SUCCEEDED (5.144m), SOUP PICKUP_RETURN Action SUCCEEDED (5.074m), Odom p75 0.23/0.11m/s, LiDAR/Collision Monitor STOP (29점), 하류 /cmd_vel 0, Odom 이동량 0m.
- 최종 기능 판정: `S5_LIVE_FUNCTION_L3=ACCEPTED`.
- 성능 예외: 주행 중 RTF **중앙값 84.39%**, 100개 중 44개가 90% 이상; 90% 중앙값 목표 **HOLD**. CPU/GPU 부하·Gazebo 물리/센서·Nav2 부하를 우선 좁혀 검증할 것.
- 종료 예외: 의도된 Ctrl+C `RUN_RC=130` 이후 ROS context invalid 관련 경고가 남아 `SHUTDOWN_CLEAN=HOLD` 유지.
- root `goal_sent=true`는 실제 2개 Action 성공과 일치. `s5_owner_approval.goal_sent=false`는 승인 직후 **사전송신 스냅샷**이며 최종 Goal 상태가 아님.
- 인수 보고서: [S5-LIVE-01 WSL2 현장 기능 인수](reports/tasks/2026-11-20_S5-LIVE-01_OWNER_WSL2_L3_FINAL_ACCEPTANCE_KO.md). 현재 원샷은 검증 및 인수 완료된 소스 `c59dd030b2f70351b06eae39e3b3bfeb7ed4b128`를 계속 사용하며, 과도한 기능 확대는 금지합니다.
