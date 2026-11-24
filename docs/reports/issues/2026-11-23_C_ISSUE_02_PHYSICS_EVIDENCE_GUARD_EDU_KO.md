# C-ISSUE-02 — 물리 증거 경로 문자열만으로 실데이터 계약 통과 가능

- 상태: **로컬 동일 경계 RESOLVED / 원격 L0 회귀 PASS**, 2026-11-23
- 대상: `ai/evaluation/dataset_contract.py`, 이전 C05 기준 SHA `a1f2488d40e7d683664a3734b7be9f1f5c361cb8`
- 책임 영역: B 데이터 검증(C read-only 수신), 모델/ROS/Nav2 자체 결함 아님.

## 현상 → 재현 → 첫 실패 지점

B-06에서 물리 관측 파일의 존재·SHA256·size를 계약에 추가했지만, C05는 `elif not cfg.get("physics_evidence"):`로 단순 문자열 존재만 확인했습니다. 존재하지 않는 `TEST_ONLY` 경로도 데이터 스키마 통과가 가능하여, 뒤이은 실제 학습 실행이 근거 없는 라벨을 받아들일 여지가 있었습니다.

원본 C05 ZIP에서 변경 전 코드와 테스트를 격리해 다음을 실행했습니다.

```text
$ python -m pytest -q tests/test_c_stability.py::test_contract_complete_fixture_shape_mock_only
1 passed in 0.07s
```

이 테스트의 입력 `capture_config={"physics_evidence":"TEST_ONLY"}`는 실제 파일 없이 통과했습니다. 테스트가 **PASS한 사실 자체가 부족한 검증 조건을 보여주는 RED 증거**입니다. 기존 B 실물 데이터는 0건이므로, 어떤 실제 샘플도 사용하지 않았습니다.

## 원인·최소 수정 및 재검

- 원인: C가 B-06의 업데이트된 `physics_evidence_sha256`, `physics_evidence_size_bytes` 계약을 따라가지 못함.
- 수정: real 경로에서 증거 파일 실재·비공백, 이미지와 다른 파일, 크기 및 sha256 일치를 확인. `MOCK_ONLY` 생성기 경로는 변경하지 않음.
- 재검: `python -m pytest -q tests/test_c_real_readiness.py::test_missing_evidence_file_rejected tests/test_c_real_readiness.py::test_evidence_corruption_and_size_rejected` → `2 passed in 0.07s`; 전체 C 테스트 34 PASS.
- 원격 CI, 실제 물리 학습·Gazebo/WSL2는 **NOT_RUN**으로 분리. 실제 자료가 오면 새 데이터의 경로·SHA·사용권은 다시 사람 검토 필요.

## 왜 이것이 중요할까요?

CSV의 `PHYSICS_OBSERVED` 문자열은 훈련 코드가 검사할 **주장**이지 물리적 사실 그 자체가 아닙니다. 독립 기록의 존재와 파일 무결성을 자동 확인하고 사람이 라벨을 승인하는 두 단계를 분리해야, AI가 잘못된 `STABLE` 결과를 정상 주행 허가로 전파할 위험을 줄일 수 있습니다.

## 원격 CI 회귀 완료 (2026-11-23)

- 고정 코드 SHA `55ae46a36c637c352d8c851614ee4a650f6c2939`; [Push CI #45125969828](https://github.com/silverbjin/samsung_AXI/actions/runs/45125969828), [PR CI #45125976380](https://github.com/silverbjin/samsung_AXI/actions/runs/45125976380), 각각 `40 passed in 0.27s`. `C_PHYSICS_EVIDENCE_FILE_MISSING`, SHA/크기 mismatch 방어 테스트 통과. **C-ISSUE-02 L0 계약 결함 RESOLVED**.
- 실물 물리적 의미의 검증은 자료가 없어 **NOT_RUN**; 확인한 것은 파일 계약의 위반 검출입니다.
