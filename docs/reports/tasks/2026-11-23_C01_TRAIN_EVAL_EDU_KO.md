# C01 — B 데이터 계약 기반 ResNet18 학습·독립 평가 실행기 개발 보고

- 날짜: 2026-11-23 / 상태 **PARTIAL (코드 L0 확인; 실제 데이터 학습 BLOCKED)**
- 저장소/기준: `silverbjin/samsung_AXI`, `main@2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`
- C 작업 브랜치: `feat/smartdish-c-stability`. **C01 최초 코드+보고서 SHA:** `d6de15d361f890e91d89e9e649268a962b8636b4` (동일 커밋). [Draft PR #39](https://github.com/silverbjin/samsung_AXI/pull/39).
- 이전 단계 미검증: B PR #37에 manifest 헤더만 존재; 실제 물리 라벨 0건; S7 `STACKED`는 안전성 정답이 아님.

## 요구사항 → 구현 → 검증 근거

| 요구사항 | C 코드 | 로컬 검증 | 실제 데이터 검증 |
|---|---|---|---|
| B 11열 스키마/이미지 SHA/권리/물리근거 검사 | `ai/evaluation/dataset_contract.py` | `tests/test_c_stability.py`, synthetic metadata contract만 | BLOCKED |
| train/val/test 및 stack_id 누수 확인 | `read_verified_split()` | 누수·중복·라벨 오류 음성 테스트 | BLOCKED |
| pretrained baseline 1종 / Fine-tuning 1회 | `ai/train/train_classifier.py` | 문법 검증; 학습 미실행 | TRAINING_NOT_RUN |
| 독립 test Accuracy/F1/Confusion Matrix | `ai/train/evaluate.py` | 계산 함수 단위 테스트만 | NOT_RUN |
| weights와 전처리 기록 | `ai/evaluation/stability_model.py`, MODEL_CARD | import/설정 parity 검증 | weights 미생성 |

## 설계 결정을 내린 이유

DACON 공유 게시물 제목은 `Multi-View ResNet`이지만 식기 트레이 시점은 A가 **단일 선택형 RGB**로 계약했습니다. 모델 수를 늘리면 데이터 확보와 인수 문제가 가려지므로 ResNet18 1종에 frozen head와 마지막 block fine-tune 두 단계로 제한했습니다. test 누수와 가짜 라벨 사용은 수치가 좋아 보여도 교육/실무에서 잘못된 결론을 낳으므로 학습 전에 엄격히 차단합니다. 데이터 없이 random image로 학습 성공/성능을 꾸미는 대안은 채택하지 않았습니다.

## 실행 증거 (로컬 격리 개발 환경)

```text
python=3.13.5 torch=2.10.0+cpu torchvision=0.25.0+cpu Pillow=12.3.0 pytest=9.0.2
$ python3 -m compileall -q ai src/smartdish_ai tests/test_c_stability.py
$ python3 -m pytest -q tests/test_c_stability.py
....................                                                     [100%]
20 passed in 0.15s
C_MODEL_TRAIN_RUNTIME_PREPROCESS_PARITY_PASS
```

이 20개는 C01+C02 공유 L0 계약 테스트 전체 건수입니다. 데이터·GPU·ROS/Gazebo 실동작이나 실제 accuracy는 검증하지 않았습니다. 학습 실행을 억제한 부재 예시는 [`C-ISSUE-01`](../issues/2026-11-23_C_ISSUE_01_B_DATA_BLOCKED_KO.md) 참조.

## 후속 작업

B의 실제 train/val/test 및 사용권 확보 → frozen 1회 → fine-tune 1회 → independent test(최종 model에 1회) → 모델 SHA 기록 → C02 ROS 노드 로드. 목표 시연은 AI OFF가 우선이며 실데이터 전에는 C의 숫자 정확도 공란을 유지합니다.

### 주니어 복습

- 왜 `STACKED` 분류기를 `STABLE` 분류기로 이름만 변경하면 안 될까요?
- 같은 `stack_id`를 train과 test에 넣으면 어떤 종류의 평가 오류가 발생할까요?
- 독립 test를 threshold 튜닝에 반복 사용하면 어떤 정보 누출이 생길까요?
