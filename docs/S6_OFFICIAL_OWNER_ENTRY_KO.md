# SAMSUNGAXI S6 — 유일한 공식 WSL2 인수 실행기 (2026-11-23)

> **상태: S6 기능 릴리스 L0/L1/L2/L3 PASS, main 병합 완료.** 사용자 GUI 육안 검수는 별도이며 자동 기능/병합 게이트가 아닙니다. RTF 90%는 HOLD입니다.

## 1. 운영자가 기억할 유일한 실행기

- **공식 경로:** `scripts/samsungaxi_s6_wslg_reaccept_once.sh` (G06 당시 제작돼 G09에서 **업데이트된 동일 파일**).
- **불변 실행기 커밋:** `6fc1ac685858cb075e56514e03f72ad3a504fd87`. 스크립트를 다운로드하는 기준이며, 실행 절차/TTY/사전검사를 소유합니다.
- **실제 ROS/Gazebo 코드 커밋:** `9d402a991d1ee0a1c46027abe91a55266b69d9bd`. 실행기 내부 `SOURCE_SHA`에 고정돼 있으며 Goal/카메라/CM/Nav2를 실행하는 코드입니다.
- **main S6 병합 커밋:** `344c242a00b716ec12bac72f5acd51d2592bd8ca`. 통합된 저장소의 변경 이력입니다. **실행할 코드 SHA를 대체하지 않습니다.**
- 개발 이력의 초기 S6 런타임 `937fbf...` 및 G06 디버깅 런타임 `611ac7...`은 **인수 목적의 사용 금지 / 역사 증거로만 유지**합니다.

### WSL2 Ubuntu 24.04 단일 실행 블록 — 이것만 사용

```bash
(
  set -Eeuo pipefail
  ENTRY_SHA='6fc1ac685858cb075e56514e03f72ad3a504fd87'
  SCRIPT="$(mktemp --suffix=.sh)"
  trap 'rm -f "$SCRIPT"' EXIT
  curl -fL --retry 3 --connect-timeout 10 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$ENTRY_SHA/scripts/samsungaxi_s6_wslg_reaccept_once.sh" \
    -o "$SCRIPT"
  bash -n "$SCRIPT"
  bash "$SCRIPT" --self-test
  bash "$SCRIPT"
)
```

**명령에서 사용자가 지정하는 SHA는 단 하나, `ENTRY_SHA`입니다.** 내부 소스 SHA는 실행기가 자동 설정하며 조합하지 마십시오. 출력의 `S6_WSLG_TESTED_RUNTIME_SOURCE_SHA=9d402a991d1ee0a1c46027abe91a55266b69d9bd`로 이중 고정이 일치하는지만 확인합니다.

## 2. 정상 실행 순서와 안전

1. `S6_WSLG_REACCEPT_SELF_TEST_PASS_NO_GOAL` → 기존 S5 검증을 재사용한 `S6_WSLG_PREFLIGHT_PASS_NO_GOAL` 확인.
2. Gazebo/RViz 시각적 상태는 운영자가 별도 확인합니다. **시각 검수는 자동 합격 게이트가 아닙니다.** 단, 실제 로봇 제어에 위험·오작동이 보이면 승인하지 마십시오.
3. 실제 TTY에서 `YES-S5-LIVE-GOALS`를 직접 입력하기 전에는 Goal을 내보내지 않습니다.
4. `S3_NAV02_GOAL_SUCCEEDED=TABLE_3` → 실제 Odom 정지 → 최신 RGB 3프레임 → `S6_VISION_REAL_RGB_STACKED_RETURN_AUTHORIZED` → `S3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN` → `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS`를 확인합니다.
5. 성공 이후 Ctrl+C로 종료하면 `SAMSUNGAXI_DIAGNOSTIC_ZIP=...`을 출력합니다. `RUN_RC=130`만으로 실패 또는 clean shutdown을 단정하지 말고 같은 ZIP의 Goal·Vision·STOP·FIRST_FAILED_MARKER를 검사합니다.
6. GPU/OpenGL 단독 진단이 필요한 경우 **같은 파일**을 `bash "$SCRIPT" --diagnose-only`로 실행할 수 있으나 ROS/Goal은 실행되지 않습니다. 단독 진단을 새로운 기능 PASS로 해석하지 마십시오.

