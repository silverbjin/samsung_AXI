# SmartDish C — Dataset v1 Frozen ResNet18 모델 카드 (최종 연구 보고)

**문서 버전:** 2026-11-27 / **분류:** 내부 교육·연구 성과 요약 (공개 코드·집계만, 체크포인트 비공개)

## 1. 판정

| 구분 | 상태 |
|---|---|
| 모델명 | `SmartDish C Dataset v1 ResNet18 frozen-head` |
| 첫 실험 | **완료**: 학습 실행/데이터 계약/체크포인트 원본 봉인 기술 PASS |
| 연구 성능 | **HOLD_NOT_ACCEPTED**; `C_RESEARCH_PILOT_ACCEPTED=false` |
| 배포·상품화 | **NOT_APPROVED**; `E_AI_ON=HOLD` |
| Test 4건 | **NOT_OPENED / NOT_EVALUATED / NOT_AUTHORIZED** |
| 연구 권리 | 내부 비상업적 교육·연구만 검토; 가중치/체크포인트 재배포 불승인 |

본 모델은 **적재 안정성 예측 제품**, **로봇 주행 안전 인증**, **Contact 물리 계측기** 또는 **실물 환경 일반화 모델**로 사용하도록 승인되지 않았습니다.

## 2. 연구 목적 및 출력 계약

- 질문: 트레이 위 적재물이 외란을 받기 전 `t0=2.0초` 단일 RGB 이미지로, 이후 고정 Gazebo 물리 시험의 `STABLE`/ `UNSTABLE`을 예측할 수 있는가?
- 입력: 트레이 전용 224×224 RGB PNG, EXIF transpose→RGB→센터 정사각 `ImageOps.fit`→ImageNet mean/std normalize.
- 출력 후보: `STABLE` 또는 `UNSTABLE`; `UNKNOWN`은 학습 클래스가 아니라 런타임 실패/저신뢰·데이터 미준비 시 안전한 제어 상태.
- ROS 2 C 토픽 계약: `/smartdish/tray/image_raw`, `/collection/ai_check_request` (request_id/capture_id), `/collection/stability` (status/confidence/model_version); C는 Nav2/CM/`cmd_vel`을 발행하지 않음. 제품 AI OFF는 변경 없음.

## 3. 데이터 소유권·프로토콜

- 출처: B QA06 Dataset v1 **사람 승인 18건**, 제외 2건, 5개 독립 Family, `PHYSICS_OBSERVED`. 고정 world +Y 토크 `0.12Nm/0.5s` 시뮬레이션 증거에 종속된 결과이며 실제 상대힘/안전 인증을 의미하지 않음.
- 동결된 split: Train **11**(STABLE 8/UNSTABLE 3), Validation **3**(STABLE 2/UNSTABLE 1), Test **4**(STABLE 3/UNSTABLE 1) — **Test 원본·개별 예측은 개봉하지 않음**. 실제 데이터·approval JSON·체크포인트 bytes는 WSL2 private 보관.
- B Dataset Version SHA `c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606`; C P0 원본 독립 42/42 검증 PASS.
- 한계: N=18, Train/Val의 매우 작은 클래스별 독립 표본, 동결 Family 및 근접쌍, 단일 외란 방향·물리 환경. 자연 현실 분포의 평가 데이터가 아님.

## 4. 모델/재현 계약

| 항목 | 설정 |
|---|---|
| backbone | TorchVision `ResNet18_Weights.IMAGENET1K_V1`, **frozen**, BN eval |
| head | `Linear(512, 2)` / 학습 파라미터 1,026 |
| CPU 전용 환경 | Ubuntu 24.04 WSL2, Python 3.12.3, torch 2.5.1+cpu, torchvision 0.20.1+cpu, Pillow 10.2.0 |
| 학습 | AdamW, lr 0.0001, batch 4, epochs 3, seed 42, no augmentation |
| 모델 선택 | Validation Cross-Entropy 최소: Epoch 3 |
| 사전 선언 임계값 | confidence 0.80 (Test에서 조정하지 않음) |
| 사전학습 가중치 SHA | `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` |
| 실험 계획 SHA | `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019` |
| 비공개 체크포인트 SHA | `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c` |

P0/P1 증거를 재사용하며 **최초 P2 1회만 학습**. 원샷 P2 SHA `9db90e52da3025f548faba28444d0dc777586138`. Private P3 pretest에서 체크포인트 원본 바이트 SHA 및 메타데이터 확인 PASS. **C 모델 성능 승인과 별개**.

## 5. 실제 P2 결과 (추가 실험 아님)

