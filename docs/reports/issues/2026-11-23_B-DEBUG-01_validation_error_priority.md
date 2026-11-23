# B-DEBUG-01 — 라벨 모순과 scene 그룹 모순의 오류 우선순위 충돌

- 2026-11-23 / 작업 컨테이너 Python 3 + pytest 9.0.2 + Pillow 12.3.0
- 상태: **RESOLVED (로컬 동일 테스트 경계)**; 실제 Gazebo **NOT_RUN**
- 기준: S7 main `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`; 수정: 본 파일과 동일 커밋.
- 연관 작업: [B-03](../tasks/2026-11-23_B-03_group_split_handoff.md)

## 현상 / 최초 실패

scene이 한 stack에 속하는지 검사하는 신규 코드 삽입 후, 기존 `test_group_conflict_rejected`가 기대한 오류보다 scene 오류를 먼저 반환하여 실패했습니다.

```text
E AssertionError: Regex pattern did not match.
Expected regex: 'B_STACK_LABEL_CONFLICT'
Actual message: 'B_SCENE_SPANS_STACKS scene_id=scene-STABLE-0'
FAILED tests/test_b_dataset.py::test_group_conflict_rejected
1 failed, 9 passed in 0.25s
```

## 재현/가설/증거

```bash
python3 -m pytest -q tests/test_b_dataset.py
```

`stack_id`가 다른 라벨을 동시에 받는 표본이 `scene_id`도 잘못 공유하는 상황이었습니다. 독립 두 오류 중 scene 검사가 앞에 있어 처음 예외가 우선했습니다. 성능/이미지 파손 문제가 아니며 **검사 순서**가 근본 원인이었습니다.

## 최소 수정 / 동일 경계 재검

`ai/scripts/prepare_dataset.py::validate`에서 **stack_id 양쪽 라벨 모순을 먼저 보고**하고 `scene_id`가 여러 stack에 걸친 모순을 다음으로 보고하도록 블록 순서를 이동했습니다. 오류 분류를 제거하거나 검사 조건을 완화하지 않았습니다.

- 수정 전: `1 failed, 9 passed in 0.25s`
- 수정 후: `10 passed in 0.22s`; 별도 `test_scene_group_leak_guard`도 통과.
- PR Actions Run: NOT_RUN. 수정 후의 동일 CI 경계 검증은 원격 파이프라인 실행 시 추가 가능.

## 교육용 핵심

중복이나 무결성 검사는 오류가 여러 개 동시에 있는 경우 어떤 오류를 먼저 반환할지까지 설계해야 합니다. 한 오류를 고친 뒤 다른 오류가 드러나는 현상은 테스트가 거짓말한 것이 아니라 검증 단계의 순서가 더 상세해진 결과일 수 있습니다. 이런 경우 첫 실패 원본을 남기고 단 하나의 조건 순서를 수정한 뒤 같은 테스트를 재실행하는 것이 안전합니다.
