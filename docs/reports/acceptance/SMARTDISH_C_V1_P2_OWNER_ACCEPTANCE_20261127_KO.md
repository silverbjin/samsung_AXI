# SmartDish C13 — P2 실제 Frozen ResNet18 단일 학습 Owner 증거 인수 (2026-11-27)

> **최신 판정:** `C_P2_EXECUTION_ACCEPTED_RESEARCH_ONLY`. 단일 frozen-head 학습 실행은 PASS. **성능 적합성 HOLD**, `C_RESEARCH_PILOT_ACCEPTED=false`, `P3_TEST_OPEN_NOT_APPROVED`. P0 42/42·P1 runtime/weight technical PASS 재사용, **재학습 금지**.

## 1. 직접 검증한 제출 원본

- 아카이브 `20261127T004925Z-p2-9db90e52da30.tar.gz` 직접 재계산 SHA256: `914b9ea89c78fb1a4c3cad82c4f2d25869d422e618d477236c89f6ecd30f0516`. 대응 `.sha256` 기록과 동일.
- 크기 1,412 bytes, 일반 증거 파일 8개: `approval_stdout.log`, `approval_stderr.log`, `checkout.log`, `environment.log`, `execution_status.json`, `summary.json`, `train_stdout.log`, `train_stderr.log`; TAR `./` 디렉터리 1개. 안전한 파일 유형/경로. stderr 파일 2개 모두 **빈 파일**.
- `summary.json` SHA256 `945f8f4aeb3b8a8e9cb1873f4353620dbd660765b3eb9688ab234a61f97a3864`; `execution_status.json` SHA256 `de701f9c3735b6830d06abccd6234d6d08ad097f7ed253b582b2a6c525c2a468`.
- `checkout.log`: source commit `9db90e52da3025f548faba28444d0dc777586138`, `C_V1_P2_CLEAN=1`.
- `environment.log`: Python 3.12.3, pip24.0이 `~/.venvs/smartdish-c-v1-py312-cpu`에 존재.
- `execution_status.json`: `exit_code=0`, UTC 완료 `2026-11-27T00:49:33.552504+00:00`, B audit/P0/P1 재실행 false, Test open/P3 evaluation false, A19 NOT_AUTHORIZED, Production Contact HOLD, AI OFF PROTECTED.
- `approval_stdout.log`: `C_P0_RESEARCH_TRAIN_GO`, 비상업 내부 교육·연구/재배포 금지 scope, frozen만 승인, P3 Test 평가 허가 false. P1 plan full SHA 및 ImageNet V1 가중치 full SHA와 기존 봉인 일치.
- `train_stdout.log`: `C_FROZEN_TRAINED` 및 `summary.json`에 기록한 체크포인트 해시·Validation loss 동일.
- **증거 경계:** 원본 체크포인트 `.pt`, 14개 private 이미지/물리 파일, 비공개 승인 JSON은 이 TAR에 들어 있지 않음. Owner 원샷 소스는 checkpoint 저장 후 파일 SHA를 계산하고 요약과 비교하도록 작성되어 있음. **이번 검토자가 체크포인트 바이트 자체를 독립 해시한 것은 아닙니다.**

## 2. 승인된 학습 범위와 실제 로그 교차 검증

| 항목 | 제출 실제 증거 |
|---|---|
| phase | `frozen` |
| Data scope | `PHYSICS_OBSERVED` |
| P1 계획 SHA | `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019` |
| Pretrained weights SHA | `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` |
| train | 11: STABLE 8, UNSTABLE 3 |
| val | 3: STABLE 2, UNSTABLE 1 |
| test | `{}` (학습 집계에 포함되지 않음) |
| seed | 42 |
| validation 선택 | **최소 loss epoch 3** |
| Best validation loss | `0.7452375292778015` |
| Checkpoint SHA256 (Owner 요약) | `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c` |
| test used for training / evaluated | `false` / `false` |
| checkpoint distribution authorized | `false` |
| model accepted / E AI ON | `false` / `HOLD` |

### 실제 학습 지표

| Epoch | Train loss | Train accuracy | Val loss | Val accuracy | Train 정답 개수 | Val 정답 개수 |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0.8826086 | 0.2727273 | 0.8243010 | 0.3333333 | 3/11 | 1/3 |
| 2 | 0.8110948 | 0.3636364 | 0.7778842 | 0 | 4/11 | 0/3 |
| 3 | 0.7492455 | 0.3636364 | 0.7452375 | 0.3333333 | 4/11 | 1/3 |

