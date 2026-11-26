> **2026-11-26 C Owner 독립 P0 증거 수령 후 상태 갱신:** [C_OWNER_P0_EVIDENCE_REVIEW_20261126_KO.md](../reports/acceptance/SMARTDISH_C_DATASET_V1_OWNER_P0_EVIDENCE_REVIEW_20261126_KO.md) 참고. C 원샷 실제 `exit0`, SHA 고정·clean, 42/42 해시 검사 실행 결과 확인. 기존 `HOLD_PRIVATE_42_RECHECK`는 제출 이전의 **과거 상태**입니다. 현재 **`C_P0_CONTRACT_PASS_HUMAN_REVIEW_REQUIRED`**, `training_permitted=false`, **P1 사람 승인·pretrained full SHA/사용권 미완료**, P2/P3/P4 NOT_RUN, Production Contact HOLD, A19 금지, AI OFF 보호 유지.

# SmartDish C — Dataset v1 P0~P6 독립 실행 및 Data Freeze 관리 계획

> **확정 정책:** 본 문서보다 B-QA06·A/B 합의의 Data Freeze·A19 금지·Production Contact HOLD·AI OFF 보호가 우선합니다. 실제 학습 GO는 CI PASS가 아니라 C P0 독립 인수와 P1 사전 계획 봉인 및 사람 검토를 모두 요구합니다.

## 변경 불가 계약

- B delivery: `feat/smartdish-b-real-dataset@f05e663ac0aaf843c544c905ddcc2a0791f741ac`; 실제 Owner 실행 pin `f9ddc56979626d4a78decb04e7b4ca28c3824b09` **별개**.
- B Dataset v1: `c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606`; release SHA `2e9bddf2359cca7f0ccbd2f4ca2c2dc8a5704cf3b9a712864243167b31abd756`; manifest `616996e1c7cdd69b6d656ae682ea9536839e15f18a90f86a2b339548fe907769`; split `8a530b6a34788300bb507ea10aafd10a7ab5616a0c0ffc0f87b7ccf79d0db6d5`.
- A15=4/A16=8/A18=8, 20 layouts/6 families 후보 동결. 사람 승인 18/5 families (STABLE13/UNSTABLE5), L18-06/08 제외. 132 near pairs 승인 판단은 연구 한계·shortcut 위험 제거의 증명이 아닙니다. 추가 A19/QA06 재실행/재라벨·재분할/가공 독립 표본 증식 불가. PM Change Request가 먼저입니다.
- Input=static cylindrical tray RGB(t0=2.0s), world +Y 고정 **명령** 토크 0.12 Nm from2.2s for0.5s, observation until12.3s. *측정 wrench가 아님*. 미래 Pose/ECM/Contact, filename/scene/seed/가족정보는 학습 feature 금지. 주행/다른 외란/다른 식기·제품 안전은 범위 밖.
- Production Contact HOLD, A15/A16 cleanup FAIL12 역사 증거 보존, A18 producer exit8 PASS만 제한적 인정. AI OFF 필수3구간/미탑재 UNKNOWN/직원 확인 유지, E의 실제 AI ON 인수 전 제품 반영 금지.

## P0 — 실제 독립 인수/데이터 계약

1. 제공된 Owner 증거 TAR 외부 `411d092f4ab9e65ad044c9b1ae73b2f84456cef1730fef35dcff04c6b393b949`·내부 15/15·중첩 6/6·첨부 파일 4개 해시 대조. B 기록 `OWNER_RELEASE_ACCEPTED`와 **C 직접 검증** 분리.
2. `ai/train/dataset_v1_gate.py`로 WSL2 **원본 private root에서 registry 42/42** SHA 확인, B/C 기존 `read_verified_split()` 재사용해 RGB PNG224, 독립 물리 증거, 경로 안전, scene/stack 분할 누출 차단. 승인 18, 제외2, 5 family assignment, frozen split 11/3/4 및 label map 동등성 확인.
3. 출력 `CONTRACT_READY_HUMAN_REVIEW_REQUIRED`는 **학습 GO 아님**. 사람 승인 ledger·rights·near-pair 독립성 검토 후 C가 P1 사전 계획을 봉인하고 개별 명시 승인해야 `C_P0_RESEARCH_TRAIN_GO`가 가능합니다. Private root가 없으면 `HOLD_PRIVATE_42_RECHECK`, exit2.
4. **C가 B release(), QA06 audit(), Gazebo 또는 A19을 재실행하지 않습니다.** 실제 이미지/승인파일은 공개 GitHub/CI 업로드 금지.

## P1 — Test 접근 이전의 사전 등록(현재 초안 봉인 후보)

`ai/docs/C_V1_EXPERIMENT_LOCK.json`을 사용합니다. ResNet18 `IMAGENET1K_V1` 고정, 공식 사전학습 가중치 **전체 SHA256/사용권/캐시 바이트를 WSL2 P2 전에 별도 봉인**; 미확보 시 HOLD, random init fallback 금지. CPU·seed42·determinism, 224 RGB+ImageNet normalization, train11/val3 only, train augmentation NONE, frozen-head 3 epochs / AdamW 1e-4 / batch4 / min-val-CE checkpoint 1개 / threshold .80, 최대 frozen 1회. Fine-tune **이번 첫 연구 파일럿에서는 사전 승인하지 않음**; 필요 시 **Test 개봉 이전 별도의 계획 변경과 근거**가 있어야 합니다. 독립 Test 4장은 checkpoint와 threshold 봉인 후 1회만 개봉. 3개 val 중 1건 실수는 33.3%p, U val1은 불확실성 큼.

