> **G11 이후 확정 정책:** 강사 WSL2에서 최종 코드 SHA 9d402a99...에 대한 **S6 기능 L3 PASS**를 확보했습니다. 시각적 GUI 육안 검수는 사용자 전담이며 기능 자동 인수 및 main 병합 필수 게이트에서 제외합니다. 실행기의 과거 문구 GUI_VISUAL_REVIEW_REQUIRED와 L3 미확정 안내보다 [G11 최종 검수 보고서](debug/s6/20261123_G11_FINAL_WSL2_L3_ACCEPTANCE_EDU_KO.md)의 판정이 우선합니다. TTY 승인·Nav2·RGB·CM STOP 안전 증거는 계속 필수입니다.

# S6 WSL2 GUI OpenGL 디버깅 재인수 — 사용자 단일 실행 가이드

> 출고 상태: GitHub 릴리스 L0 PASS, 변경 런타임의 S6 실제 Gazebo L2 진행 중, 강사 WSL2 실제 GUI/L3 NOT_RUN. 목표 RTF 90% HOLD.

## 시작 조건 및 기준 SHA

- 릴리스 엔트리 원본 커밋: `6fc1ac685858cb075e56514e03f72ad3a504fd87`
- 엔트리에서 다운로드하는 **변경된 런타임 코드 SHA**: `9d402a991d1ee0a1c46027abe91a55266b69d9bd`
- 이전 성공한 S6 L2 런타임 SHA: `937fbf025cefec01489c40bc5104c39e3d4709be` (무수정 원본으로 보존)
- 이전 GUI 실패 ZIP SHA256: `e045f50f6e66c305eed22885d37c1fa533b20bfe37c720f82b07adaa190aa8d3`

## 1. 실행 블록: NO_GOAL → 사람 TTY 승인 → TABLE_3 → RGB STACKED → 복귀 → LiDAR STOP

WSL2 Ubuntu 24.04에서 아래를 복사해 실행합니다. 실제로 실행되는 GitHub 스크립트는 SHA로 고정되어 있으며, 실행 도중 새 코드를 개발하지 않습니다.

```bash
(
  set -Eeuo pipefail
  RELEASE_SHA='6fc1ac685858cb075e56514e03f72ad3a504fd87'
  F="$(mktemp --suffix=.sh)"
  trap 'rm -f "$F"' EXIT
  curl -fL --retry 3 --connect-timeout 10 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$RELEASE_SHA/scripts/samsungaxi_s6_wslg_reaccept_once.sh" \
    -o "$F"
  bash -n "$F"
  bash "$F" --self-test
  bash "$F"
)
```

## 2. 실행 절차 및 성공 증거

1. 출력의 `S6_WSLG_REACCEPT_SELF_TEST_PASS_NO_GOAL`, `S6_WSLG_PREFLIGHT_PASS_NO_GOAL` 확인.
2. S6 Qt GUI만 `QT_QPA_PLATFORM=xcb`를 사용합니다. D3D12 강제 자동선택은 해제했으며 현재 로그인 셸 환경은 그대로 유지합니다.
3. Gazebo와 RViz 화면이 정상인지 **운영자가 눈으로 확인합니다**. 창이 없다면 Goal을 승인하지 않습니다.
4. 실제 프롬프트가 나오면 `YES-S5-LIVE-GOALS`를 직접 입력하여 승인합니다.
5. 다음 문자열과 증거를 점검합니다: `S3_NAV02_REAL_GOAL_ACCEPTED=TABLE_3`, 첫 Action 성공 및 Odom 정지, `S6_VISION_REAL_RGB_STACKED_RETURN_AUTHORIZED`, `S3_NAV02_REAL_GOAL_ACCEPTED=PICKUP_RETURN`, LiDAR CM STOP, 실제 속도/이동량.
6. 실제 성공 후 Ctrl+C로 종료하면 `SAMSUNGAXI_DIAGNOSTIC_ZIP=...` 경로를 출력합니다. 같은 RUN_ID의 `s5_live_evidence.json`과 `s6_table_rgb.ppm`을 ZIP에서 확인합니다.
7. ZIP과 사용자가 확인한 GUI 상태를 제출하면 강사 WSL2 L3 최종 인수를 판정합니다.

