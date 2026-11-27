# C15 — Frozen ResNet18 첫 학습 실패 원인 분석 / 교육용 디버깅 (2026-11-27)

> **결론:** `C15_EVIDENCE_DIAGNOSIS_COMPLETE_PERFORMANCE_HOLD`. **정량적 성능 미달 현상은 확인**, 정확한 단일 원인은 `UNDETERMINED`. 현행 첫 실험은 재학습하지 않으며 P3 Test도 개봉하지 않음.

## 1. 증거 및 코드 경계

- 근거 원본: Owner P2 `20261127T004925Z-p2-9db90e52da30.tar.gz` SHA256 `914b9ea89c78fb1a4c3cad82c4f2d25869d422e618d477236c89f6ecd30f0516`, 실제 내부 `summary.json` SHA256 `945f8f4aeb3b8a8e9cb1873f4353620dbd660765b3eb9688ab234a61f97a3864`. 본 작업은 **이 8개 로그 파일의 확인된 집계**만 공개 요약 JSON으로 복사. private PNG, physics evidence, per-sample probabilities, 승인 원본, checkpoint bytes는 별도 분석하지 않음.
- Owner P3-pretest checkpoint SHA·metadata PASS `P3_PRETEST_CHECKPOINT_SHA_PASS_PERFORMANCE_HOLD`, `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c`. 실험 원본 SHA는 고정; P2 재실행·P3 Test 접근 없음.
- 코드: `ai/evaluation/dataset_contract.py`의 `training_only=True`가 Test를 row 목록에서 제외한 후 이미지 검증, 실제 물리 evidence 독립 SHA 및 `stack_id` split 누출 방지 확인. `ai/evaluation/stability_model.py`는 EXIF 보정→RGB→224 정사각 `ImageOps.fit`→ImageNet normalize. `ai/train/train_classifier.py`는 ResNet18 frozen backbone/BN eval, 512×2+2=**1026개 fc trainable weights** (유지되는 코드 그대로), `batch4`일 때 epoch당 `ceil(11/4)=3` step, 총 **9 optimizer steps**, AdamW lr1e-4/3 epochs. `val CE`가 가장 낮은 Epoch3 checkpoint 선택.
- `ai/docs/C_V1_EXPERIMENT_LOCK.json`은 변경하지 않음. 여기서 `PREDECLARED_NOT_APPROVED_TO_TRAIN` 상태문구는 기존 사전 등록 당시 provenance이며, 실제 C 학습 승인은 별도 private Owner 파일로 발급받아 1회 사용했음.

## 2. 관찰·계산 (Owner 결과 이상 과장 금지)

| Epoch | Train CE | Train 정답 | Validation CE | Validation 정답 |
|---|---:|---:|---:|---:|
| 1 | 0.8826086 | 3/11 | 0.8243010 | 1/3 |
| 2 | 0.8110948 | 4/11 | 0.7778842 | 0/3 |
| 3 | 0.7492455 | 4/11 | 0.7452375 | 1/3 |

- Train Epoch3 accuracy `36.36%`, Val Epoch3 `33.33%`. 사전 지정 loss 최솟값 `0.7452375292778015` at Epoch3; 선택 절차 올바름.
- 다수 클래스 `STABLE` 상수 예측의 사후 비교: Train `8/11=72.73%`, Val `2/3=66.67%`. **모델은 둘 다 이 단순 기준보다 낮음.** 이 기준은 새 학습 알고리즘 선택/공식 acceptance threshold로 사후 적용하지 않음.
- Loss 감소와 정확도 저하/정체는 동시에 일어남. **Loss 감소 = 학습 신호 변경**이지 분류 안전성 입증 아님. 소수 Validation N3에서 한 건 차이는 `33.3%p`.
- 추가 주의: Train CE/accuracy는 각 mini-batch의 **optimizer.step 전/중 로그를 epoch 내 누적**한 값. 최종 선택된 checkpoint를 Train 11개에 대해 별도로 사후 추론한 수치가 아니므로 checkpoint 자체의 정확도를 `4/11`로 단정하는 표현을 피함. Validation은 해당 epoch의 가중치로 추론한 집계이며 1/3은 확인됨.

## 3. 근본 원인: 검증된 현상 vs 미검증 가설

