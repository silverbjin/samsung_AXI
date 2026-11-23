# C-ISSUE-01 — 데이터 의존성 차단: 모델 학습 실행 전 fail-fast

- 날짜: 2026-11-23 / 상태: **OPEN / 외부 의존성 BLOCKED**, 수정 결함으로 위장하지 않음
- 관련 작업: [`C01`](../tasks/2026-11-23_C01_TRAIN_EVAL_EDU_KO.md)
- 영향: frozen/fine-tuning 학습 및 독립 test 수치 **NOT_RUN**. ROS 추론 계약 코드는 별도로 개발 가능.

## 1. 현상과 최초 실패

검증 환경: Python 3.13.5, torch 2.10.0+cpu, torchvision 0.25.0+cpu. B 데이터는 별도 Draft PR #37에 있으며 B의 `split_manifest.csv`는 **헤더만** 있습니다. C의 작업 디렉터리에는 아직 B가 병합되지 않아 manifest 자체가 없습니다.

```bash
python3 -m ai.train.train_classifier --phase frozen \
  --out /tmp/should-not-exist.pt --report /tmp/should-not-exist.json
```

실제 최초 실패 핵심 원문:

```text
File "ai/evaluation/dataset_contract.py", line 26, in read_verified_split
    raise ValueError("C_SPLIT_MANIFEST_MISSING")
ValueError: C_SPLIT_MANIFEST_MISSING
```

## 2. 최초 원인 분리

- **확인된 원인**: C 브랜치에 B manifest 없음; B 브랜치에는 manifest 헤더만 있고 유효한 물리 관측 이미지 0건. 학습 실패는 의도한 차단 동작입니다.
- **가설 아님/부정됨**: CUDA 메모리, torchvision 가중치, training loop 문제로 증명되지 않았습니다. 이 예외는 pretrained 모델 로드 전에 발생했습니다.
- **선택한 조치**: 허위 성능을 만들지 않도록 학습을 막고 ROS/core 계약 개발을 진행합니다. B 데이터나 DACON 일반 구조물을 임의로 STABLE 라벨로 치환하지 않습니다.
- **제외한 대안**: 가짜 PNG 6장을 물리적으로 검증된 것처럼 label 처리 후 training PASS 표시하기 — 학습 평가 누수와 안전 오판 위험으로 금지.

## 3. 동일 경계 재검 및 결과

```text
$ python3 -m pytest -q tests/test_c_stability.py
20 passed in 0.15s
$ python3 -m compileall -q ai src/smartdish_ai tests/test_c_stability.py
(exit 0)
```

테스트의 `test_no_real_data_fails_training_contract`는 헤더-only 입력에서 `C_TRAINING_NOT_RUN_NO_REAL_DATA`가 정상 발생함을 입증합니다. **실제 데이터 학습은 시도하지 않았고** 본 문제는 해결(RESOLVED)이 아닙니다.

## 4. 해결 조건/인계

B가 사람 검토 물리 라벨·실제 이미지·원본 SHA와 `stack_id` 기반 독립 train/val/test 및 이용허가를 인계할 것. 그 후 같은 C train 명령으로 재검하고 학습/평가 수치 및 원본 evidence를 별도 보고서에 기록한 뒤 `OPEN→RESOLVED` 판정합니다. A 카메라 실제 트레이 RGB도 후속 별도 경계입니다.

### 교육 포인트

종종 오류를 '고쳐서 PASS'로 만드는 것보다 **의도적인 가드가 정상 작동하며 다음 단계가 실제로 차단됨을 입증**하는 것이 더 중요합니다. 개발자는 의존성 미해결과 코드 결함을 구분해야 합니다.
