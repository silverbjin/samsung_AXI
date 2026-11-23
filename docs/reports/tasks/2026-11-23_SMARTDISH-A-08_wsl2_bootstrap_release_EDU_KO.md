# SMARTDISH-A-08 — WSL2 원샷 단일 명령 배포·교육 보고서

- 날짜: 2026-11-23 KST
- 소유 브랜치: `feat/smartdish-a-robot`
- GUI 기본 원샷 출시 소스 SHA: `7d110ece67096151daff7bf351420952b18a9a66`
- 실제 현장 WSL2 L3: **A-09 실제 운영자 GUI 3-leg PASS**(실행 SHA `2ec54a0`, 신규 GUI 기본값만 변경되어 재주행 불필요)
- A의 이전 실 Gazebo CI L2: [운영 YAML #45125551884](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884), 실제 Nav2 3-leg **PASS**
- 담당자 수동 Goal 승인 정책: 필수, 자동 입력 금지

## 1. 사용자 관점: Ubuntu WSL2 한 줄 실행

WSL2 Ubuntu 24.04의 **대화형 터미널**에서 아래 한 줄을 그대로 복사·붙여넣기합니다.

```bash
curl -fsSLo "$HOME/smartdish_a_wsl2_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/7d110ece67096151daff7bf351420952b18a9a66/scripts/smartdish_a_wsl2_bootstrap.sh" && bash "$HOME/smartdish_a_wsl2_bootstrap.sh"
```

GUI 없이 실행하려면 아래 한 줄을 선택합니다.

```bash
curl -fsSLo "$HOME/smartdish_a_wsl2_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/cd99c59f90d26f80b247c2a3763b0b4a0ff981c2/scripts/smartdish_a_wsl2_bootstrap.sh" && bash "$HOME/smartdish_a_wsl2_bootstrap.sh" --headless
```

`curl`은 GitHub에 게시된 *정확한 커밋* `cd99c59`의 다운로드 파일을 저장하며, `bash`는 저장된 파일을 **그 터미널에서 실행**합니다. `curl | bash`를 사용하지 않는 이유는 stdin 파이프가 운영자 직접 TTY 입력 조건을 혼동시킬 수 있기 때문입니다.

## 2. 부트스트랩 내부 아키텍처

```text
[WSL2 Ubuntu] 1-line curl(download) && bash
       │
       ▼
scripts/smartdish_a_wsl2_bootstrap.sh
  ├─ WSL2 커널 / 실제 터미널 / HOME ext4 검사 (NO_GOAL)
  ├─ ~/samsung_AXI_A 미존재: A 브랜치만 clone
  ├─ 기존 저장소: origin·브랜치·tracked 변경 검사 + git merge --ff-only
  ├─ 실행 SHA 출력
  └─ exec bash scripts/smartdish_a_wsl2_one_shot.sh [--headless|--gui]
                  │
                  ▼
           A-07 map custody + colcon ROS Jazzy build
                  │
                  ▼
        Gazebo Harmonic + Nav2/AMCL/CM + scan/odom
                  │
                  ▼
       인간이 /dev/tty 직접 YES-SMARTDISH-A-GOALS
                  │
                  ▼
        HOME → T03 → DISH_RETURN → HOME
                  │
                  ▼
        l3_evidence.json + summary.json + compact log tar.gz
```

**재사용:** 기존 S7의 World·지도·공식 Nav2·Collision Monitor, 검증된 A-06 `table_poses.yaml`을 변경하지 않습니다.

## 3. 잘못된 배포 방지 설계의 이유

- *덮어쓰기 금지*: `~/samsung_AXI_A`에 다른 디렉터리/원격 저장소/브랜치/추적된 로컬 수정이 있으면 중단합니다.
- *강제 Git 조작 금지*: `reset --hard`·`git clean -fd`·`rm -rf` 없이 `fetch` 후 `merge --ff-only`만 합니다. 브랜치가 분기되었다면 개발자의 변경을 보존한 채 차단합니다.
- *실제 Goal 안전*: 부트스트랩에서 자동 인증·승인 문자열·ROS Goal을 보내지 않습니다. A-07은 실제 `/dev/tty` 직접 승인 후에만 Goal 발행을 허용합니다.
- *기기 격리*: `WSL_DISTRO_NAME`·WSL2 커널·`/dev/tty`가 아니라면 **클론조차 진행하지 않고** 종료합니다.
- *추적성*: 다운로드는 고정 SHA이며 실제 checkout Git SHA를 `SMARTDISH_A_BOOTSTRAP_SOURCE_SHA`·L3 JSON으로 기록하므로 이후 업데이트 버전을 분리할 수 있습니다.

## 4. 결과 판단

성공(운영자의 WSL2에서 **실제로 확인한 뒤에만**): `SMARTDISH_A_WSL2_OWNER_L3_PASS`.
차단: `SMARTDISH_A_BOOTSTRAP_BLOCKED_NO_GOAL`.
실패: `SMARTDISH_A_WSL2_OWNER_L3_NOT_PASS` 또는 `SMARTDISH_A_WSL2_FIRST_FAILURE`.
증거 제출: `~/samsung_AXI_A/generated/smartdish_a_wsl2/<run_id>/smartdish_a_owner_evidence.tar.gz` **하나만** 첨부합니다.

## 5. 검증 구분 및 RED→GREEN

- L0: `bash -n` 및 `--help`, 일반 GitHub CI 비-WSL2에서 원격 clone/실주행 전 차단, unsafe Git 변경이 없음, 기존 A 계약 회귀.
- L1: ROS Jazzy 컨테이너 `smartdish_robot navigation_adapter` 정상 빌드·발견.
- L2: 이전 A-06 실제 Gazebo 3/3 SUCCEEDED (검증된 운영 좌표; 부트스트랩 자체에 대한 실주행 증거와는 다름).
- **WSL2 L3: GUI 사용자의 현장 3-leg PASS**가 [A-09](2026-11-23_SMARTDISH-A-09_WSL2_GUI_L3_ACCEPTANCE_EDU_KO.md) 증거로 확인됨. GUI 기본값만 변경했으므로 Nav2 재주행 불필요. `PASS`를 임의 생성하지 않으며 실패하면 첫 실패 증거만 수집하여 교육용 `docs/reports/issues/`로 추적합니다.

## 6. 초심자 디버깅 예

`SMARTDISH_A_BOOTSTRAP_BLOCKED_NO_GOAL: Local tracked edits present`라면 `git status`로 수정 파일을 확인하고 커밋·stash 후 다시 실행합니다. **절대 reset --hard로 무조건 지우지 않습니다.** `SMARTDISH_A_BOOTSTRAP_BLOCKED_NO_GOAL: Origin mismatch`라면 Git 원격이 다른 프로젝트일 수 있으므로 리포지토리 출처부터 확인합니다. Gazebo·Nav2 실행 실패는 A-07 증거 번들의 첫 오류와 해당 로그에서만 진단합니다.

## 7. 출시 최종 CI 결과 (확인된 사실)

- [Actions #45129546662](https://github.com/silverbjin/samsung_AXI/actions/runs/45129546662), 실제 CI 소스 `75160a89e6af5fbb59fa36d82d60f17754b44131`.
- **L0 PASS — 45 tests**: `bash -n` 두 셸 실행기, 실제 운영자 확인을 보존한 비-WSL 차단, 올바른 브랜치 및 fast-forward, 손상된 증거/과장 성공 차단.
- **L1 PASS — ROS Jazzy**: `Summary: 1 package finished`, `smartdish_robot navigation_adapter`, `SMARTDISH_A_L1_BUILD_NO_GOAL_PASS` 확인.
- 본 최종 보고 변경은 문서만 변경하며 동일 부트스트랩·ROS 소스·운영 좌표는 보존합니다.
- 전체 인수 구분: 기 검증 A-06 Gazebo CI L2 3/3 PASS. **사용자 소유 WSL2 L3는 기존 실행 SHA `2ec54a0`에서 3/3 PASS로 확인 (A-09 보고서)**. D UI/10초/5초 완료도 NOT_RUN.

## 8. GUI 모드 기본 정책 갱신(A-10)

기본 인자 없이 `bash smartdish_a_wsl2_bootstrap.sh`를 호출하면 `--gui`를 기본값으로 사용합니다. 내부 `smartdish_a_wsl2_one_shot.sh`의 직접 호출도 GUI를 기본값으로 적용합니다. **헤드리스 대체가 필요하면 마지막에 `--headless`를 명시적으로 붙입니다.** 사용자 요청에 따라 기본 표시만 전환했고, Nav2/Collision Monitor/승인/판정 로직은 수정하지 않았습니다.
