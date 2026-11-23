# C06 — B-06 물리 증거 무결성 검증 및 실데이터 전환 사전검사

- **요구사항:** 실제 B 데이터가 출고되면 C를 **더미 실습 없이** 실학습으로 전환. 출고 전에는 데이터 부재를 명확하게 BLOCKED로 기록.
- **작업 환경/기준:** 2026-11-23, `feat/smartdish-c-stability`, 시작 HEAD `a1f2488d40e7d683664a3734b7be9f1f5c361cb8`; B read-only SHA `1bfc19eabe07f2a0ea8c5c8ba3509491c9dd217d` (PR #37).
- **변경:** `ai/evaluation/dataset_contract.py`, `ai/train/check_real_data_readiness.py`, `tests/test_c_stability.py`, `tests/test_c_real_readiness.py`, 이 교육 보고서 및 [C-ISSUE-02](../issues/2026-11-23_C_ISSUE_02_PHYSICS_EVIDENCE_GUARD_EDU_KO.md).
- **판정:** 로컬 데이터 계약 **PASS**, 실제 데이터 학습 **BLOCKED**, Gazebo/WSL2 **NOT_RUN**. GitHub CI 실행 결과는 후속 코드 SHA가 확인된 뒤 기록.

## 1. 왜 지금 이 검사가 필요한가?

B의 이전 수집 버전은 사용자가 문자열로 넘긴 `physics_evidence`를 확인 없이 CSV에 담을 수 있었습니다. B-06에서는 실제 물리 근거 파일이 존재하고 비어 있지 않은지, 이미지 파일과 별개인지 확인하며 SHA256·크기를 기록하도록 개선되었습니다. 그러나 C05는 `capture_config` 안에 `physics_evidence`라는 **문자열이 있는지만** 검사했습니다. C 코드도 최신 B-06 계약에 맞게 파일을 다시 검증해야 배포·학습 결정의 추적성을 보존할 수 있습니다.

## 2. RED → GREEN 재현과 설계 결정

- **RED 근거(수정 전):** C05 ZIP의 실제 `dataset_contract.py`와 당시 테스트를 별도 디렉터리에 복원하여 `python -m pytest -q tests/test_c_stability.py::test_contract_complete_fixture_shape_mock_only` 실행 → `1 passed`. 이때 합성 메타데이터는 `{"physics_evidence":"TEST_ONLY"}`만 가진 상태였고, 실제 근거 파일·SHA는 없었습니다. **해당 불충분한 입력을 받아들이는 것이 결함**입니다.
- **최소 수정:** 실제 데이터 경로(`demo_fixtures=False`)에서 증거 파일 존재, 이미지와의 독립성, 길이, SHA256 일치 여부를 검증합니다. 비정상인 경우 구체적인 `C_PHYSICS_EVIDENCE_*` 오류로 중단합니다. B의 이미지/라벨·기존 S7 원본은 전혀 수정하지 않습니다.
- **GREEN 근거:** `python -m pytest -q tests/test_c_stability.py tests/test_c_mock_pipeline.py tests/test_c_real_readiness.py` → `34 passed` (로컬). 파일 미존재·메타데이터 누락·SHA/크기 변형을 각각 거부합니다.
- **왜 자동 물리 판정을 하지 않나요?** SHA는 전송 뒤 파일이 변경되지 않았다는 **무결성**만 보장합니다. 전도·접촉·낙하 관측과 라벨의 정확성, 촬영·재배포 권한은 B 운영자가 직접 확인해야 하므로 `CONTRACT_READY_HUMAN_REVIEW_REQUIRED`로 명확히 구분합니다.

## 3. 실데이터 대기 상태를 확인하는 명령

```bash
python3 -m ai.train.check_real_data_readiness \
  --split-manifest /path/to/B/ai/data/split_manifest.csv \
  --root /path/to/B --b-ref 1bfc19eabe07f2a0ea8c5c8ba3509491c9dd217d \
  --report /tmp/c-real-readiness.json
```

B 최신 브랜치에서 `split_manifest.csv`는 헤더만 있습니다. 따라서 현재 기대 상태는 `verdict=BLOCKED`, `reason=C_TRAINING_NOT_RUN_NO_REAL_DATA`, **종료 코드 2**입니다. 이 코드는 정상적인 데이터 미준비 신호이지 학습 오류를 덮으려는 무조건 PASS가 아닙니다.

## 4. 근거·검증 경계 / 후속

| 검증 | 관측/상태 | 의미 |
|---|---|---|
| B manifest 실제 행 수 | **0** (GitHub HEAD에서 직접 확인) | 실학습 BLOCKED |
| local C06 계약 검사 | **34 passed** | Python 형식·파일 무결성만 PASS |
| 실제 B 물리 증거 1건 이상 검토 | **NOT_RUN** | B 자료 필요 |
| Pretrained/fine-tune/독립 test | **TRAINING_NOT_RUN** | 실제 데이터 불가 |
| ROS Jazzy / Gazebo 트레이 실영상 | **NOT_RUN** | A 카메라 필요 |

**주니어 체크 질문:** (1) 데이터 행이 있어도 사람 검토 없이 학습 승인하면 안 되는 이유는? (2) 두 파일의 SHA가 같아도 라벨의 물리적 의미는 보장되나요? (3) C가 B 소유 `manifest.csv`를 직접 바꾸면 추적성이 어떻게 깨지나요?

**작업 결과 코드 SHA:** 동일 커밋에 본 보고서 포함. 정확한 GitHub SHA 및 CI URL은 원격 검증 후 기록합니다.
