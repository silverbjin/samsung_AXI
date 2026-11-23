# SmartDish — D 담당 UI·서비스 개발 인계서

- 작성일: 2026-11-23
- GitHub: https://github.com/silverbjin/samsung_AXI
- 브랜치: \`feat/smartdish-d-service\` (S7 main 2dd7f968dd3d24e2afb48e0917ef8c9d054ac894에서 분기)
- **Draft PR #38**: https://github.com/silverbjin/samsung_AXI/pull/38 (main 미병합)
- 최종 *기능 코드* 수정 SHA: \`b3e9bfdb80b96607faf5f5f121429370f36ec1d6\`
- 문서 보강 후 정확한 HEAD: Draft PR의 \`head_sha\`/ \`git rev-parse HEAD\`에서 확인 (자기 SHA를 자기 문서에 기록하지 않음)
- 기능 판정: **D-DBG-001 기준 L0 26 PASS (MOCK_ONLY) / ROS L1 PASS**, 이후 D-DBG-002 steady timer 보완은 최신 HEAD CI 재검 대상. REAL GAZEBO NOT_RUN

## 1. 소유 파일
\`\`\`text
src/smartdish_service/
  smartdish_service/mission_manager.py  # D01 ROS 독립 FSM
  smartdish_service/manager_node.py      # D02 7토픽 ROS 전송
  smartdish_service/ui_app.py            # D03 Tkinter GUI
  config/ui_layout.yaml                  # 화면상의 ui_pixels (map Pose 아님)
  launch/smartdish_service.launch.py
  setup.py, setup.cfg, package.xml, resource/...
tests/test_smartdish_d_service.py
tests/test_smartdish_d_ui.py
docs/integration/smartdish_d_contract_fixtures_v1.json
docs/integration/SMARTDISH_D_A_CONTRACT_ADOPTION_KO.md
docs/pm/SMARTDISH_D_WBS_RISK_20261123_KO.md
docs/reports/smartdish/d/ (개발·디버깅·검증 교육 보고서)
\`\`\`

A \`src/smartdish_robot\`, B dataset, C inference, S7 World/Nav2/CM 및 기존 tests는 변경하지 않았습니다.

## 2. 빠른 시작(WSL2 Jazzy)
**전제:** A의 Robot/Gazebo/Nav2/AMCL을 별도로 실행하고, A의 \`DISH_RETURN\` 유효 map Pose를 실제 검증해야 합니다. A 실행 상세는 \`docs/handoff/A_HANDOFF.md\` (A PR #36) 참조. **현재 null이라 3-leg 실주행 인수는 BLOCKED.**

\`\`\`bash
# E 통합 작업 트리(아직 main 병합 전이므로 개별 D 브랜치만 clone하면 A는 없음)
git clone -b feat/smartdish-d-service https://github.com/silverbjin/samsung_AXI.git
cd samsung_AXI
set +u
source /opt/ros/jazzy/setup.bash
python3 -m pytest -q tests/test_smartdish_d_service.py tests/test_smartdish_d_ui.py
colcon build --symlink-install --packages-select smartdish_service
source install/setup.bash
ros2 pkg executables smartdish_service
ros2 launch smartdish_service smartdish_service.launch.py ai_available:=false
\`\`\`

A 통합 후 실제 Goals 사용 시 다른 TTY에서 A Nav Adapter를 사용자가 직접 실행·승인합니다.
\`\`\`bash
ros2 run smartdish_robot navigation_adapter --ros-args \
  -p goals_enabled:=true -p set_initial_home:=false
# TTY 수동 승인: YES-SMARTDISH-A-GOALS
\`\`\`
기존 S7 \`scripts/restaurant_demo.sh navigation\`으로 Gazebo/Map/Nav2가 준비된 후에만 A를 시작합니다. \`set_initial_home:=false\`일 때는 AMCL 초기화가 별도로 정확해야 합니다.

## 3. ROS 실제 구독·발행 확인
\`\`\`bash
ros2 topic list -t | grep /collection/
ros2 topic info -v /collection/nav_goal
ros2 topic info -v /collection/nav_result
ros2 topic echo /collection/status std_msgs/msg/String
\`\`\`
\`VOLATILE\`이므로 A 구독 생성 전 D 요청은 전송하지 않습니다. D는 A 구독자가 0이면 \`ADAPTER_NOT_READY_NO_GOAL\`로 거절합니다. UI도 Manager 구독이 없으면 요청하지 않습니다.

## 4. 단위 검증과 실제 인수의 경계
| 단계 | 기대 근거 | 현재 |
|---|---|---|
| D Python L0 | 3-leg 합성 결과·10/5초·BUSY·실패·AI 분기 | PASS (MOCK_ONLY) |
| D ROS L1 | Jazzy ament build·console_scripts·import | [#45121672872](https://github.com/silverbjin/samsung_AXI/actions/runs/45121672872) PASS |
| D Tk GUI 시각 | T03 클릭·상태·색상·버튼 | 실제 WSLg NOT_RUN (시각은 사용자 검수) |
| A+D AI OFF 실제 | 3개의 A SUCCEEDED + /odom + UI COMPLETED/동일 ID | **BLOCKED / NOT_RUN** |
| A+C+D AI ON | tray RGB 실제 프레임 + C 결과 + D 직원 승인 | OPTIONAL / NOT_RUN |

## 5. E 통합에서 반드시 확보할 기록
1. E 통합 HEAD SHA, A/D 각 Draft PR 및 파일 버전.
2. 실제 A 시작 로그 \`SMARTDISH_A_READY\`, TTY 승인 및 subscriber 수.
3. UI \`/collection/request\` 원문 JSON 1개와 \`request_id\`.
4. \`TO_TABLE\`, \`TO_RETURN\`, \`TO_HOME\` 3개 A \`SUCCEEDED\` + 실제 odom 구간 근거.
5. \`WAIT_LOADING\` 10초, \`WAIT_UNLOADING\` 5초의 단조시간 경과 및 \`/collection/status\`.
6. UI 최종 \`COMPLETED\`, 사용자 시각 검수(자동 게이트 아님).
7. 최초 실패가 있으면 \`D-DBG-NNN\` 형태로 첫 오류·원인·수정·재검증을 별도 기록.

### 공개 CI 재검증 증거
- D03 기준 [#45121462007](https://github.com/silverbjin/samsung_AXI/actions/runs/45121462007): Python 24 PASS / ROS Jazzy L1 PASS.
- D-DBG-001 기준 [#45121672872](https://github.com/silverbjin/samsung_AXI/actions/runs/45121672872): Python **26 PASS** / ROS Jazzy L1 PASS.
- 최신 Draft PR 소스 SHA의 전체 CI 판정은 PR Checks에서 별도 확인합니다. 기능 변경 마지막 SHA는 `b3e9bfdb`이고 이후 문서 추가만 발생했습니다.

### 타이머 시계 고정
`D-DBG-002`에서 `ClockType.STEADY_TIME`으로 ROS timer scheduling을 고정하고 FSM deadline의 `time.monotonic()`과 일치시켰습니다. 최신 GitHub CI에서는 Python 정적 회귀와 ROS Jazzy의 실제 create_timer API 호출을 확인해야 합니다.

## 6. 현재 차단 사항과 다음 액션
- **최우선:** A가 \`DISH_RETURN\` 실제 map Pose/통로 도달성을 확정할 것.
- 그다음: E 브랜치에서 A와 D를 결합해 AI OFF 실주행 1회. D 단독 성공을 E 실제 인수로 승격하지 않음.
- C 미준비면 AI 옵션은 OFF. D의 \`--ai-available true\`는 실제 C 준비 후만 사용.
- 12/07 기능 동결, 12/08 리허설, 12/09 발표. 범위가 넘치면 UI 장식/AI 추가 기능부터 중단.

## 7. 개발 문서만으로 되짚기
\`docs/reports/smartdish/d/README.md\` → D01 → D02 → D03 → D-DBG-001 → D-DBG-002 → D04 검증 → 이 인계서 순서로 읽습니다. 원격 Actions URL과 커밋 SHA를 함께 비교하면 수정 이유와 검증 범위를 추적할 수 있습니다.

## D05 — 재실행 안전성 개선 인계 (2026-11-23)

- D05 코드 SHA: `ffa8cc8ee0750ed540534566a8c4176e6376c049` (최초 L0 작업 이전)
- 최신 CI/가이드: `docs/reports/smartdish/d/D05_WSL2_FAIL_FAST_RUNNER_EDU_KO.md`, `docs/handoff/D_WSL2_ONE_SHOT_GUIDE_KO.md`
- 기존 `~/samsung_AXI`는 보존, 전용 `~/samsung_AXI_d_service` 사용.
- 기본 `bash scripts/smartdish_d_wsl2_one_shot.sh --verify`는 NO_GOAL.
- 기존 `main`/A/B/C 소스 변경 없음. D05 Git·빌드 검증은 실제 Gazebo 3구간 주행의 대체 근거가 아닙니다.
