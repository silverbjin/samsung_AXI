# S6 G12 — G06/G09 인수 실행기 혼재 해소 및 공식 진입점 단일화

2026-11-23 | 변경 성격: **실행기 진입 경로/문서/테스트만 수정**, Nav2/Gazebo/CM/모델/안전 정책 불변.

## 1. 질문: 왜 인수 실행기 SHA와 실제 코드 SHA가 다른가?

**두 계층이 서로 다른 불변 Git 커밋을 소유하기 때문**입니다. (1) 실행기 SHA `6fc1ac685858cb075e56514e03f72ad3a504fd87`는 사용자가 내려받는 Bash 원샷을 고정합니다. (2) 해당 원샷의 `SOURCE_SHA=9d402a991d1ee0a1c46027abe91a55266b69d9bd`는 `samsungaxi_wsl2_gui_acceptance_once.sh` 및 실제 ROS/Gazebo 소스 실행을 고정합니다. (3) `main` 병합 커밋 `344c242a00b716ec12bac72f5acd51d2592bd8ca`는 저장소 통합 상태를 나타내며 두 핀과 의미가 다릅니다.

**중요:** 스크립트의 실행기 SHA가 실제 source SHA보다 늦게 생성되는 것은 타당합니다. 실행기가 확정된 런타임 버전을 *가리키기* 때문입니다. 이것은 일반적인 bootstrapper/runtime 버전 구분이며 그 자체로 버그가 아닙니다.

## 2. 실제 GitHub 개발 타임라인 (소스 확인)

| 개발 단위 | 스크립트 이름 | 당시 실제 런타임 | 관측 결과 | 현재 처리 |
|---|---|---|---|---|
| 최초 S6 L2 | `samsungaxi_s6_wsl2_l3_once.sh` | `937fbf025cefec01489c40bc5104c39e3d4709be` | Gazebo L2 PASS, 최초 현장 L3는 NOT_RUN | **진입점 폐기** |
| G01~G06 OpenGL 디버깅 | `samsungaxi_s6_wslg_reaccept_once.sh` (초기 상태) | `611ac7b9edf5aa275dc4dbbde86530a573165a77` | Qt/XCB·프로세스 격리 L0 성공, 이후 Gazebo 복귀/초기화 RED 2건 | **이력 보존** |
| G09 (G08 RED 이후) | **위와 같은 `samsungaxi_s6_wslg_reaccept_once.sh` 파일을 repin** | `9d402a991d1ee0a1c46027abe91a55266b69d9bd` | [실제 Gazebo L2 #45106929216](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216) PASS, 강사 WSL2 G11 L3 PASS | **유일한 공식 실행기** |
| G11 | PR #31→PR #30→`main` | 위 G09 SOURCE_SHA 그대로 | S6 기능 인수·main 병합 완료 | PASS / GUI 육안은 사용자 담당 |

**G06 실행기와 G09 실행기는 파일명이 서로 다른 두 실행기가 아닙니다.** G06에 새로 만든 실행기 *동일 파일*의 내부 `SOURCE_SHA`를 G09 때 갱신한 것입니다. 다만 그 이전의 최초 S6 실행기(`samsungaxi_s6_wsl2_l3_once.sh`)가 별도로 남아 있어 총 두 경로가 혼재했습니다.

## 3. RED → GREEN: 이번 통일 사이클

**RED:** `main`에 최초 S6 실행기가 여전히 `937fb...`을 내려받으며 테스트도 이를 정상적인 공식 동작으로 간주했습니다. 최초 강사 가이드와 G06/G09 당시 가이드에는 서로 다른 실행 블록과 과거 NOT_RUN 상태가 섞여 있었습니다.

**변경:**
- 공식 문서 [S6_OFFICIAL_OWNER_ENTRY_KO.md](../../S6_OFFICIAL_OWNER_ENTRY_KO.md)를 **한 곳만** 운영합니다. 사용자가 지정하는 값은 `ENTRY_SHA=6fc1ac...` 하나뿐이며 내부 G09 `SOURCE_SHA=9d402...`는 자동 고정됩니다.
- 과거 `scripts/samsungaxi_s6_wsl2_l3_once.sh`는 **네트워크/ROS/Goal 실행을 하지 않고** `S6_LEGACY_ENTRY_RETIRED_NO_GOAL`과 공식 문서 링크를 출력해 차단합니다. 과거 immutable SHA의 원본을 소급 수정하지 않습니다.
- 과거 `docs/S6_WSL2_L3_OWNER_GUIDE_KO.md`, `docs/S6_WSLG_GUI_REACCEPT_GUIDE_KO.md`는 공식 문서로 연결만 남깁니다. `README.md`에도 첫 화면에서 해당 공식 문서를 제시합니다.
- `tests/test_s6_owner_release.py`, `tests/test_s6_canonical_entry.py`에 오래된 실행기의 Fail Closed, 공식 가이드 SHA 및 TTY 계약을 검증하는 L0 테스트를 추가했습니다.
- 기존 `scripts/samsungaxi_s6_wslg_reaccept_once.sh`와 실제 G09 `9d402...` 런타임 **변경 없음**. 과거 L2/L3 성공 증거 재시험 불필요.

**GREEN:** [공개 CI #45111731548](https://github.com/silverbjin/samsung_AXI/actions/runs/45111731548)에서 표준 실행기/레거시 차단·교육용 Vision 상태 계약 정적 테스트 PASS. 추가 문서 변경 후 CI 역시 별도 확인하며, GUI/WSL2 실제 운전 재실행 결과라고 주장하지 않습니다.

## 4. 초심자용 데이터 흐름

사용자 WSL2 터미널 → ENTRY_SHA 고정 curl(원샷 Bash) → G09 SOURCE_SHA 선택 → 같은 SOURCE_SHA의 wrapper 및 실제 소스 준비 → no-goal preflight → TTY 수동 YES-S5-LIVE-GOALS → Nav2 TABLE_3 → 물리 Odom 정지 → RGB Vision STACKED → Nav2 RETURN → LiDAR STOP → ZIP 증거.

**예외 관리:** S6 초창기 G06 이전 명령 또는 불변 커밋 `105300...`을 재실행하면 원본 오래된 코드가 계속 다운로드됩니다. Git에서 이미 생성된 커밋은 수정할 수 없으므로 이를 공개 문서와 현재 `main` 레거시 경로에서 명확히 차단하는 것이 정당한 조치입니다.

## 5. 교육 질문 및 향후 통제

1. 외부 실행기 SHA와 실제 런타임 SHA가 다른 것이 왜 항상 오류는 아닙니까?
2. `main` HEAD를 현재 시각의 가변 포인터로 참조할 때와 검수된 불변 SHA를 사용했을 때 재현성 차이는 무엇입니까?
3. 기존 실행기 경로가 새 코드의 동작을 잘못 대표하지 않으려면 어떤 최소 퇴역 조치가 필요합니까?
4. 왜 문서/레거시 진입점 변경을 GUI·안전 기능 실제 L3 반복 인수로 대체하지 않아도 됩니까? **바뀐 코드 경계를 구분해야** 하기 때문입니다.

**운영 규칙:** S6 기능 변경이 새 SHA로 검증되면 동일한 공식 한 곳의 가이드에서 ENTRY_SHA/RUNTIME_SHA를 동시 갱신하고, 예전 실행기는 '현재용'으로 안내하지 않습니다. 사용자 GUI 육안 확인은 자동/병합 게이트가 아니며, ROS Action·실제 RGB·STOP는 여전히 필수입니다.
