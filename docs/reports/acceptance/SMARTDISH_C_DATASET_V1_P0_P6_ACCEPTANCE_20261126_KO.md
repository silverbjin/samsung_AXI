> **2026-11-26 C Owner 독립 P0 증거 수령 후 상태 갱신:** [C_OWNER_P0_EVIDENCE_REVIEW_20261126_KO.md](../reports/acceptance/SMARTDISH_C_DATASET_V1_OWNER_P0_EVIDENCE_REVIEW_20261126_KO.md) 참고. C 원샷 실제 `exit0`, SHA 고정·clean, 42/42 해시 검사 실행 결과 확인. 기존 `HOLD_PRIVATE_42_RECHECK`는 제출 이전의 **과거 상태**입니다. 현재 **`C_P0_CONTRACT_PASS_HUMAN_REVIEW_REQUIRED`**, `training_permitted=false`, **P1 사람 승인·pretrained full SHA/사용권 미완료**, P2/P3/P4 NOT_RUN, Production Contact HOLD, A19 금지, AI OFF 보호 유지.

# SmartDish C Dataset v1 — P0~P6 독립 인수 원장 (2026-11-26)

## 1. 신뢰 경계 / 식별자
- 코드 검증 SHA: `bd0ca4cbb234c753269cf0486827af577fb19a4f` (교육 보고만 별도 문서 커밋).
- 브랜치 `feat/smartdish-c-dataset-v1-pilot`, [Draft PR #58](https://github.com/silverbjin/samsung_AXI/pull/58), base `main@63e147289e307e0b9900ca365e9c4557c5921804`. **미병합**.
- B delivery `f05e663ac0aaf843c544c905ddcc2a0791f741ac`, Owner execution pin `f9ddc56979626d4a78decb04e7b4ca28c3824b09`.
- Dataset version `c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606`, release `2e9bddf2359cca7f0ccbd2f4ca2c2dc8a5704cf3b9a712864243167b31abd756`, manifest `616996e1c7cdd69b6d656ae682ea9536839e15f18a90f86a2b339548fe907769`, split `8a530b6a34788300bb507ea10aafd10a7ab5616a0c0ffc0f87b7ccf79d0db6d5`.

## 2. 실물 증거와 적합성
| Gate | Owner/B 증거 | C 이번 턴 독립 검사 | 판정 |
|---|---|---|---|
| Owner evidence outer SHA | `411d092f4ab9e65ad044c9b1ae73b2f84456cef1730fef35dcff04c6b393b949` | 파일 직접 일치 | PASS |
| Outer `SHA256SUMS` | 15개 | 15/15 재계산 | PASS |
| Nested diagnostics | 6개 | 6/6 재계산 | PASS |
| 첨부 release metadata/등록된 파일 | release registry 42 | **제공된 4개** 직접 확인 | PASS (4/42 범위) |
| Private 이미지/물리/승인 원본 | B Owner 42/42 보고 | **38개 private 파일 직접 재검 불가** | C P0 HOLD |
| frozen Family split/정확 CSV | 승인18(13S/5U), 제외2 | train 8S3U / val2S1U / test3S1U, CSV SHA 일치 | 메타데이터 PASS |
| P0 학습 적합성 | B-Q07 C review HOLD | WSL2 42/42 미실행; 독립 human plan approval 없음 | **C_P0_HOLD_PRIVATE_42_RECHECK** |

B가 수행한 WSL2 Owner Release ACCEPTED를 C 실제 private 42/42 완료로 **표기하지 않습니다**.

## 3. 개발·검수 원장
| 단계 | 상태 | 실제 근거/인수 조건 |
|---|---|---|
| P0 코드/첨부 증거 | PASS 제한 | `ai/train/dataset_v1_gate.py`, 15/15+6/6+4/42 |
| P0 Owner private 42/42 | NOT_RUN/HOLD | immutable WSL2 원샷·출고원본 재해시 필요 |
| P1 사전 계획 | 초안 잠금 / GO 미발급 | `ai/docs/C_V1_EXPERIMENT_LOCK.json`; pretrained full SHA/rights/C 승인 미확정 |
| P2 frozen train11/val3 | **TRAINING_NOT_RUN** | C owner P0, human approval+SHA, weights pin이 먼저 |
| P3 independent Test4 | **TEST_NOT_OPENED** | 단일 checkpoint/threshold 봉인 이후 1회만 |
| P4 research checkpoint | **NO_CHECKPOINT / NO_MODEL_SHA** | C human research acceptance와 test report 필수 |
| P5 public C V1 CI | **51 PASS** | [Run #45784500398](https://github.com/silverbjin/samsung_AXI/actions/runs/45784500398) (code SHA bd0ca4...) |
| P5 existing C contract | PASS | [Run #45784500415](https://github.com/silverbjin/samsung_AXI/actions/runs/45784500415) |
| P5 B regression contract | PASS | [Run #45784500181](https://github.com/silverbjin/samsung_AXI/actions/runs/45784500181) |
| P5 WSL2 owner C | **NOT_RUN** | local `scripts/smartdish_c_dataset_v1_owner_once.sh` no auto-training |
| P6 D/E code handoff | 준비 | 코드/UNKNOWN/직원 승인 계약 전달 가능, E AI ON product HOLD |

GitHub RED [#45784287293](https://github.com/silverbjin/samsung_AXI/actions/runs/45784287293) 49 PASS/2 FAIL (numpy 누락), GREEN [#45784500398](https://github.com/silverbjin/samsung_AXI/actions/runs/45784500398) 51 PASS. 교육용 원인 분석은 `docs/reports/issues/2026-11-26_C_V1_ISSUE_01_TEST_ISOLATION_AND_RELEASE_GUARD_KO.md` 참조.

## 4. 정책·PM 변경 금지
Data Freeze A15 4+A16 8+A18 8 =20 independent layout/6 family; 승인18/5 family, 제외 L18-06/08, 132 near-pair 논의의 연구용 위험 인정. **A19 자동 착수·추가 물리 생산·재분할·라벨 변경·테스트 튜닝 금지**. Production Contact HOLD(Q03), diversity HOLD(Q05), C review Q07 HOLD. Model scope = 정적 실린더 적재 RGB t0 2.0s, world+Y fixed **command torque** 0.12Nm 0.5s; measured wrench/주행 조건 아님. E AI ON 제품 판단/안전 인증 아님. AI OFF 필수 3구간 보호. 추가 생산은 기능 차단 근거와 PM 승인 Change Request 후에만.

## 5. 다음 Owner 절차
1. 정확한 Draft PR code SHA를 고정해 사용자 WSL2에서 `scripts/smartdish_c_dataset_v1_owner_once.sh` 1회 실행. READ-ONLY 42/42 검사만 수행, 최소 evidence TAR+sidecar 생성.
2. **C P0 PASS가 나와도 즉시 train하지 않음**. 사전 plan SHA, pretrained weights 전체 SHA/version/license, CPU/Torch 환경과 C human approval을 별도 봉인.
3. P2 승인 뒤 frozen 1회/val선택 1개, P3 단일 Test 1회, P4 제한 연구용 승인, P6 D/E 검토. Test에 따른 model reselection 금지.
4. 12/7 freeze, 12/8 rehearsal, 12/9 presentation은 PM 확인 전 일정 가정.

**최종:** `C_V1_P0_HOLD_PRIVATE_42_RECHECK`, `TRAINING_NOT_RUN`, `E_AI_ON_HOLD`; `AI_OFF_PROTECTED`, `A19_NOT_AUTHORIZED`, `PRODUCTION_CONTACT_HOLD`.

## 2026-11-27 C09 P1 Owner 도구 오류 원본 수령·최소 수정

- 제출 `20261127T001421Z-p1-17c6db753b52.tar.gz`의 SHA256 `52ed93611104983e7f776e798e992ca0a08b9a2dd71072648e44cd6f1f730998`와 sidecar 직접 일치.
- 정확 실행 코드 `17c6db753b52333b971bfc0b380a3da29b62f8a4`, detached checkout/clean, Python3.12.3, 종료코드 **2**, `p1_report.json` `HOLD / C_V1_TORCH_OR_TORCHVISION_MISSING / ModuleNotFoundError`. 이번 원본만으로 **어느 패키지가 누락됐는지는 알 수 없음**.
- 기존 P0 42/42 결과는 **PASS 유지**, P0 재실행 없음; P1 실물 weight cache SHA·사용권 아직 없음, 연구 학습 GO **미발급**.
- 오류 원인 분류 최소 수정 코드 `9a1f7bb46c91ab7f27727d5ba02bd1db9278a113`; [C 전용 CI #45916029495](https://github.com/silverbjin/samsung_AXI/actions/runs/45916029495) **70 passed**. 공개 fixture-only, Owner의 P1 환경 설치·가중치 인수 PASS가 아님.
- [문제 진단](../issues/2026-11-27_C_V1_ISSUE_02_P1_DEPENDENCY_IMPORT_HOLD_KO.md), [C09 교육 보고](../tasks/2026-11-27_C09_P1_OWNER_DEPENDENCY_HOLD_EDU_KO.md) 참조.
- 현재 상태 **`C_P0_CONTRACT_PASS_HUMAN_REVIEW_REQUIRED / C_P1_HOLD_DEPENDENCY_IMPORT / P2_NOT_RUN / P3_TEST_NOT_OPENED / P4_NO_MODEL / E_AI_ON_HOLD`**. Data Freeze, AI OFF, A19 금지, Production Contact HOLD 지속.

## 2026-11-27 C10 — 다른 WSL2 개발과 독립된 CPU venv 설치·자동 활성화

- 사용자 환경 조회: system Python `torch`/ `torchvision` 모두 **NOT_INSTALLED**, `Pillow=10.2.0`. 기존 P1 `C_V1_TORCH_OR_TORCHVISION_MISSING` 차단 원인 구체화; **P0 42/42 PASS에는 영향 없음**.
- C 전용 설치기 `scripts/smartdish_c_v1_install_cpu_venv.sh`: `~/.venvs/smartdish-c-v1-py312-cpu` 전용, Python3.12, 공식 CPU wheel `torch2.5.1`/`torchvision0.20.1`, `Pillow10.2.0`/`numpy1.26.4`; 잠금/완료 표식/버전검증/설치 TAR+SHA. 시스템 Python/ROS 2를 변경하지 않음.
- `scripts/smartdish_c_v1_p1_pretrained_once.sh` 원샷이 위 **전용 가상환경을 내부에서 자동 활성화**. `TORCH_HOME=~/.cache/smartdish-c-v1/torch`로 공유 캐시와 분리; 미설치·다른 CPU 버전·동시 설치는 fail-fast. 원샷 자체는 install/download 실행 금지.
- 설치 기본값은 wheel만 설치. `--with-weights`는 명시적으로 요청할 때만 공식 `ResNet18_Weights.IMAGENET1K_V1` 가중치를 전용 Torch 캐시에 다운로드·SHA-prefix+full SHA 확인. **가중치 사용권 승인이나 모델 학습 GO가 아님**.
- 개발 코드 SHA `683a682bc1ecf2f6c959b82dd8fda998be8b706f`. CI는 공개 fixture-only이며 **Owner 실제 WSL2 CPU wheel 설치/P1 재검은 NOT_RUN**. [C10 교육 보고서](../tasks/2026-11-27_C10_VENV_AUTO_ACTIVATION_EDU_KO.md).
- 상태 유지: `P0_PASS / P1_HOLD_ENV_INSTALL_NOT_RUN / P2_TRAIN_NOT_RUN / P3_TEST_NOT_OPENED / P4_NO_CHECKPOINT / AI_OFF_PROTECTED / A19_NOT_AUTHORIZED / PRODUCTION_CONTACT_HOLD`.

## 2026-11-27 C11 — WSL2 Owner P1 isolated CPU / pretrained SHA 기술 검증 PASS

- 새 제출 원본 `20261127T003050Z-p1-23e5dcd49361.tar.gz` SHA256 `c346ddae3764198b1aadb878747a2ca4c097535aa54b9c15b504dee3bc1db38a`; sidecar 직접 일치. 고정 C checkout SHA `23e5dcd49361405d2ee53fa379ed7a28ff3ce3c8`, clean1/exit0, stderr 빈 로그, 6개 일반 증거 파일.
- Python3.12.3 / `torch2.5.1+cpu` / `torchvision0.20.1+cpu` / Pillow10.2.0; 공식 ResNet18 V1 가중치 46,830,571 bytes, SHA256 `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` Owner 보고서 수령. P0 report hash `56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0`; 사전 P1 계획 hash `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019`.
- 기술적 결과 **`P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED`**. `pretrained_license_reviewed=false`, `C_research_approval_issued=false`, `training_permitted=false` 지속. P0 42/42 PASS 보존, P1 재설치/재검수 필요 없음.
- [실제 검수/교육 상세](../reports/acceptance/SMARTDISH_C_V1_P1_OWNER_TECH_ACCEPTANCE_20261127_KO.md). **P2 학습·P3 Test·P4 모델 미실행**, E AI ON HOLD, A19 금지, Production Contact HOLD, AI OFF 유지.

## 2026-11-27 C12 — Owner 명시 연구 학습 승인 / P2 one-shot 출고 대기

- **Owner 권한:** 대화에서 연구 학습 명시 승인. 연구·교육 목적 한정, 상업/가중치·checkpoint 재배포/제품 AI ON은 허가 안 됨. 실행 시 명시적인 비상업 내부 연구·교육 scope attestation 필요.
- **P0/P1 재사용:** P0 Owner private42/42, P1 venv+pretrained SHA `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec`, P1 lock `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019`, Plan 변경 없음. 권리/출처 검토 [문서](../reports/acceptance/SMARTDISH_C_V1_RESEARCH_TRAINING_APPROVAL_POLICY_20261127_KO.md).
- P2 전용 `scripts/smartdish_c_v1_p2_frozen_owner_once.sh` SHA 고정 실행기: 기존 C 전용 CPU venv 자동 활성, 원본데이터는 train11/val3만 사용, frozen-head epoch3 batch4 seed42 CPU AdamW1e-4, validation min-CE checkpoint1. 디버깅 TAR/sidecar 자동 생성. 두 번째 학습·Test 평가/원본 재생산 금지.
- Owner의 명시 승인과 WSL2에 생성될 private 승인 JSON은 구별합니다. **P2 학습 아직 NOT_RUN, Test4 밀봉, P4 체크포인트 연구 인수 아직 NOT_RUN**. GitHub fixture-only CI PASS ≠ 실물 학습 PASS. Data Freeze/A19 금지, Production Contact HOLD, AI OFF 그대로.
- [교육 보고](../reports/tasks/2026-11-27_C12_P2_RESEARCH_FROZEN_EDU_KO.md).

## 2026-11-27 C13 최신 P2 Owner 학습 인수 (과거 NOT_RUN 상태보다 우선)

- WSL2 Owner P2 제출 TAR `20261127T004925Z-p2-9db90e52da30.tar.gz`의 SHA256 `914b9ea89c78fb1a4c3cad82c4f2d25869d422e618d477236c89f6ecd30f0516` 및 sidecar 일치. C source `9db90e52da3025f548faba28444d0dc777586138`, checkout clean, `exit0`, stdout `C_FROZEN_TRAINED`, stderr 비어 있음.
- **P2 학습 실행 인수 PASS**: frozen Train11/Val3, Test 미개봉, seed42, Epoch3 `val_loss=0.7452375292778015` 최소 기준 선택, 체크포인트 **Owner 보고 SHA** `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c`. 실제 checkpoint 바이트는 본 TAR 미포함; 별도 WSL2 read-only 봉인 전 직접 SHA 재검 아님.
- **모델 성능 HOLD**: 마지막 Train 4/11=36.4%, Val 1/3=33.3%; STABLE 다수 기준선 Train8/11=72.7%, Val2/3=66.7% 미달. 분류 경향/UNSTABLE 검출 성능·confidence는 집계만으로 판단 불가.
- **P3 Test4 개봉 명시 승인 미발급**. `C_P2_EXECUTION_ACCEPTED_RESEARCH_ONLY`, `C_P2_MODEL_PERFORMANCE_HOLD`, `P3_TEST_OPEN_NOT_APPROVED`, `C_RESEARCH_PILOT_ACCEPTED=false`, `E_AI_ON_HOLD`.
- [C13 증거 기반 인수 보고서](SMARTDISH_C_V1_P2_OWNER_ACCEPTANCE_20261127_KO.md). P2 재학습/재분할/Test 기반 튜닝/A19 금지, Production Contact HOLD, AI OFF 유지.

## 2026-11-27 C14 최신 P3-pretest 실제 Owner checkpoint 기술 인수

- P3 pretest TAR `20261127T010407Z-454600671d21.tar.gz` SHA256 `5874707038d2d74e2f83d0d7370dbed6ed4baf32d12c6d8164aa8357e0f84148` sidecar 일치. Immutable checkout `454600671d21dec78155baddfb528c1505754841`, clean/exit0, report `P3_PRETEST_CHECKPOINT_SHA_PASS_PERFORMANCE_HOLD`.
- 실제 WSL2 private checkpoint SHA `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c` + P2 summary·P1 plan 메타데이터 PASS. **P3 Test authorized=false, opened=false, evaluated=false**. Val1/3 vs majority2/3; 성능 HOLD, P4 미승인.
- 운영 정책 [Agent-first / Owner WSL2 최종 1회](../../policies/SMARTDISH_AGENT_FIRST_WSL2_FINAL_ONLY_POLICY_KO.md): 에이전트 코드·CI·문서·분석 책임, 사용자 WSL2는 private/최종 인수만. 향후 환경 점검 필요시 단일 스크립트+자동 아카이브, **기존 PASS 재실행 불가**. C14 [교육 보고](../tasks/2026-11-27_C14_OWNER_MINIMAL_WSL2_EDU_KO.md).
- AI OFF PROTECTED, A19 NOT_AUTHORIZED, Production Contact HOLD, P3 Test4 미개봉, E AI ON HOLD 지속.

## 2026-11-27 C15 → C16 완료: 1차 Frozen 연구 기술검토 종료, 제품 Pilot HOLD

- P2 원본 집계 SHA `945f8f4aeb3b8a8e9cb1873f4353620dbd660765b3eb9688ab234a61f97a3864`를 재사용한 C15 [실패 원인 분석](../tasks/2026-11-27_C15_P2_FAILURE_FORENSIC_EDU_KO.md): Val 1/3=33.3% < STABLE majority2/3=66.7%; frozen 1,026 trainable head params/총 9 optimizer steps, 이전 t0 RGB의 미래 physics label 예측 여부 미입증. **근본 단일 원인 단정 불가**.
- C16 [기술적 연구 종료/의사결정](../tasks/2026-11-27_C16_RESEARCH_FIRST_PASS_DECISION_EDU_KO.md): `C16_FIRST_RESEARCH_PASS_CLOSED_NEGATIVE_VALIDATION_RESULT`. 첫 Frozen 연구 pass의 **부정적 결과 보존**. `C_RESEARCH_PILOT_ACCEPTED=false`, `P3_TEST_NOT_APPROVED_NOT_OPENED`, `P4_MODEL_HOLD`, `E_AI_ON_HOLD`.
- 다른 실험·데이터 생산·A19·재학습은 신규 PM Change Request + 별도 승인 전 금지. 현재 사용자 WSL2 **추가 작업 없음**. P0/P1/P2/P3-pretest 기술 PASS 보존, Test4 봉인·AI OFF·Contact HOLD 지속.
