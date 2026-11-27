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
