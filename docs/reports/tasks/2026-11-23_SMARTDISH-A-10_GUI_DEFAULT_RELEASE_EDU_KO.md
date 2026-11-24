# SmartDish A-10 — WSL2 원샷 기본 GUI 모드 전환·출고 보고서

- 날짜: 2026-11-23 KST
- 대상: `scripts/smartdish_a_wsl2_bootstrap.sh`, `scripts/smartdish_a_wsl2_one_shot.sh`
- 코드 기준: `7d110ece67096151daff7bf351420952b18a9a66`
- 범위: **기본 인자 및 테스트만 변경**, 기존 Nav2/Collision Monitor/운영 map/Goal 규칙 불변
- 인수 근거: [A-09 실제 운영자 WSL2 GUI L3 3/3 PASS](2026-11-23_SMARTDISH-A-09_WSL2_GUI_L3_ACCEPTANCE_EDU_KO.md)

## 1. 변경 요구와 실패 위험

운영자는 한 줄 원샷 실행 시 GUI Gazebo/RViz가 기본으로 표시되길 요구했습니다. 과거에는 부트스트랩과 내부 실행기가 기본 `--headless`였으므로 사용자가 `--gui`를 명시해야 했습니다. 이 문제는 자율주행 로직이 아니라 **진입점 CLI 기본값**에 있으므로 ROS/Gazebo 코드를 변경하지 않고 해결합니다.

## 2. 정책

| 입력 | 부트스트랩→내부 실행기 | 목적 |
|---|---|---|
| 인자 없음 | `--gui` | **새 기본값**, WSLg 창 띄우기 |
| `--gui` | `--gui` | 기존 명시적 GUI 사용자 호환 |
| `--headless` | `--headless` | 디스플레이가 불안정한 시스템용 수동 대체 |
| `--help` | 설명만 출력, NO_GOAL | 빌드·클론 안 함 |
| 잘못된 인자 | FAIL_FAST, NO_GOAL | 우발적 다른 모드 방지 |

`--gui`일 때 WSLg 디스플레이 환경 자체가 없다면 선행 `BLOCKED_NO_GOAL`로 중단하고, 동의 없이 헤드리스 주행으로 자동 전환하지 않습니다. 기존 안전 승인 문구 `YES-SMARTDISH-A-GOALS`는 터미널에서 **실제 사람이** 입력합니다.

## 3. WSL2 복사·붙여넣기 **한 줄**

```bash
curl -fsSLo "$HOME/smartdish_a_wsl2_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/7d110ece67096151daff7bf351420952b18a9a66/scripts/smartdish_a_wsl2_bootstrap.sh" && bash "$HOME/smartdish_a_wsl2_bootstrap.sh"
```

헤드리스로 실행하고 싶다면 위 명령 맨 뒤에 `--headless`를 붙입니다.

이 예제의 다운로드는 **코드 변경이 반영된 고정 SHA `7d110ece...`** 에서 수행합니다. 내부 `git fetch` 후 클린한 기존 `~/samsung_AXI_A`는 Fast-forward만 허용하며 로컬 변경을 지우지 않습니다.

## 4. 수업용 검증/검수 경계

- [`tests/test_smartdish_a_bootstrap.py`](../../../tests/test_smartdish_a_bootstrap.py): 부트스트랩 `MODE=--gui`, 명시적 헤드리스 대체, 실제 TTY/비-WSL 차단.
- [`tests/test_smartdish_a_wsl2_l3.py`](../../../tests/test_smartdish_a_wsl2_l3.py): 내부 원샷 `MODE=--gui`, 잘못된 증거 차단, 인간 승인·안전 경계.
- `bash -n`으로 두 셸 문법 확인, 실제 Jazzy L1로 기존 Adapter 빌드 불변 확인.
- 현장 **A-09 GUI 3-leg 실주행 PASS**를 보존합니다. 단순 기본 인자 수정 때문에 전 과정 실주행을 재실행하지 않습니다.
- D UI`COMPLETED` 검증은 A-10의 일부가 아니며, 별도 E 통합에서 진행합니다.

## 5. 최종 GitHub CI 검증 완료

- [GUI 기본값 적용 + 교육 문서 기준 Actions #45132140083](https://github.com/silverbjin/samsung_AXI/actions/runs/45132140083), CI 소스 SHA `267c9f83ca56ed10eeb3437d5f43cafdf39542d0`.
- L0 **45 PASS**: Bash 두 실행기 `bash -n`, `--help` 기본값 문구, `MODE=--gui` 계약, 수동 `--headless` 대체, 안전 차단, 기존 A 계약 전부 통과.
- ROS Jazzy L1 **PASS**: `Summary: 1 package finished`, `smartdish_robot navigation_adapter`, `SMARTDISH_A_L1_BUILD_NO_GOAL_PASS` 로그 확인.
- 출고 이후 보고서·A→E 인계 계획만 개정. 실행기 기본값 코드는 검증된 SHA `7d110ece...`와 동일.
- 현장 실제 GUI L3는 **A-09 이전 운영 코드에서 3/3 PASS**. 후속 변경은 CLI 기본값·보고서뿐이므로 실물 재주행은 생략. D 통합 L3는 NOT_RUN.
