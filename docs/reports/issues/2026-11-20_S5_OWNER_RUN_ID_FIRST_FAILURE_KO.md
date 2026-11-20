# S5-LIVE-01 — WSL2 RUN_ID 최초 실패 분석·RED→GREEN·Owner 출고 보고서

## 1. 원본·판정 범위

- Repo: `silverbjin/samsung_AXI`, 최초 main `a24a77b8c7ded14627742c9e1865f161c9167e20`.
- 성공했던 실제 Gazebo S5 Python 통합 L2: [#44673556772](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772), source `d0738c56716390c52710767e7a3ac7b42d1966b5`.
- 현장 실패: `samsungaxi_gui_20261120T044231Z-3756.zip`, SHA256 `be8193c2f096aeebe65d000c438ac3fd1bf51db953b473b6dbc8737de1685749`.
- 사용자 제공 ZIP `run.log`: 지도 SHA·Nav2 파라미터 확인 후 최초 `S5_BLOCKED_INVALID_RUN_ID`, `RUN_RC=2`, `VERDICT=HOLD`. 실제 Gazebo/Goal 실행 **이전**에 종료.
- 원본 ZIP은 강사 PC 정보가 있어 공개 저장소에 넣지 않음.

## 2. 최초 원인과 CI 검출 누락

- 출고 Shell `samsungaxi_wsl2_gui_acceptance_once.sh`: `SAMSUNGAXI_S5_RUN_ID="$STAMP-$"`.
- 출고 Shell `restaurant_demo.sh`: `...- $` 형태의 PID fallback (문자열 끝이 단일 `$`).
- 실제 PID 확장 `$$` 대신 `$`가 남아 기존 허용 문자 정규식 `^[A-Za-z0-9_-]+$`에서 거부.
- 기존 S5 CI L2는 `ci_s3_amcl_smoke.py`를 직접 실행하므로 배포된 Shell 체인의 RUN_ID 생성 구간을 지나지 않았음. 기존 정적 테스트는 `--self-test`/문자열만 검사.
- ZIP의 `error_clues.txt`가 비어 있던 이유는 기존 grep 규칙에 `BLOCKED`가 없었기 때문.

## 3. RED → GREEN

1. 신규 `tests/test_s5_owner_run_id_preflight.py` 작성. B01 자동 RUN_ID / B02 유효 외부 RUN_ID / B03 불법 문자열·최초 오류 ZIP / B04 Wrapper→Owner→Core / B05 이중 승인·TTY / B06 Core 단독 fallback.
2. 최초 공개 CI [#44679694021](https://github.com/silverbjin/samsung_AXI/actions/runs/44679694021)의 실패는 시스템 Python에 pytest가 없는 **CI 전제조건 오류**였으므로 RUN_ID RED 증거로 사용하지 않음. CI에 `python3-pytest` 최소 설치.
3. 실제 RED: [#44679907694](https://github.com/silverbjin/samsung_AXI/actions/runs/44679907694), 회귀 6개 실패. `--preflight-only` 미지원, 실행 체인 및 Compact ZIP 계약 누락 명확히 확인.
4. **최소 수정:** 공통 `scripts/s5_run_id_contract.sh`에서 `BASHPID` 기반 생성 및 **기존** 정규식 검증. 생산용 원샷은 같은 SHA에서 계약 셸을 다운로드, Core는 같은 SHA의 체크아웃에서 source. Owner가 `--preflight-only`로 Core 실제 경로를 통과하되 ROS/Goal은 실행하지 않음.
5. 진단 ZIP: `PUBLIC_SOURCE_SHA`, `OWNER_SOURCE_SHA`, `S5_RUN_ID`, `FIRST_FAILED_PHASE`, `FIRST_FAILED_MARKER`, `RUN_RC`, `GOAL_AUTHORIZED`, `GOAL_SENT`, `DIAGNOSTIC_ZIP`. `BLOCKED|S5_|RESTAURANT_OWNER_`를 오류 추출에 추가. 실행 ID 불법 문자열을 느슨하게 허용하지 않음.
6. GREEN: [#44680424493](https://github.com/silverbjin/samsung_AXI/actions/runs/44680424493) 신규 6개 PASS → [#44680643148](https://github.com/silverbjin/samsung_AXI/actions/runs/44680643148) 기존 S5 안전 계약 포함 20 PASS → **최종 [#44681029156](https://github.com/silverbjin/samsung_AXI/actions/runs/44681029156) 21/21 PASS**, 검증 소스 `340527bf81c3ad23fdef0279fbaf07314d242a0b`.

## 4. 기존 실증·안전 경계 보존

- 실제 Gazebo·Nav2 실행기 `scripts/ci_s3_amcl_smoke.py` **변경 없음**. 저장 지도, AMCL 초기 위치, NORMAL/SOUP 속도, CM STOP, 최종 `/cmd_vel` 및 물리 `/odom` 검증 계약 **변경 없음**.
- 이번 L0은 현장 배포 Shell의 생성/승인/진단 경계만 변경. ROS 물리 정책 및 Python 실행을 수정하지 않아 **불필요한 새 Gazebo L2를 반복하지 않음**. 기존 실제 L2 원본 [#44673556772](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772)과 [Artifact #14601770464](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772/artifacts/14601770464) 보존.
- 실제 Shell 실행기 유효성은 독립 `--preflight-only`로 검증: Goal 생성 없음, 비대화형 Goal 차단 유지, RUN_ID 동일성 확인, 잘못된 값은 실패 ZIP.
- 새로운 Python navigation, SLAM, Planner, Supervisor, YOLO, 모터 제어 없음.

## 5. 출고·Owner WSL2 L3

- 검증된 소스 SHA: `340527bf81c3ad23fdef0279fbaf07314d242a0b`. `docs/S5_LIVE_GUIDE_KO.md`에서 이 SHA의 GitHub Raw를 다운로드.
- `bash -n` → `--self-test` → **`--s5-live --preflight-only`** → 현장 수동 승인 후 `--s5-live --approve-goals`.
- Preflight 성공 표식: `S5_OWNER_RUN_ID_REGRESSION_PASS`(CI), `S5_OWNER_PREFLIGHT_PASS_NO_GOAL`, `S5_OWNER_DIAGNOSTIC_CONTRACT_PASS`(CI).
- 현장 GOAL 이중 승인/TTY 후 실제 Gazebo 주행 L3는 별도. CI 성공만으로 `S5_LIVE_L3=ACCEPTED`로 보고하지 않음.

```text
S5_OWNER_RUN_ID_REGRESSION_PASS
S5_OWNER_PREFLIGHT_PASS_NO_GOAL
S5_OWNER_RELEASE_READY=TRUE
S5_LIVE_L3=NOT_RUN
```