| 구분 | 관찰/코드 근거 | 원인 확정 여부 |
|---|---|---|
| **확정된 결과** | Val1/3, STABLE 다수 기준2/3, Train mini-batch 누적4/11 | **성능 근거 부족 확정** |
| **표본·통계 해상도** | Train11/Val3, Validation UNSTABLE 1개, Family 기준 split (Train F3/F4, Val F1) | **측정 한계 확정** |
| 최적화 부족 | frozen 1,026 trainable params / 9 optimizer steps / 3 epochs / CE 감소 | 원인 후보, **미확정** |
| 입력-정답 표현 가능성 | RGB는 외란 전 t0=2.0s, 라벨은 이후 고정 world+Y 명령 torque 결과 관찰 | 예측 가능성 미입증, **인과 원인 미확정** |
| 전처리 cue 손실 | `ImageOps.fit`은 정사각 cropping 가능, 단일 프레임 224 RGB 사용 | 원인 후보, 원본 픽셀 미분석 |
| 데이터 다양성·shortcut/near-pair | 5 Family/18 승인, 132 near pairs 검토 이력, train/val 다른 Family | 위험 잔존, 실제 shortcut 원인 미증명 |
| Class imbalance | Train STABLE 8:3 / Val 2:1 | 위험 요인, 성능 저하 원인 미분리 |

- 근거 부족: `UNSTABLE→STABLE` 거짓 안전 판단, 클래스별 confusion/recall, confidence `>=0.8` UNKNOWN/coverage, Family별 개별 오류, 입력 모양/색 shortcut은 **집계 보고서만으로 계산 불가**. 이를 특정 원인이라 단언하지 않음.
- `torchvision ResNet18 pretrained` import/weight/cache 결함은 P1 SHA와 C P2 실제 `exit0`로 기존 설치 장애와 분리됨. `train_classifier.py`의 frozen BN eval도 코드 경로로 확인. 새로운 bug라고 주장하거나 원인 근거 없이 모델을 재학습하지 않음.

## 4. 판정/개발 산출물

- `ai/docs/C_V1_P2_AGGREGATE_EVIDENCE_LOCK.json`: 공개 가능 최소 집계. Test N4 **존재만** 기록, 픽셀/라벨/예측값 없음.
- `ai/train/c15_aggregate_diagnostic.py`: stdlib-only 사전 데이터 hash/검증 + 정량 분석, **모델 inference/training/evaluate import 없음**.
- `tests/test_c15_aggregate_diagnostic.py`: 수치/해시/보호 계약 변조에 대한 synthetic-only unit tests.
- 이번 분석의 기술 진단과 부정적 연구 결과는 교육용 회고·후속 C16 결정 근거로 보존. **P2 모델 성능 HOLD / P3 TEST CLOSED / P4 NOT_ACCEPTED / E AI ON HOLD** 유지.

## 5. RED → GREEN 교육 관점

문제는 코드 예외가 아니라 **성공한 학습 실행의 부정적인 성능 근거**였습니다. 먼저 이미 통과한 설치·원본 SHA를 재검하지 않고, checkpoint나 private RGB가 불필요한 집계 분석으로 진단 범위를 제한했습니다. 이 방식은 Test4를 소비하는 사후 튜닝을 방지하며, 원인 가설을 확정된 장애로 오해하지 않게 합니다.

추가 실험을 하고 싶다면 기존 v1 frozen 1회 계약을 수정하는 대신 독립 계획·PM Change Request·권리 검토 및 새 사전 등록이 필요합니다. **현재 C15은 실험 반복을 승인하지 않습니다.**

## CI actual result and verification boundary (2026-11-27)

- C15 commit `f3b3e874c6e7476cbbcbe75f9ed18db22f7052d8`: [Dataset v1 public contract #45921692273](https://github.com/silverbjin/samsung_AXI/actions/runs/45921692273) **172 passed**, [C L0 #45921692265](https://github.com/silverbjin/samsung_AXI/actions/runs/45921692265) SUCCESS, B CI SUCCESS.
- C16 commit `b57645574595d1f9742aff514d45ca7f596a6c12`: [Dataset v1 public contract #45921792047](https://github.com/silverbjin/samsung_AXI/actions/runs/45921792047) **184 passed**. C15/C16 pure stdlib `--report` generated in GitHub fixture-only CI. [B dataset contract #45921792073](https://github.com/silverbjin/samsung_AXI/actions/runs/45921792073) SUCCESS.
- These results mean **static aggregate evidence-review/contract-only CI PASS**. Private original PNG, WSL2 owner training, checkpoint inference and Test4 **NOT_RUN here**; reuse previous owner P0/P1/P2/pretest technical PASS. Model performance and C research pilot acceptance remain HOLD.