## 3. 왜 실행기 SHA와 런타임 SHA가 다른가?

| SHA 종류 | 담당 | 불변성의 의미 |
|---|---|---|
| ENTRY_SHA `6fc1ac...` | 사용자 다운로드, 자체 검사, 원본 고정·TTY/사전검사 흐름 | 항상 같은 *실행기 내용* |
| SOURCE_SHA `9d402...` | ROS 2/Gazebo/Nav2/AI/Safety 실제 워크스페이스 코드 | 항상 같은 *검증된 로봇 프로그램* |
| main `344c...` | 여러 PR/보고서의 통합 브랜치 | 계속 발전할 수 있으며 고정 인수 버전이 아님 |

이는 패키지 실행기의 버전과 실제 애플리케이션 버전을 구분하는 **의도적인 이중 핀 구조**입니다. 다른 SHA라고 버그가 아니며, 잘못된 것은 두 실행기와 과거 명령을 동시에 현재용으로 안내한 일입니다. 이제 사용자는 **G09 완료된 실행기 하나만** 사용합니다.

## 4. G06/G09 개발 이력

- 초기 `samsungaxi_s6_wsl2_l3_once.sh`: S6 첫 통합 SHA `937fb...`을 실행했습니다. G09 이후 **폐기된 진입점**입니다. 최신 `main`의 같은 경로는 동작을 막는 안전 안내 스크립트입니다. 과거 immutable SHA `105300...`에 저장된 원본은 수정할 수 없으므로 재사용하지 마십시오.
- G06: WSLg Qt OpenGL context 최초 실패를 확인하고 GALLIUM D3D12 자동 적용을 S6에서 중지, Gazebo GUI만 Qt XCB/종료 분리, GUI 에러를 Goal 전에 기록하도록 구현. 당시 `samsungaxi_s6_wslg_reaccept_once.sh`는 디버깅 코드 SHA `611ac7...`을 실행했습니다.
- G08: 동일 SHA 실제 Gazebo 두 차례에서 서로 다른 Map/Lifecycle 준비 실패 및 FollowPath ack timeout RED 증거를 보존했습니다.
- G09: 같은 `samsungaxi_s6_wslg_reaccept_once.sh` 내부 SOURCE_SHA를 CI/WSL2 성공한 `9d402...`으로 변경했습니다. S6 전용 Nav2 시작 10초 분리 + BT Goal ack 200ms 적용. 새 파일 이름이 아닌 **같은 실행기의 내용 업데이트**입니다.
- G11: 동일 SHA의 강사 WSL2 L3 배달·AI·복귀·LiDAR STOP PASS 후 PR #31/#30을 `main`에 병합. 화면 육안 검수는 사용자 담당 별도 기록입니다.

## 5. 공식 증거와 앞으로의 변경 관리

- [G09 실제 Gazebo CI #45106929216](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216) (L2 PASS).
- [G11 강사 WSL2 기능 L3 인수](debug/s6/20261123_G11_FINAL_WSL2_L3_ACCEPTANCE_EDU_KO.md) (정확한 SOURCE_SHA PASS).
- [G06/G08/G09 교육 보고서](debug/s6/20261123_G09_NAV2_CONTROLPLANE_EDU_KO.md).
- [향후 S7/GUI/성능 백로그](S6_POST_RELEASE_ROADMAP_KO.md).
- 향후 새로운 기능 변경은 별도 브랜치에서 테스트한 후, 검증된 **새로운 버전 하나**를 공식 가이드와 실행기에 동시에 반영합니다. 기존 G09 SHA와 인수 증거는 소급 수정하지 않습니다.
