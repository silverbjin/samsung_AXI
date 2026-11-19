# CI-01 문제 해결 보고서 — ROS 2 환경 설정의 `nounset` 충돌

- 발생일: 2026-11-19 (KST)
- 최초 Run: [GitHub Actions #44443691545](https://github.com/silverbjin/samsung_AXI/actions/runs/44443691545)
- 실패 Job: `L1 build + L2 real Gazebo no-goal smoke`
- 상태: **OPEN — 최소 수정 후 실제 CI 재실행 필요**
- 증거 기준 소스: 원격 HEAD `a11951cc3dbe9e18c8b154d8e8787a09dd6f7dc2`
- 관련 경과 보고: [CI-01](../tasks/2026-11-19_CI-01_actions_nounset_recovery.md)

## 1. 현상·기대 결과

- 기대: Ubuntu 24.04 runner에 Jazzy/Nav2/Gazebo 패키지 설치 → ROS 환경 설정 → colcon 패키지 빌드 → 실제 Gazebo 헤드리스 센서 수신.
- 실제: apt 설치는 정상 종료했지만 `source /opt/ros/jazzy/setup.bash`에서 즉시 실패. **ROS 패키지 컴파일·Gazebo 실행 단계에는 도달하지 못함**.
- 정상 경계: 독립 L0 문법·정적 계약 Job은 SUCCESS.

## 2. 실패 근거·원인 식별

최초 CI 로그에 기록된 오류:

```text
/opt/ros/jazzy/setup.bash: line 8: AMENT_TRACE_SETUP_FILES: unbound variable
Process completed with exit code 1.
```

원인: 워크플로 단계에서 먼저 `set -Eeuo pipefail`을 설정한 상태로 ROS 환경 설정 스크립트를 `source`했으며, ROS 셸 초기화 코드가 설정되지 않은 `AMENT_TRACE_SETUP_FILES`를 참조하면서 Bash `nounset` 규칙에 의해 중단됐습니다. **패키지 설치 실패, Nav2 컴파일 실패, Gazebo 자체 실패가 아닙니다.**

로컬에서 ROS 대신 존재하지 않는 변수를 참조하는 작은 Bash setup 스크립트로 동일 셸 메커니즘을 재현했습니다. `set -u` 상태의 source는 실패하고, 해당 source 구간에서만 `set +u`로 해제한 경우 성공했습니다.

## 3. 최소 수정과 선택 이유

1. `.github/workflows/restaurant-ci.yml`: `source /opt/ros/jazzy/setup.bash` 및 `source install/setup.bash` 주변에만 `set +u` / `set -u` 추가.
2. `scripts/restaurant_demo.sh`: Owner WSL2에서도 동일 위험이 있어 기존 Jazzy·workspace setup 구간만 동일하게 처리.
3. `tests/test_ros_setup_nounset.py`: **RED→GREEN** 소규모 회귀 테스트 1개 추가. 실제 ROS 패키지를 설치하지 않고 `nounset` 충돌 메커니즘과 모든 setup 호출 지점을 확인.

전체 빌드 구조 변경, 무작위 sleep, CI 검증 비활성화, `set -u` 전역 제거는 하지 않았습니다.

## 4. 재검 및 판정

- 로컬 오류 재현 테스트 RED: Guard 전 `Unguarded source .github/workflows/restaurant-ci.yml:64` 확인.
- 로컬 수정 후 `pytest -q tests/test_ros_setup_nounset.py tests/test_static_contract.py`: **6 PASS**.
- Bash 문법 검사, Python compileall: **PASS**.
- GitHub Actions L1·L2 재실행: **NOT_RUN** (새 커밋 push 후 판정 업데이트).
- 최초 실환경 실패 경계가 GREEN으로 재확인되기 전까지 **RESOLVED가 아닌 OPEN** 유지.

## 5. 교육 포인트

ROS 2 패키지 설치가 성공한 뒤 바로 실패했다고 해서 ROS 패키지나 Gazebo를 수정해서는 안 됩니다. 최초 실패가 명령 셸의 환경 설정에 있는지 확인하면 소스 코드·의존성 설치를 건드리지 않고 단일 지점을 수정할 수 있습니다. 개발용 `set -u`는 유용하지만, 외부에서 제공하는 환경 설정 스크립트와 호환되지 않을 수 있으므로 source 시점만 예외 처리하고 즉시 복원합니다.
