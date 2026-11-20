# S5-PERF-01 — WSL2 실주행 Goal ABORT 최초 실패, CI 경계 보완 및 재배포

## 1. 현장 제출 원본(비공개 보존)

- 대상 저장소: `silverbjin/samsung_AXI`; 기준 main `4b4bbf614e75ec43f733ecec065b51a540fc07b7`.
- 이전 배포 실행 SHA: `666da599e0af1ef866c9d29bec073a1462ca5756`.
- Preflight: `samsungaxi_gui_20261120T073154Z-7950.zip`, SHA256 `040eb66d20dfc6a691b43b4bf5b81e6465d98ce2492fc9694fce97ff0210df71`, `RUN_RC=0`, `VERDICT=PREFLIGHT_PASS_NO_GOAL`.
- 실패: `samsungaxi_gui_20261120T073155Z-7990.zip`, SHA256 `12a812161def5003138ea332d4965c98a47d86ee2683b9376be3da5578f73f66`, `RUN_RC=1`, `VERDICT=HOLD`, `S5_PERF_MODE=baseline`.
- 지도 원본 SHA/연결성, 수동 Pose 없는 AMCL, Nav2 Lifecycle ACTIVE, TTY 19.463초 뒤 승인, 승인 후 신규 Scan/Odom PASS.
- 정상 속도 한도 `S4_NAV2_ABSOLUTE_SPEED_LIMIT=NORMAL MPS=0.23` 및 `S3_NAV02_REAL_GOAL_ACCEPTED=TABLE_3` 후 **`NAV_GOAL_NOT_SUCCEEDED_TABLE_3:6`**. ROS 2 Action status 6은 **ABORTED**, 실제 Goal 수락 뒤 Nav2가 정상 종료하지 못했음을 뜻함. S5 정상 왕복/STOP은 **이 세션에서는 미검증**.
- `ci-s3-summary.txt`는 주로 Lifecycle/종료 시점 메시지와 `bt_navigator: Goal failed`만 보존해 구체적 Planner/Controller 실패 사유를 잃음. `s5_live_evidence.json` root `goal_sent=false`는 실패 당시 잘못된 **과거 pregoal 스냅샷**이므로 이번 Goal 미전송이라는 해석은 금지. `status.txt`의 `GOAL_SENT=TRUE` 및 수락 로그가 정확.
- 같은 ZIP의 `owner_tails.txt`에는 45분 내 다른 실행의 `PICKUP_RETURN:6`도 혼합돼 있어 **현재 실행의 최초 실패와 혼동 금지**.
- RTF: `s5_perf_summary.json` startup median 0.9980/24개, NORMAL 이동 median **0.6403/26개**, 전체 median 0.9737/50개. RTF 하락과 Nav2 ABORT는 **동시 관찰**; 인과관계와 Nav2 하부 오류 코드는 기존 ZIP으로 확정 불가.
- GPU probe: NVIDIA RTX 3060 D3D12 accelerated, 기본 `glxinfo` llvmpipe는 강제 프로브 전 값. WSL2 가용 RAM은 넉넉했으며 메모리 부족의 직접 근거 없음.
- 원본 ZIP은 사용자 시스템 경로가 포함되어 공개 GitHub에는 업로드하지 않고 SHA256·확정 사실만 기록.

## 2. 기존 CI 누락 원인 및 RED→GREEN

