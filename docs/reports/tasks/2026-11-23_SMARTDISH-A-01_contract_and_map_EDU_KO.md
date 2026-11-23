# SmartDish A-01 — 로봇 목표 계약과 map 좌표 검증 (교육용 개발 보고서)

- 날짜: 2026-11-23 KST
- 상태: **PARTIAL** (코드 구현, 원격 CI 결과는 후속 확인; 실제 DISH_RETURN 주행 NOT_RUN)
- 기준: S7 main `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`
- 작업 브랜치: `feat/smartdish-a-robot`
- 작업 커밋: 이 문서와 `contract.py`, `table_poses.yaml`, L0 tests를 함께 포함하는 커밋
- 요구사항: SMARTDISH_MVP_INTERFACE_CONTRACT_v1.0 / A_robot_v0.3

## 1. 문제 정의 — 왜 좌표부터 검증합니까?

사용자 화면의 T03은 **논리 ID**이고, Nav2 Goal은 `map` 좌표계의 Pose입니다. 기존 `src/restaurant_world/config/tables.yaml`은 World SDF 기준 숫자이므로 Nav2 지도 목표로 복사하면 안 됩니다. 이미 S3에서 검증된 `s3_map_waypoints.yaml`의 `pickup→HOME`, `table_3→T03`만 재사용하고, 새 반납 지점은 **미검증 null**로 두었습니다.

## 2. 변경과 재사용 판단

| 항목 | 구현 | 선택 이유 |
|---|---|---|
| `config/table_poses.yaml` | map 프레임의 HOME/T03/DISH_RETURN | UI 픽셀 및 월드 좌표 혼용 방지 |
| `contract.py` | 3개 leg 조합, JSON 형식, 유한 숫자, 결과 enum 검사 | ROS/Gazebo 없이 오류를 먼저 재현할 수 있는 순수 로직 |
| `tests/test_smartdish_a_contract.py` | 정/오류 입력과 좌표 원본 비교 | 실패 입력이 실제 `goToPose`로 이어지지 않도록 차단 |

복잡한 새 메시지 타입·직접 좌표 변환·Planner 작성은 하지 않았습니다. 기존 S7 지도 및 안전 소스는 수정하지 않았습니다.

## 3. RED → GREEN 교육 시나리오

- RED 입력: `{"request_id":"REQ","leg":"TO_RETURN","destination_id":"T03"}`
- 기대 오류: `INVALID_GOAL_COMBINATION` (구간-목적지 쌍 오류).
- RED 입력: `TO_RETURN/DISH_RETURN` 및 `null` Pose.
- 기대 오류: `UNCONFIGURED_DESTINATION`; 실제 Goal **미전송**.
- GREEN 입력: `TO_TABLE/T03` 및 `TO_HOME/HOME`; 검증된 map-frame 숫자만 반환.

```bash
python3 -m pytest -q tests/test_smartdish_a_contract.py
```

위 출력은 GitHub Actions에서 확인 전까지 **NOT_RUN**입니다. `FakeTask`는 enum 변환의 L0 테스트일 뿐 실제 Nav2 Action 증거가 아닙니다.

## 4. 학습 포인트·증거 경계

- 테스트 코드를 먼저 만들면 목적지 이름 혼동을 로봇 동작 이전에 막을 수 있습니다.
- `map`은 SLAM/AMCL의 지도 프레임이며 SDF World 축과 우연히 숫자가 비슷해도 동일 좌표계가 아닙니다.
- 거짓으로 찍힌 `NAV_RESULT=SUCCEEDED`는 교육이나 인수 증거가 아닙니다.
- 원격 L0, ROS L1, Gazebo L2, WSL2 L3는 각각 분리 판정합니다.

## 5. 다음 작업

A-02는 공식 `BasicNavigator`를 재사용하는 Navigation Adapter를 구현합니다. A-03에서 기존 S7 실행 경로를 확인하며 실제 반납점 접근 좌표의 검증 절차를 제공합니다. 새 `DISH_RETURN`이 `null`이므로 **SmartDish 3-leg L2는 NOT_RUN**입니다.