- 선택 알고리즘은 사전 고정 기준 **최소 Validation Cross-Entropy**를 준수해 Epoch 3 선택 PASS.
- 하지만 Train/Val 분류 정확도가 낮음. 모든 이미지를 `STABLE`로 예측하는 **Train 다수 클래스 기준선 8/11=72.73%, Val 2/3=66.67%**보다 낮음. 이는 단지 참값 분포를 이용한 사후 비교 기준이며, Test 결과나 추가 모델 선택 기준이 아닙니다.
- Val loss는 계속 감소하지만 최종 `0.7452`이고 정확도는 1/3에 머묾. 단지 학습 손실이 감소했다는 이유로 모델의 위험분류가 유효하다고 말할 수 없음.
- 주어진 집계만으로 `UNSTABLE→STABLE` 오류 수, 클래스별 Precision/Recall, threshold0.80 UNKNOWN/coverage 또는 Family별 오차를 계산할 수 **없음**. 예측값/확률 원본이 없으며 Test는 미개봉.
- 데이터 규모 Train11/Val3, 특히 Val UNSTABLE 1장이므로 model acceptance나 주행·적재 안전 일반화 주장 금지. 원인으로 Representation 미적합/표본 과소/클래스 편향 등을 가설로만 볼 수 있고, 현재 증거로 특정 원인 확정 불가.

## 3. 최종 수용 판정

- `P2_FROZEN_TRAINED_AWAIT_C_REVIEW` → 이번 독립 증거 검수로 **`C_P2_EXECUTION_ACCEPTED_RESEARCH_ONLY`**. 학습 실행기/데이터 격리/선택 계약 충족.
- **`C_P2_MODEL_PERFORMANCE_HOLD`**: Val 정확도 33.3% 및 majority 66.7% 대비 미달. 새로운 최소 품질 목표를 사후 학습 허용/재튜닝 기준으로 소급하지는 않음.
- **`P3_TEST_OPEN_NOT_APPROVED`**: Owner가 승인한 것은 P2 연구 학습이었음. Test4를 열지 않았고, 첫 번째 Test를 소비하기 전 모델의 낮은 Validation 성능·연구 목적·해석 한계를 사람 검토로 별도 결정해야 함. 현재 기본 권고는 `P3_HOLD_PENDING_EXPLICIT_SINGLE_TEST_DECISION`.
- 단일 고정 체크포인트/threshold0.80을 유지하고 다시 학습하거나 Test 결과로 파라미터를 재선택하지 않음. 학습 1회 성공에 따라 P2 재실행 권한 없음.
- 연구 모델 출고 `P4_NO_RESEARCH_ACCEPTANCE`, 제품 `E_AI_ON_HOLD`. 기존 AI OFF 3-leg, Data Freeze A18_LAST, A19 NOT_AUTHORIZED, Production Contact HOLD 보존.

## 4. 필요한 후속 작업

- **P3 이전 read-only checkpoint seal**: Owner private 체크포인트 SHA의 직접 재계산, 메타데이터·P1 plan/데이터 scope 검사. 원본 이미지를 열거나 추론을 실행하지 않고 Test lock/승인서도 만들지 않음.
- P3 실제 단일 Test 평가 여부는 **별도 명시적 판단**. 강행 평가한다면 연구용 실패 사례 기록에만 사용하며, 후속 튜닝·반복 테스트·제품 모델 성능 홍보 금지.
- 결과/재검이 필요하면 공개 보관 대상은 이 상세 교육 보고서·집계/해시뿐. private 이미지, 물리 증거, 승인 JSON, checkpoint 바이트는 GitHub에 업로드하지 않음.

## 교육 핵심

**CI PASS ≠ Owner WSL2 학습 PASS ≠ Model Performance PASS ≠ 실제 로봇 안전 PASS**. 특히 작은 Validation 집합에서는 1개 샘플 판정 변화만으로 정확도가 33.3%p 변합니다. 장기적으로 데이터 다양성 부족을 해결하려면 기존 Data Freeze를 깨뜨리는 자동 생산이 아니라 PM Change Request와 독립 검증 계획이 필요합니다.
