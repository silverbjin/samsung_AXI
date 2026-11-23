# SmartDish D — WSL2 원샷 실행 가이드 (초심자용)

## 먼저 확인할 것

- Ubuntu 24.04 / ROS 2 Jazzy 설치, Git/colcon/pytest 설치, 인터넷 연결
- 원격 저장소: `silverbjin/samsung_AXI`, D 브랜치 `feat/smartdish-d-service`
- **기존 `~/samsung_AXI` 디렉터리는 그대로 둡니다.** 삭제·reset·clean·강제 checkout 금지.
- 실제 로봇 이동은 A/E 통합 전에는 수행하지 않습니다.

## 1. clone과 재실행의 차이

과거에는 같은 `~/samsung_AXI`에 clone을 반복해 실패했고, 그다음 명령이 오래된 소스에서 실행됐습니다. 새 실행기는 무조건 전용 `~/samsung_AXI_d_service`에 소스를 둡니다.

```text
~/samsung_AXI                ← 기존 S7·A/B/C 작업을 보존
~/samsung_AXI_d_service      ← D 전용 소스 (Git)
~/.local/state/smartdish-d/  ← D 테스트·빌드·설치·로그 (Git 밖)
```

기존 D 전용 폴더에 미커밋 소스가 있거나 원격 브랜치보다 HEAD가 뒤/앞선 상태면 자동 merge/rebase 하지 않고 **사람에게 먼저 검토**를 요청합니다.

## 2. 저장소를 clone한 사용자 — 로컬 실행

```bash
cd ~/samsung_AXI_d_service
bash scripts/smartdish_d_wsl2_one_shot.sh --preflight
bash scripts/smartdish_d_wsl2_one_shot.sh --verify
```

최초에는 전용 경로가 없으므로 *뒤의 4단계 pinned 다운로드 명령*으로 bootstrap 하세요. 지금의 `cd` 예시는 이미 작업 경로가 있는 경우만 해당합니다.

## 3. 화면(GUI)을 실행할 때

```bash
cd ~/samsung_AXI_d_service
bash scripts/smartdish_d_wsl2_one_shot.sh --run-ui
```

- `DISPLAY`가 없거나 Tk 생성에 실패하면 스크립트는 중단합니다.
- UI가 실제로 생성되고 이벤트 루프가 시작될 때 `SMARTDISH_D_UI_READY`가 출력됩니다.
- 시작 시 AI OFF입니다. A Navigation Adapter가 없으면 D는 `ADAPTER_NOT_READY_NO_GOAL`로 회수 명령을 거부합니다.
- **화면 표시 성공 ≠ Nav2 Goal 성공**. A의 실제 3-leg·odom·동일 request_id UI COMPLETED는 E 통합에서만 인수합니다.

## 4. 리포지토리 경로와 무관한 pinned 실행

GitHub PR #38에서 검증된 최신 Commit SHA를 확인한 후 아래 *형식*의 명령을 사용합니다. 다운로드 코드는 SHA를 고정해야 하며, 현장 실행 전 아래의 `PIN` 값은 반드시 최신 CI PASS 커밋으로 설정하십시오.

```bash
PIN=<40-hex-verified-D-commit>
FILE=$(mktemp --suffix=.sh)
curl -fsSL --retry 3 \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_d_wsl2_one_shot.sh" \
  -o "$FILE"
bash -n "$FILE" && SMARTDISH_D_SOURCE_SHA="$PIN" bash "$FILE" --verify
rm -f "$FILE"
```

**주의:** 위 내용은 CI 결과 확인 전의 범용 형식입니다. 실제 검증된 SHA/명령은 최종 보고 및 PR 인계에서 제공됩니다.

## 5. PASS와 BLOCKED 판단법

| 마커 | 뜻 | 다음 조치 |
|---|---|---|
| `GIT_PASS` | remote/branch/SHA/clean 검증 | 필수 소스 확인 |
| `SOURCE_PASS` | D 소스와 테스트 존재 | ROS 환경 확인 |
| `PREFLIGHT_PASS_NO_GOAL` | 빌드 전 기본 검증 | `--verify` 실행 |
| `VERIFY_PASS_NO_GOAL` | pytest·패키지 빌드/설치 확인 | 필요하면 `--run-ui` |
| `BLOCKED=DIRTY_WORKTREE` | 기존 로컬 변경을 발견해 보존 | 사용자 직접 diff/stash/commit |
| `BLOCKED=WRONG_ORIGIN` | 다른 리포지토리를 가리킴 | 기존 디렉터리 보존, 원격 확인 |
| `BLOCKED=REMOTE_HEAD_CHANGED` | remote와 HEAD 불일치 | 수동 비교 후 안전한 업데이트 |
| `BLOCKED=PACKAGE_NOT_DISCOVERED` | ROS 패키지 미발견 | D 소스·package.xml 확인 |
| `BLOCKED=COLCON_BUILD_FAILED` | 빌드 실패 | 최초 오류와 colcon 로그 확인 |

오류가 난 시점부터 후속 단계를 진행하지 않습니다. `SMARTDISH_D_BLOCKED`가 나오면 `FAILED_STAGE`, `SOURCE_SHA`, `NEXT_ACTION`을 함께 보내 주시면 오류 구간을 좁혀 분석할 수 있습니다.

## 6. 교육용 문제

- 왜 `git clone` 실패 직후 `cd samsung_AXI`가 성공할 수도 있나요?
- 같은 `install/setup.bash`를 source해도 소스 파일이 다른 브랜치라면 왜 ROS package가 없나요?
- 임시 Git fixture가 통과해도 WSL2 GUI와 실제 Gazebo 로봇 인수는 별도인 이유는 무엇인가요?