| Epoch | Train 누적 CE | Train 누적 정확도 | Val CE | Val 정확도 |
|---:|---:|---:|---:|---:|
| 1 | 0.8826 | 3/11 (27.3%) | 0.8243 | 1/3 (33.3%) |
| 2 | 0.8111 | 4/11 (36.4%) | 0.7779 | 0/3 (0.0%) |
| 3 | **0.7492** | **4/11 (36.4%)** | **0.7452** | **1/3 (33.3%)** |

사전 등록한 최소 Val CE 기준 Epoch 3 선택은 **계약 준수**입니다. 그러나 Validation 1/3(33.3%)으로 STABLE 상수 예측의 사후 다수 클래스 기준선 2/3(66.7%)보다 낮습니다. Train 4/11은 훈련 중 미니배치 누적 로그로서 최종 체크포인트의 전체 Train 재추론 결과와 동일하다고 주장하지 않습니다. 단순 다수 클래스 기준은 원래 실험 선등록된 품질 임계값이 아니라 결과 해석용 비교입니다.

**집계만으로 알 수 없는 것:** UNSTABLE→STABLE 위험 오류 건수, 클래스별 precision/recall, calibrated confidence, 임계값 0.80에서 UNKNOWN/coverage, Family별 오차, Test 정확도·Macro-F1. 누락된 수치를 만들어내지 않습니다.

## 6. 적합성·위험·편향

- **검증된 미달:** Validation 정답 1/3, 다수 클래스 기준선 대비 부족. 단지 loss가 감소한 것으로 안전분류 성능을 입증할 수 없음.
- **원인 가설 (미확정):** 학습 표본·클래스 비율, frozen 1,026개 head/총 9 optimizer step, 정적 t0 영상에서 미래 contact 결과 예측의 가능성, center crop 정보 손실, Family 유사도·shortcut.
- **배포 위험:** UNSTABLE을 STABLE로 잘못 승인하는 경우 이후 로봇 임무를 잘못 진행할 수 있음. C17 제품 SHA allowlist gate는 `PRODUCT_APPROVED_CHECKPOINT_SHA256=None`으로 기본 로딩을 막고 ROS는 `UNKNOWN`/직원 확인으로 후퇴.
- **사용 권리 제한:** TorchVision BSD 소스 이용조건과 pretrained ImageNet 가중치/데이터 권리는 동일하지 않음. 현재는 명시적 비상업 내부 교육·연구 및 파생 가중치 비공개만 보수적으로 검토. 법률적 상업 이용권은 확인·허가하지 않음.

## 7. 연구/제품 인수 결정

- C15: `C15_EVIDENCE_DIAGNOSIS_COMPLETE_PERFORMANCE_HOLD`.
- C16: `C16_FIRST_RESEARCH_PASS_CLOSED_NEGATIVE_VALIDATION_RESULT`.
- `P3_TEST_OPEN_NOT_APPROVED`; 파일럿 `HOLD_NOT_ACCEPTED`; D/E AI OFF **이미 L3 PASS**, 추가 WSL2 재실행하지 않음.
- 제품 및 파일럿 checkpoint 배포 **금지**. 사람의 명시적 승인 없는 fine-tune, 추가 P2 학습, A19 신규 물리 데이터 생산, Test 개봉, AI ON은 하지 않음.
- 향후 **C20 GitHub CHANGE REQUEST #59**에서 새 실험의 데이터/GT·시점·평가 프로토콜을 사전 설계하고 별도 승인. **C20 이슈 생성 자체는 연구 GO가 아님.**

## 8. 추적 참조

- [C15 원인 분석](https://github.com/silverbjin/samsung_AXI/blob/feat/smartdish-c-dataset-v1-pilot/docs/reports/tasks/2026-11-27_C15_P2_FAILURE_FORENSIC_EDU_KO.md)
- [C16 기술 결산](https://github.com/silverbjin/samsung_AXI/blob/feat/smartdish-c-dataset-v1-pilot/docs/reports/tasks/2026-11-27_C16_RESEARCH_FIRST_PASS_DECISION_EDU_KO.md)
- [C P2 실제 Owner 인수](https://github.com/silverbjin/samsung_AXI/blob/feat/smartdish-c-dataset-v1-pilot/docs/reports/acceptance/SMARTDISH_C_V1_P2_OWNER_ACCEPTANCE_20261127_KO.md)
- [D/E AI OFF main E L3 인수](https://github.com/silverbjin/samsung_AXI/blob/main/docs/reports/integration/SMARTDISH_MVP_FINAL_ACCEPTANCE_KO.md)
- [C 연구 브랜치 PR #58](https://github.com/silverbjin/samsung_AXI/pull/58), [차기 v2 연구 Change Request #59](https://github.com/silverbjin/samsung_AXI/issues/59)
