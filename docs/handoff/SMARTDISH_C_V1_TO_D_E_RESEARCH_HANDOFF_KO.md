> **2026-11-26 C Owner 독립 P0 증거 수령 후 상태 갱신:** [C_OWNER_P0_EVIDENCE_REVIEW_20261126_KO.md](../reports/acceptance/SMARTDISH_C_DATASET_V1_OWNER_P0_EVIDENCE_REVIEW_20261126_KO.md) 참고. C 원샷 실제 `exit0`, SHA 고정·clean, 42/42 해시 검사 실행 결과 확인. 기존 `HOLD_PRIVATE_42_RECHECK`는 제출 이전의 **과거 상태**입니다. 현재 **`C_P0_CONTRACT_PASS_HUMAN_REVIEW_REQUIRED`**, `training_permitted=false`, **P1 사람 승인·pretrained full SHA/사용권 미완료**, P2/P3/P4 NOT_RUN, Production Contact HOLD, A19 금지, AI OFF 보호 유지.

# SmartDish C Dataset v1 → D/E 제한 연구 파일럿 인계

## 현재 인계 상태 (2026-11-26)

- B Owner release `B_QA06_FINAL_DATASET_V1_RELEASED`는 검증된 **B 출고**입니다. C는 별개 독립 검수를 수행해야 합니다.
- C 첨부 증거 직접 재검: archive `411d092f…` 외부 PASS, 내부15 PASS, 중첩6 PASS, release CSV/JSON/카드/제외 4 PASS, 18행·2제외·split 11/3/4 계약 PASS. **전체 private 42개 파일 직접 검사 미수행; C P0 HOLD.**
- C 실학습 `NOT_RUN`, test `NOT_OPENED_FOR_MODEL_SELECTION`, checkpoint SHA `NOT_AVAILABLE`, `C_RESEARCH_PILOT_ACCEPTED` **미발급**, E AI ON `HOLD`. 이 코드/지침만으로 제품 AI ON 활성화 금지.
- Data Freeze: A15 4+A16 8+A18 8, 20 layout/6 family, 승인18/5 family; L18-06/08 제외. Q03 Contact 생산 HOLD, Q05 다양성 HOLD, Q07 C 검토 HOLD. A19 NOT_AUTHORIZED, 새 물리 실행/임의 재분할/라벨 승격/근접쌍 중복 증식 금지.

## 인계할 계약과 테스트

1. 영상 `/smartdish/tray/image_raw` (`sensor_msgs/Image`, RGB `rgb8/bgr8`), t0=2.0s single RGB; 실제 A 생산은 고정 world +Y 토크 조건의 **정적 시뮬레이션**만 해당합니다.
2. 요청 `/collection/ai_check_request` JSON `{request_id,capture_id}`; 결과 `/collection/stability` JSON `{request_id,capture_id,status,confidence,model_version}`. `STABLE/UNSTABLE/UNKNOWN`. UNKNOWN은 학습 label이 아닌 fail-closed 상태입니다.
3. 모델 미탑재, 이미지 미도착/오래됨, threshold 미달, 오류, 미응답/timeout → **UNKNOWN / 직원 확인 또는 중단**, 승인 없는 다음 `/collection/nav_goal` 발행 금지. D의 상태 전이는 D 소스가 책임지고 C가 Nav2 명령을 직접 발행하지 않습니다.
4. D/E AI OFF 필수 3-leg 시연은 **C 모델·B private 파일 없이** 실행되어야 합니다. 제품 AI ON 병합은 E 실제 ROS/GUI/Owner 별도 인수 뒤 PM 승인 시에만 가능합니다.
5. P1 experiment lock은 `ai/docs/C_V1_EXPERIMENT_LOCK.json`; 이 문서가 테스트 성능과 독립적인 **사전 학습 계획**입니다. P0·가중치 full SHA·C human approval 전 P2 훈련 금지.

## 조건부 최종 인계물 체크리스트