- 이전 [S5-PERF CI #44692959074](https://github.com/silverbjin/samsung_AXI/actions/runs/44692959074)는 RGB-D 2Hz, 실제 Gazebo Nav2·CM STOP은 검증했지만 **동시 RTF 기록기를 실행하지 않았고, baseline 5Hz 프로파일러 부하를 검증하지 않음**.
- 추가 회귀 `tests/test_s5_perf_field_abort.py`: ABORT status 6에서 action error_code/error_msg, 최종 Goal 송신 여부, 피드백·이동량·센서 freshness를 기록하는 계약과 실 프로파일러 동시 실행 L2 계약.
- RED [#44696814433](https://github.com/silverbjin/samsung_AXI/actions/runs/44696814433): `s5_nav_abort_evidence` 모듈 없음. 이어 [#44696927504](https://github.com/silverbjin/samsung_AXI/actions/runs/44696927504): 오류 근거 함수의 실제 호출 누락. 수정 전 원인을 재현.
- 최소 수정: `scripts/s5_nav_abort_evidence.py`와 `ci_s3_amcl_smoke.py` 연결. 승인이나 Nav2 안전 조건 변경 없이 Action 결과/진행/물리 증거를 **예외 발생 전** 저장하고, 이미 성공한 첫 Goal도 즉시 저장. 임의 자동 재시도·성공 승격 없음.
- 해당 세션 `ci-s3-summary.txt`에 `NAV2_ACTIVE_GOAL_ERRORS_AND_CONTEXT_LAST_120` 소형 집중 로그 추가. `samsungaxi_wsl2_gui_acceptance_once.sh`의 실패 분류 `NAV2_ACTIVE_GOAL`, 현재 실행 로그만 ZIP에 넣음.
- `scripts/s5_perf_profile.py`의 기본 `ps`/ `nvidia-smi` 주기적 프로세스 생성을 중단하여 측정 자체가 주행을 교란할 위험을 줄임. 독립적인 `--resource-probes` 옵션만 별도 유지. 해당 변경의 실제 WSL2 효과는 미측정으로 분리.
- 신규 `.github/workflows/restaurant-s5-perf-field-parity-ci.yml`: 실제 Gazebo GUI Xvfb + baseline 5Hz + **실제 profiler 동시 실행** + 실제 12초 승인 + 두 Nav2 Action + LiDAR/CM STOP + RTF CSV/JSON.

## 3. 최종 공개 CI GREEN 및 근거

- **[Run #44697440947](https://github.com/silverbjin/samsung_AXI/actions/runs/44697440947), 검증 소스 `e72d2d04561494becac8ba597105bc9afc793b67`, L0 34/34 PASS, 실제 Gazebo L2 PASS**.
- ROBOTIS Waffle Pi RGB-D 5Hz, GPU LiDAR 10Hz PASS.
- 지연 TTY 승인 12.015초 후 신규 Scan/Odom PASS.
- NORMAL TABLE_3 `SUCCEEDED`, 물리 Odom **5.153m**, AMCL 도착 오차 0.212m.
- SOUP PICKUP_RETURN `SUCCEEDED`, 물리 Odom **5.097m**, AMCL 도착 오차 0.085m.
- 실제 속도 p75 NORMAL 0.23m/s / SOUP 0.11m/s, 물리 원통 LiDAR STOP 구역 29점, 공식 Collision Monitor STOP 및 필터/물리 정지 PASS.
- **실제 성능 기록기를 활성화한 동일 세션**에서 `S5_PERF_BASELINE_RTF_SAMPLE_PRESENCE_PASS`, `S5_PERF_PROFILED_BASELINE_REAL_GAZEBO_L2_PASS`, `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS` 모두 발생.
- [Compact Artifact #14611542017](https://github.com/silverbjin/samsung_AXI/actions/runs/44697440947/artifacts/14611542017), 12,310 bytes, SHA256 `32e8077a2ddcc484ff531abddc5e9b34b1d547b8bac147024f2de73aa5879863`.
- **주의**: GitHub-hosted runner의 Xvfb/llvmpipe는 강사 WSL2/WSLg D3D12 GPU 성능을 대체하지 않음. 이번 L2 GREEN은 동시 프로파일러·Nav2 통합 계약의 PASS이며 **강사 현장 ABORT 완전 해결이나 RTF ≥90% 인수의 증명은 아님**.

## 4. 출고 경계 및 현장 재검

- 기능 기준선 `S5_LIVE_FUNCTION_L3=ACCEPTED`는 이전 실제 성공에서 보존. 2026-11-20 16:32의 **신규 PERF 현장 A/B 시도는 실패(HOLD)**로 별도 관리.
- 재배포 SHA: `e72d2d04561494becac8ba597105bc9afc793b67`. [S5-PERF-01 원샷 가이드](../../S5_PERF_01_OWNER_AB_GUIDE_KO.md): `bash -n` → `--self-test` → `--s5-live --preflight-only` → 기본 5Hz의 `--s5-live --approve-goals --perf-baseline` 우선 단 1회.
- Goal 허가 문자열은 `YES-S5-LIVE-GOALS`. 실패하면 **새 ZIP 한 개만 업로드**하여 `nav2_goal_failure.error_code/error_msg` 및 원인별 Nav2 Context를 확인. 안전 조건이나 Nav2 progress checker를 임의 완화하지 않음.
- 재검 5Hz 성공 후에만 RGB-D 2Hz 후보를 동일 절차로 검사. 주행 중 RTF 90% 기준, 정상 종료 안정성은 별도 HOLD.
- 미해결: `S5_PERF01_WSLG_RTF_90_PERCENT=HOLD`, `S5_SHUTDOWN_CLEAN=HOLD`; 이번 실제 현장 Nav2 ABORT는 새 SHA WSL2 인수까지 `NOT_REVERIFIED`.

## 5. 정량적 후속 목표

1. 실패 시 `NAV2_ACTION_ABORT`의 원인 코드와 현재 세션 ROS 서버 메시지 확인.
2. 동일 주행에서 **전체 RTF median >=0.9 및 이동 중 median >=0.9**, 표본 수 기준 충족.
3. S5 원래 Nav2 배달·복귀·CM STOP 모두 PASS 유지.
4. 실제 WSL2에서 정상 완료 이전에는 `S5_PERF01_FIELD_ACCEPTED` 승격 금지.
