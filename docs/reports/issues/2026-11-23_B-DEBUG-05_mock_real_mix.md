# B-DEBUG-05 — MOCK_ONLY 검사 옵션에서 실제 라벨 행과 fixture 혼입 수용

- 최초 실패 환경: Python 3.13.5, Pillow 12.3.0, pytest 9.0.2
- 기준 SHA: B-08 `c9c528072f76b8b2dbc1119ead770d23308ffda0`
- 상태: **RESOLVED (로컬 계약 경계), 원격 CI 후속 확인**
- 연결: [B-09](../tasks/2026-11-23_B-09_mock_real_isolation.md)

## 최초 실패 원본

```text
B09_BEFORE_MIXED_ACCEPTED MOCK_ONLY 7
```

6개의 `CONTRACT_FIXTURE/MOCK_ONLY`와 1개의 테스트용 `GAZEBO_TRAY/PHYSICS_OBSERVED` 메타데이터 행을 함께 준비하였을 때 `validate(..., allow_fixtures=True)`에서 PASS가 나왔습니다. 실제 물리 관측 데이터가 존재했다는 뜻이 아니며 메타데이터 분류 경계 실패를 확인한 재현 실험입니다.

## 원인과 조치

- 원인: `allow_fixtures=True`가 가짜 행을 **추가로 허용**할 뿐, 실제 라벨 행을 거부하지 않았습니다. 보고서는 실행 옵션만 보고 `MOCK_ONLY`라고 기록했습니다.
- 최소 수정: fixture 허용 경로에서 다른 `ground_truth`가 발견되면 바로 `B_FIXTURE_MODE_REAL_DATA_FORBIDDEN`; CSV 스키마·C 추론·모델 가중치는 변경하지 않음.
- 재검: `python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py` → **25 passed in 0.30s**. 혼합 입력과 물리 행 단독 fixture 모드가 모두 거부됨.
- GitHub CI, 실제 Gazebo 트레이 라벨/학습: **NOT_RUN**(문서 작성 시점).

## 교육 포인트

테스트를 통과한 소스가 올바른 원본을 사용했다는 주장은 별도 검증이 필요합니다. 가짜 샘플은 계약 테스트에만 사용하고, 학습 데이터는 물리 관측 및 권리 확인 후 오직 별도 기본 경로로 입수해야 합니다.