GUI 오류가 재발하면 `S6_GUI_OPENGL_CONTEXT_CREATE_FAILED` 또는 `S6_GUI_PROCESS_ABORTED`가 먼저 기록되는지 확인합니다. Nav2 후속 context 오류를 원인으로 오분류하지 않습니다.

## 3. 독립 GUI 렌더링 진단 (실제 Goal **절대 없음**)

위 명령 실행 후 GUI가 여전히 실패하면 동일 ZIP 없이 아래처럼 실행기를 다시 받아 `--diagnose-only`를 사용합니다.

```bash
(
  set -Eeuo pipefail
  RELEASE_SHA='6fc1ac685858cb075e56514e03f72ad3a504fd87'
  F="$(mktemp --suffix=.sh)"
  trap 'rm -f "$F"' EXIT
  curl -fL --retry 3 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$RELEASE_SHA/scripts/samsungaxi_s6_wslg_reaccept_once.sh" -o "$F"
  bash -n "$F"
  bash "$F" --diagnose-only
)
```

`~/samsungaxi_gui_evidence/s6_wslg_qt_gl_*.zip`에 baseline/XCB/XWayland/D3D12/llvmpipe 결과와 종료 코드, ogre2.log 최근 부분을 압축합니다. **NO_GOAL 진단으로만 활용**하며 'GUI 생존'을 GUI 성공으로 판정하지 않습니다.

## 4. 단계별 증거와 교육 참고

- 기존 실제 S6 L2 PASS: https://github.com/silverbjin/samsung_AXI/actions/runs/45098202033
- 신규 scoped XCB 변경 L0 28/28 PASS: https://github.com/silverbjin/samsung_AXI/actions/runs/45104473441
- 새 WSLg 고정 실행기 L0 PASS: https://github.com/silverbjin/samsung_AXI/actions/runs/45104827199
- 각 RED→GREEN 보고서: docs/debug/s6/20261123_G01_FIRST_FAILURE_EDU_KO.md, 20261123_G02_G03_GL_AB_EDU_KO.md, 20261123_G04_G05_GUI_LIFECYCLE_EDU_KO.md, 20261123_G06_RELEASE_EDU_KO.md.
- 주니어 체크: 사용자 승인과 ROS Action Goal은 별개이고, GUI 렌더러 실패와 Nav2 Lifecycle 후속 오류는 서로 다른 시간 순서를 가집니다.
- `main` 병합은 현장 L3 PASS 및 문서 갱신 후에만 수행합니다.

## 5. G09 실제 Gazebo 인수 확인과 남은 구분
- **검증 SHA** `9d402a991d1ee0a1c46027abe91a55266b69d9bd`: [S6 L0/L1/L2 CI #45106929216](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216) SUCCESS.
- TABLE_3 Action SUCCEEDED 5.137m, RGB 3프레임 모델 STACKED confidence 0.6652, PICKUP_RETURN SUCCEEDED 5.054m, LiDAR CM STOP 29점, 필터 출력 0m/s, 정지 Odom 0m.
- [Artifact #14787673933](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216/artifacts/14787673933) / ZIP SHA256 `a9ee749ef91586b27a19de04e6e2cc902176701d3f66971c4225ab1a96cd528c`.
- 변경 내용: S6만 Nav2/Gazebo 초기화를 10초 분리하고 BT `default_server_timeout` 200ms 적용, 기본 S5 설정과 안전 임계값은 보존.
- **강사 WSL2 GUI OpenGL 해결은 아직 검증되지 않았습니다.** 사용자의 진단 ZIP, 실제 Gazebo/RViz 화면 확인, 동일 SHA 두 Goal·Vision·STOP 증거가 있어야 L3 PASS로 인정합니다.
- S6 주행 중 RGB를 상시 AI 구독하지 않습니다. 카메라의 Gazebo 렌더러 자체가 유휴 상태인지와 RTF≥0.90은 HOLD입니다.
