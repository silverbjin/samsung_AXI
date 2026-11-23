# D-DBG-004 — GitHub Actions 작업 SHA와 이동하는 원격 브랜치의 경쟁 조건

- 날짜: 2026-11-23
- 담당: D DevOps/CI
- 관측된 실제 오류: [Actions #45124788414](https://github.com/silverbjin/samsung_AXI/actions/runs/45124788414), L0 성공/L1 원샷 단계 실패
- 관련 소스 SHA: 해당 workflow commit `7f64c534b141d7f020e8328566262ca50a83e99a`
- 보호 관점: 로컬 실행기 안전 기능은 **정상적으로** 불일치 감지, CI 환경 구성은 비결정적이었음

## 최초 실패 원본과 시간 순서

```text
SMARTDISH_D_SOURCE_SHA: 7f64c534b141d7f020e8328566262ca50a83e99a
SMARTDISH_D_MODE=--verify
SMARTDISH_D_BLOCKED=SOURCE_PIN_MISMATCH
FAILED_STAGE=GIT
SOURCE_SHA=a82b3e229a330c2c38dc9857be26a232d21578da
NEXT_ACTION=Review the SHA change and update the pinned release
```

CI job은 **옛 커밋**을 검증하려는 동시에 `git clone -b feat/smartdish-d-service`로 **당시 새 HEAD**를 받았습니다. 그래서 source pin이 달라졌습니다. 이는 소스 충돌도 Gazebo 오류도 아니며, 검사 입력 중 하나(원격 브랜치)가 실행 시점에 따라 바뀐 **CI 경쟁 조건**입니다.

## 원인과 수정 전후

| 항목 | 수정 전 | 수정 후 |
|---|---|---|
| CI에서 clone하는 remote | 현재 공개 feature branch (시간에 따라 변경) | 이 CI의 `GITHUB_SHA`만 포함한 `/tmp/smartdish_d_ci_remote.git` |
| PIN | workflow `github.sha` | 동일한 `github.sha` |
| 실제 Jazzy ROS 패키지 | ros:jazzy-ros-base-noble | 동일 (가짜 ROS 아님) |
| 변경된 것 | CI 스크립트의 remote fixture 설정 | D runner 자체, ROS/Nav2/A/B/C 변경 없음 |
| 예상 판정 | 새 커밋 시 mismatch 가능 | 해당 SHA 고정 후 L0/ROS L1 독립 시험 |

## 수정 구현

```bash
git init --bare /tmp/smartdish_d_ci_remote.git
git push /tmp/smartdish_d_ci_remote.git \
  "$GITHUB_SHA:refs/heads/feat/smartdish-d-service"
export SMARTDISH_D_TEST_MODE=1
export SMARTDISH_D_TEST_REPO_URL=file:///tmp/smartdish_d_ci_remote.git
export SMARTDISH_D_TEST_WORKDIR=/tmp/smartdish_d_ci_worktree
export SMARTDISH_D_TEST_STATE_DIR=/tmp/smartdish_d_ci_state
export SMARTDISH_D_TEST_ROS_SETUP=/opt/ros/jazzy/setup.bash
SMARTDISH_D_SOURCE_SHA="$GITHUB_SHA" \
  bash scripts/smartdish_d_wsl2_one_shot.sh --verify
```

위 `TEST_MODE=1`은 Git 원격/경로만 임시 fixture로 대체합니다. `/opt/ros/jazzy/setup.bash`, `python3 -m pytest`, `colcon build`, `ros2 pkg prefix`는 실제 Jazzy 환경에서 실행합니다. 일반 사용자에게는 테스트 환경변수 없이 기본 GitHub remote/전용 홈 작업공간을 사용하도록 안내합니다.

## 재검증/미검증

- [수정 전 L0 40 PASS 및 실제 L1 PASS #45124883730](https://github.com/silverbjin/samsung_AXI/actions/runs/45124883730) — public branch와 CI SHA가 일치한 경우
- [수정 전 시간차 RED #45124788414](https://github.com/silverbjin/samsung_AXI/actions/runs/45124788414) — 불일치 실패 사례를 원본으로 보존
- 수정 후 최신 CI의 실제 L0/L1 판정은 Actions 원본에서 확인하고 최종 PR에 기재합니다.
- 실제 사용자 WSL2 화면 및 Gazebo 3-leg는 여전히 NOT_RUN입니다.

## 교육용 질문

1. 왜 `GitHub Actions checkout`의 코드 SHA와 `git clone -b`가 내려받는 SHA가 항상 같지는 않나요?
2. 동일 소스를 대상으로 테스트해야 할 때 mutable branch 대신 immutable commit을 사용해야 하는 이유는?
3. `SOURCE_PIN_MISMATCH`을 로컬 모드에서 없애면 어떤 데이터 손상 위험이 생길까요?
4. 리포지토리 변경 없이 CI 입력 고정만으로 이 문제를 해결할 수 있는 이유는?

## CI-DBG-004B — CI 컨테이너 체크아웃 소유권 경계 (추가 RED)

- 최초 재검 실패: [Actions #45125230558](https://github.com/silverbjin/samsung_AXI/actions/runs/45125230558), L0 40 PASS / 기존 ROS Jazzy package build PASS / 고정 remote 생성 단계 FAIL.
- **실제 첫 오류:** `fatal: detected dubious ownership in repository at '/__w/samsung_AXI/samsung_AXI'`.
- 원인: GitHub-hosted runner에서 컨테이너 볼륨으로 가져온 checkout의 파일 소유자와 컨테이너 프로세스가 다를 수 있습니다. 안전 디렉터리 예외 없이 `git push`는 해당 경로를 사용할 수 없었습니다.
- 최소 수정: `git -c safe.directory="$GITHUB_WORKSPACE" push ...`로 **이 명령 한 번에 한하여** CI checkout 경로를 신뢰합니다.
- **금지:** 로컬 WSL2의 Git 보호를 해제하거나 `git config --global --add safe.directory '*'`로 모든 디렉터리를 신뢰하지 않습니다.
- 테스트: 같은 SHA의 Git bare fixture 생성→actual Jazzy `--verify`가 종료코드 0과 `SMARTDISH_D05_L1_PINNED_COMMIT_REAL_ROS_PASS_NO_GOAL`을 출력해야 GREEN입니다.
- 이 수정으로 처음 사용자에게 보고된 clone 오류, S7/A/B/C 소스 및 실제 로봇 제어 경로는 변경되지 않았습니다.

## CI-DBG-004C — Shallow checkout의 bare remote 전송 제한

- 추가 재검 RED: [Actions #45125448028](https://github.com/silverbjin/samsung_AXI/actions/runs/45125448028), L0 40 PASS, ROS Jazzy 패키지 자체는 PASS, 고정 bare 생성 단계 FAIL.
- 원본 첫 오류: `! [remote rejected] <sha> -> feat/smartdish-d-service (shallow update not allowed)`.
- 근본 원인: `actions/checkout@v4` 기본 `fetch-depth: 1`은 현재 commit만 있는 shallow checkout입니다. 이 shallow 소스를 새 bare remote에 그대로 push할 때 원격 측에서 역사를 온전히 표현할 수 없어 전송을 거부합니다.
- 수정: **L1 작업에만** `actions/checkout@v4 with: fetch-depth: 0`을 적용하고, 이후 동일한 명령으로 임시 로컬 bare remote를 생성합니다. 실제 ROS 2 코드는 변경하지 않습니다.
- 검증: 해당 CI commit의 immutable repo를 clone하여 `SMARTDISH_D_SOURCE_SHA=GITHUB_SHA`가 일치한 상태에서 실제 Jazzy `--verify` 실행/NO_GOAL 마커로 판정합니다.
- 교육 포인트: GitHub Actions 자체 checkout은 성공해도, 그 복제본을 **다른 bare remote로 재배포**할 때는 shallow 이력 제약이 별도 문제입니다.
