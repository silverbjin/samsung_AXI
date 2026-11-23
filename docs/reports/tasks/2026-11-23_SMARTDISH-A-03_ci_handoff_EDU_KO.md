# SmartDish A-03 — CI 분리·현장 인계 (개발 경과 보고서)

- 날짜: 2026-11-23 KST
- 브랜치: `feat/smartdish-a-robot` / 기준 S7 main `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`
- 작업 커밋: 본 보고서와 workflow, handoff 문서가 들어 있는 커밋
- 출고 범위: 계약 L0 + ROS 빌드 L1 후보, 기존 S7 코어 수정 0건
- 상태: **L0 25 PASS / L1 ROS build PASS** (원본 SHA `e069a13`), **A-DBG-01 수정 후 L0 26 PASS** (SHA `bae0c36`), 신규 3-leg Gazebo NOT_RUN

## 1. 목표·설계 판단

A 코드가 ROS 2가 없는 PC에서도 계약 검사 가능하도록 L0를 분리했습니다. GitHub Actions ROS Jazzy 컨테이너에서 실제 `colcon build`/패키지 엔트리포인트 검사를 추가했지만, 이를 실제 Gazebo 주행으로 승격하지 않습니다. 기존 S7의 무거운 전체 주행 CI를 불필요하게 재실행하지 않는 것이 MVP 원칙입니다.

## 2. 변경 내역

| 파일 | 기능 | 이유 |
|---|---|---|
| `.github/workflows/smartdish-a-ci.yml` | 독립 A 전용 L0/L1 | 빠른 계약 검증과 ROS 패키지 설치 검증 구별 |
| `docs/handoff/A_HANDOFF.md` | D/E용 토픽·실행·좌표·NO_GOAL 지침 | 통합자가 A 코드를 수정하지 않고 경계를 연결 |
| `docs/DEVELOPMENT_LOG.md` | 교육 보고서 색인 | 개발 이력의 추적 가능성 |

## 3. 검증 명령·예상 결과

```bash
python3 -m pytest -q tests/test_smartdish_a_contract.py tests/test_smartdish_a_package.py
colcon build --packages-select smartdish_robot
ros2 pkg executables smartdish_robot
```

- 기대 L0: 세 쌍의 목적지 계약, 잘못된 입력 거부, null 목적지 실패, 패키지 구조 확인.
- 기대 L1: `smartdish_robot navigation_adapter` 발견.
- **실제 L0/L1 Run/판정:** [#45118875792](https://github.com/silverbjin/samsung_AXI/actions/runs/45118875792) L0 `25 passed in 0.04s`, PASS; L1 `Summary: 1 package finished`, `smartdish_robot navigation_adapter`, `SMARTDISH_A_L1_BUILD_NO_GOAL_PASS`. 이후 [#45119133312](https://github.com/silverbjin/samsung_AXI/actions/runs/45119133312) L0 **26 passed in 0.04s**, L1 재검 진행 중 (소스 코드는 이전 L1 성공 버전과 동일).
- L2 Gazebo 3-leg: `DISH_RETURN`의 실제 map Pose를 현장에서 검증하기 전 **NOT_RUN**.

## 4. 주니어 개발자를 위한 판단·질문

- CI의 Python Mock PASS가 로봇이 움직였다는 근거가 될 수 있습니까? **아닙니다.**
- 왜 S7 Map/Collision Monitor를 복제하지 않았습니까? 이미 검증된 안전 경로의 변경 위험을 줄이기 위해서입니다.
- Goal이 `FAILED`이면 어느 층을 먼저 봅니까? JSON 계약 → Pose/TF → Nav2 Action → 센서/odom 순으로 좁힙니다.
- `DISH_RETURN` null은 버그입니까? **미검증 좌표를 주행시키지 않는 의도적 HOLD 상태**입니다.

## 5. 핸드오프

코드와 노드 실행 명령은 [A_HANDOFF.md](../../handoff/A_HANDOFF.md)를 참조하십시오. 실물 인수 전까지 통합 `COMPLETED`는 달성으로 기록하지 않습니다.