실제 pretrained full SHA, 최종 C 소스 SHA, 원본 환경, training approval, 데이터 readiness 영수증이 없으므로 **현재 P1 사전 계획은 작성 완료/실행 GO 아님**.

## P2 — GO 조건부 실학습(현재 NOT_RUN)

- B private root에서 C immutable SHA checkout 후 P0 42/42 독립 PASS + C 명시 학습 승인 + pretrained full SHA + P1 plan SHA 기록 이후에만 기존 `ai/train/train_classifier.py --phase frozen`을 1회 호출합니다.
- 학습기에는 train/val만 전달합니다. Test pixel/label을 checkpoint 선택에 전달하거나 보고서에 노출하지 않습니다. `split_manifest.csv` 원본 바이트 불변·가족 분할 고정. Test sha·유효성 독립 검사는 별도 P0 과정입니다.
- 보고서: torch/torchvision/Pillow/Python 실행환경, source pin, dataset/version/split, weights full SHA, metrics/epoch/loss/val, 최종 모델 hash, traceback/최초 실패, private archive.
- 실제 훈련 성공이 없으면 `TRAINING_NOT_RUN` 유지. ML 정확도 목표를 이유로 데이터 재생산 요청 금지.

## P3 — 단일 Test 개봉(현재 NOT_RUN)

1. Train/val에서만 고른 단일 checkpoint SHA + threshold0.80 + plan SHA + C 리뷰 승인을 **먼저** 봉인. Test 4개 단 한 번 측정. 동일 test 결과로 재선택/threshold 변경/추가 fine-tune 금지.
2. Stable/Unstable 행이 참값, 예측 열인 2x2 confusion matrix, positive=UNSTABLE TP/TN/FP/FN, class별 precision/recall/F1, balanced accuracy, UNKNOWN/coverage, `UNSTABLE→STABLE` 위험. Majority STABLE=3/4(75%)는 test 개봉 **이후** 묘사 참고치일 뿐 학습 목표/선택 기준이 아님.
3. N=4 / UNSTABLE n=1은 100% 결과라도 성능 일반화·안전 인증 불가. 결과가 낮거나 근거 불충분하면 AI OFF 보호한 채 `C_RESEARCH_PILOT_HOLD` 종료 가능.

## P4 — 연구용 모델/ROS 계약(현재 CHECKPOINT_NOT_CREATED)

- 기존 `stability_model.py`, `train_classifier.py`, `evaluate.py`, `smartdish_ai` 재사용. 미승인 학습 weight 자체를 **제품 모델로 공개·반입 금지**. Pilot acceptance는 C/E 검수 후 별도 결정. ONNX는 별도 필요성/동등성 없으면 생략.
- `/smartdish/tray/image_raw` → `/collection/ai_check_request` (`request_id`,`capture_id`) → `/collection/stability` (`status`, `confidence`, `model_version`), `UNKNOWN` on model missing/low score/stale/image errors, D timeout·직원 확인, AI OFF 3구간 기본.
- 모델은 Nav2 Goal/`cmd_vel`이나 안전 제어를 발행하지 않습니다. Test raw 결과로 threshold 재튜닝하지 않습니다.

## P5 — 공개 CI/WSL2(현재 P0 부재로 Owner 인수 대기)

- 공개 CI: fixture-only 단위/계약/회귀 + BAD SHA/path/ground truth/rights/split/contact negative cases. 실제 image/evidence 미업로드. **CI PASS ≠ Owner WSL2 PASS**.
- `scripts/smartdish_c_dataset_v1_owner_once.sh`: immutable C SHA **정확 checkout**, clean 확인, private 42개 읽기 전용 검사, **학습 실행 금지**, exit0/2, minimal diagnostic archive+sidecar 자동 생성. 반복시험 금지. P0 이후에만 추가 학습 인수 스크립트를 설계/승인.
- 코드·테스트·디버깅 과정 교육용 보고서를 SHA/Run/한계 구분하여 브랜치에 함께 저장합니다.

## P6 — D/E 인계(인계 문서 준비 / 모델 인계 HOLD)

- E에는 Dataset/plan 코드, C ROS request/response 계약과 offline UNKNOWN 경계를 전달; **실제 checkpoint/성능/WSL2 출고값은 NOT_RUN**. D/E는 mock/UNKNOWN/승인 대기만 독립 개발 가능.
- `C_RESEARCH_PILOT_ACCEPTED`는 P0+P1+P2+P3+P4 및 C 연구 승인 이후에만 부여. **E 제품 AI ON PASS는 별도 E 인수 책임**; C 자체 병합/ON 활성화 금지.
- B PR #46은 E의 통합 경계로 유지. A/B/D/E/main/Platform과 보존된 C 기존 브랜치는 수정하지 않습니다.

## PM 의사결정·일정

12월7일 기능 동결·12월8일 리허설·12월9일 발표는 *가정*이며 PM 확인 필요. 현 시점 `C_P0_HOLD_PRIVATE_42_RECHECK`; C에게 새 생산 요청 권한 없음, A19 금지. User WSL2에서 42/42 증거를 받고 연구 계획/가중치 SHA를 봉인한 후 후속 P2 진행 여부를 재판정합니다.