- [x] B Owner archive SHA와 공급원 검증 기록
- [x] 단일 RGB ResNet18 코드 및 MOCK_ONLY contract-only CI
- [x] P0 WSL2 immutable 원샷/진단 아카이브·sidecar 생성기
- [x] Test 재선택/증강/추가 생산 금지 계획
- [ ] C WSL2 private 42/42 검증 원본 보고서
- [ ] Pretrained weights SHA/version/license + P1 human plan approval
- [ ] train/val 선택 모델과 checkpoint SHA
- [ ] 단일 최종 test confusion + risk/UNKNOWN/coverage
- [ ] C research-only model card / approval
- [ ] D/E actual AI ON acceptance + AI OFF regression

현재는 **코드·계약 인계 가능**, `C_RESEARCH_PILOT_ACCEPTED`/모델 출고 불가입니다. 실제 private Dataset v1은 GitHub/공개 CI 업로드 금지. B PR #46은 E 통합 소유, 다른 팀 소스 무단 변경 금지.


## C 코드 검증 인계 증거

[Draft PR #58](https://github.com/silverbjin/samsung_AXI/pull/58) / 검증 C 코드 SHA `bd0ca4cbb234c753269cf0486827af577fb19a4f`, [C V1 CI #45784500398](https://github.com/silverbjin/samsung_AXI/actions/runs/45784500398) 51 PASS, [기존 C contract CI #45784500415](https://github.com/silverbjin/samsung_AXI/actions/runs/45784500415) SUCCESS. **P0 C private 42/42·P2 학습·P3 Test·P4 모델은 아직 HOLD/NOT_RUN**. D/E는 코드 JSON 계약과 UNKNOWN/직원 확인만 통합검토 가능; E AI ON product acceptance는 별도입니다.

## 2026-11-27 C09 P1 Owner 도구 오류 원본 수령·최소 수정

- 제출 `20261127T001421Z-p1-17c6db753b52.tar.gz`의 SHA256 `52ed93611104983e7f776e798e992ca0a08b9a2dd71072648e44cd6f1f730998`와 sidecar 직접 일치.
- 정확 실행 코드 `17c6db753b52333b971bfc0b380a3da29b62f8a4`, detached checkout/clean, Python3.12.3, 종료코드 **2**, `p1_report.json` `HOLD / C_V1_TORCH_OR_TORCHVISION_MISSING / ModuleNotFoundError`. 이번 원본만으로 **어느 패키지가 누락됐는지는 알 수 없음**.
- 기존 P0 42/42 결과는 **PASS 유지**, P0 재실행 없음; P1 실물 weight cache SHA·사용권 아직 없음, 연구 학습 GO **미발급**.
- 오류 원인 분류 최소 수정 코드 `9a1f7bb46c91ab7f27727d5ba02bd1db9278a113`; [C 전용 CI #45916029495](https://github.com/silverbjin/samsung_AXI/actions/runs/45916029495) **70 passed**. 공개 fixture-only, Owner의 P1 환경 설치·가중치 인수 PASS가 아님.
- [문제 진단](../reports/issues/2026-11-27_C_V1_ISSUE_02_P1_DEPENDENCY_IMPORT_HOLD_KO.md), [C09 교육 보고](../reports/tasks/2026-11-27_C09_P1_OWNER_DEPENDENCY_HOLD_EDU_KO.md) 참조.
- 현재 상태 **`C_P0_CONTRACT_PASS_HUMAN_REVIEW_REQUIRED / C_P1_HOLD_DEPENDENCY_IMPORT / P2_NOT_RUN / P3_TEST_NOT_OPENED / P4_NO_MODEL / E_AI_ON_HOLD`**. Data Freeze, AI OFF, A19 금지, Production Contact HOLD 지속.

## 2026-11-27 C10 — 다른 WSL2 개발과 독립된 CPU venv 설치·자동 활성화

- 사용자 환경 조회: system Python `torch`/ `torchvision` 모두 **NOT_INSTALLED**, `Pillow=10.2.0`. 기존 P1 `C_V1_TORCH_OR_TORCHVISION_MISSING` 차단 원인 구체화; **P0 42/42 PASS에는 영향 없음**.
- C 전용 설치기 `scripts/smartdish_c_v1_install_cpu_venv.sh`: `~/.venvs/smartdish-c-v1-py312-cpu` 전용, Python3.12, 공식 CPU wheel `torch2.5.1`/`torchvision0.20.1`, `Pillow10.2.0`/`numpy1.26.4`; 잠금/완료 표식/버전검증/설치 TAR+SHA. 시스템 Python/ROS 2를 변경하지 않음.
- `scripts/smartdish_c_v1_p1_pretrained_once.sh` 원샷이 위 **전용 가상환경을 내부에서 자동 활성화**. `TORCH_HOME=~/.cache/smartdish-c-v1/torch`로 공유 캐시와 분리; 미설치·다른 CPU 버전·동시 설치는 fail-fast. 원샷 자체는 install/download 실행 금지.
- 설치 기본값은 wheel만 설치. `--with-weights`는 명시적으로 요청할 때만 공식 `ResNet18_Weights.IMAGENET1K_V1` 가중치를 전용 Torch 캐시에 다운로드·SHA-prefix+full SHA 확인. **가중치 사용권 승인이나 모델 학습 GO가 아님**.
- 개발 코드 SHA `683a682bc1ecf2f6c959b82dd8fda998be8b706f`. CI는 공개 fixture-only이며 **Owner 실제 WSL2 CPU wheel 설치/P1 재검은 NOT_RUN**. [C10 교육 보고서](../tasks/2026-11-27_C10_VENV_AUTO_ACTIVATION_EDU_KO.md).
- 상태 유지: `P0_PASS / P1_HOLD_ENV_INSTALL_NOT_RUN / P2_TRAIN_NOT_RUN / P3_TEST_NOT_OPENED / P4_NO_CHECKPOINT / AI_OFF_PROTECTED / A19_NOT_AUTHORIZED / PRODUCTION_CONTACT_HOLD`.

## 최신 P1 Owner 인계 — 2026-11-27 (기존 과거 HOLD 문단보다 우선)

- WSL2 전용 CPU venv·Torchvision ResNet18 V1 cache 검수 PASS, 실행 pin `23e5dcd49361405d2ee53fa379ed7a28ff3ce3c8`, 6파일 로그 TAR SHA `c346ddae3764198b1aadb878747a2ca4c097535aa54b9c15b504dee3bc1db38a`.
- torch2.5.1+cpu / torchvision0.20.1+cpu / Pillow10.2.0 / ResNet18 pretrained SHA `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec`. 계획 SHA `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019`.
- P0 42/42 + P1 weights/runtime **기술 PASS**, 그러나 C human research approval/weights license 미승인: `training_permitted=false`. **P2 train, P3 Test, P4 model release NOT_RUN**, D/E AI ON HOLD, AI OFF protected.
- [P1 상세 검토](../reports/acceptance/SMARTDISH_C_V1_P1_OWNER_TECH_ACCEPTANCE_20261127_KO.md). 기존 P0/과거 P1 HOLD 설명은 당시 이력이며 현행 우선 판정이 아님.

## 2026-11-27 C12 — 연구 학습 승인, 제품 인계 불변

- Owner가 연구 모델 **학습 실행**을 명시 승인. P0/P1 PASS 재사용, private P2 frozen-head 1회 원샷 인수 준비. [scope/rights 검토](../reports/acceptance/SMARTDISH_C_V1_RESEARCH_TRAINING_APPROVAL_POLICY_20261127_KO.md).
- 아직 **checkpoint/성능/검증 Test 증거 없음**. E에게 연구용 모델·AI ON 제품 인수 자료라고 홍보하거나 병합하지 않음. D/E는 UNKNOWN/직원 확인 계약과 AI OFF 3구간 유지.
- Test 4개는 P3 별도 승인·단일 checkpoint/0.80 threshold 봉인 전 열지 않음, A19 금지/Production Contact HOLD/AI OFF 보호 지속.
