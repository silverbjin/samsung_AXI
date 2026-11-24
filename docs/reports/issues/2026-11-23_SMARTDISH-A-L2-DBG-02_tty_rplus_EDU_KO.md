# SMARTDISH-A-L2-DBG-02 — 실제 TTY 승인 함수의 비탐색 스트림 오류

- 날짜: 2026-11-23 KST
- 상태: **RESOLVED / 실제 TTY 승인 후 3구간 ROS/Gazebo L2 PASS**
- 실패 Run: https://github.com/silverbjin/samsung_AXI/actions/runs/45124267209
- 실패 SHA: `ee0b164ac6bd555f23cea4b872f6181d5ac53a1f`
- 연결 작업: [A-05 실 Gazebo 3구간](../tasks/2026-11-23_SMARTDISH-A-05_real_gazebo_3leg_EDU_KO.md)

## 1. 실제 증거와 첫 실패

- 실 Gazebo/AMCL/Nav2 시작: `A_L2_REAL_GAZEBO_PREFLIGHT_PASS_NO_GOAL`.
- A Adapter: `SMARTDISH_A_WAIT_NAV2_ACTIVE_NO_GOAL`, `Nav2 is ready for use!`, `SMARTDISH_A_SENSOR_PREFLIGHT_PASS_NO_GOAL {"odom": true, "scan": true}`.
- 첫 실패: `SMARTDISH_A_BLOCKED_NO_GOAL_OR_ABORTED {"reason": "OPERATOR_TTY_READ_FAILED_NO_GOAL"}`, 이어 `A_L2_FIRST_FAILURE=RuntimeError('ADAPTER_TTY_CLOSED')`.

**위 증거는 Nav2 Action Goal 전송 0건**입니다. 정확한 시뮬레이터 위치/경로의 문제나 식기 반납 Pose 실패로 진단하면 안 됩니다.

## 2. 원인 분리 실험 (실제 로컬 Python pseudo-TTY)

원본 `navigation_adapter.py`의 `os.fdopen(fd, "r+", buffering=1)` 호출을 동일한 `pty.fork()`의 `/dev/tty`에서 재현하였더니 아래 예외가 발생했습니다.

```text
io.UnsupportedOperation: File or stream is not seekable.
```

TTY는 seek 가능한 일반 파일이 아니므로 CPython에서 read/write 양방향 텍스트 스트림을 열려는 접근이 실패한 것입니다. 실제 GitHub CI 로그는 이 내부 OSError를 상위 `OPERATOR_TTY_READ_FAILED_NO_GOAL`로 포장한 사실과 일치합니다. **PTY 프로세스가 종료되어 발생한 2차 `ADAPTER_TTY_CLOSED`를 근본 원인으로 오해하지 않습니다.**

## 3. RED → 수정 → GREEN

- RED: 기존 `fdopen("r+")`는 터미널에서 비탐색 스트림 예외.
- 최소 수정: ROS와 분리한 `tty_approval.py`에서 `os.open("/dev/tty",O_RDWR)` 뒤 `os.write` + `os.read`를 직접 사용. 문자열 한 줄 입력만 받고 정해진 승인 문자열과 일치할 때만 다음 단계로 갑니다.
- 단위 회귀: `tests/test_smartdish_a_tty.py`가 실제 PTY 프로세스로 **정상 승인, 잘못된 승인 거절, fdopen 금지**를 확인.
- 로컬 독립 재현: 수정형 `os.read/write`로 올바른 승인 exit0 및 `NO` 입력 exit2를 확인했습니다. 이 검사는 **ROS/Action 주행 증거가 아닙니다**.
- 현장 정책: ROS 토픽, 환경 변수, 파이프로 실제 승인 우회 불가. `NavigationAdapter`는 TTY 성공 이후에만 `/collection/nav_goal` 구독.

## 4. 검증 대기

[Run #45124267209](https://github.com/silverbjin/samsung_AXI/actions/runs/45124267209)는 사전검사 PASS 후 승인 단계에서 종료됐습니다. 코드 수정 뒤 같은 CI에서 별도 Run을 받아 실제 3개의 Nav2 Action 및 odom 결과를 확인해야 **RESOLVED**로 종료할 수 있습니다.

## 5. 교육 포인트

예외 래핑 `OPERATOR_TTY_READ_FAILED_NO_GOAL`과 이후 관찰 `ADAPTER_TTY_CLOSED`는 같은 단계의 다른 증상입니다. 미세한 I/O 타입 문제를 Nav2 안전 설정·Gazebo 물리 설정으로 고치지 않았고, 순수 Python의 가장 작은 재현 환경으로 먼저 좁힌 뒤 안전승인 경계를 보존했습니다.

## 6. 수정 후 독립 GREEN (2026-11-23)

[Run #45124877004](https://github.com/silverbjin/samsung_AXI/actions/runs/45124877004)에서 `A_L2_TTY_PROMPT_OBSERVED_NO_GOAL` → 10초 후 `A_L2_SIMULATION_TTY_APPROVED_AFTER_DELAY` → `SMARTDISH_A_OPERATOR_APPROVED` → `SMARTDISH_A_READY` 순으로 확인했습니다. 뒤이어 실제 Nav2 Action 3개가 SUCCEEDED와 /odom 근거로 종료됐습니다. 따라서 원래 TTY 오류는 **RESOLVED**입니다. `cb11b8d`에서 L0 정적 테스트가 옛 위치를 검사하던 문제도 수정했고 [#45124920240](https://github.com/silverbjin/samsung_AXI/actions/runs/45124920240) L0 **29 PASS**로 확인했습니다.
