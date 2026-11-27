# C19 — SmartDish C 최종 안전 출고 / PR 분리 인수 원장 (2026-11-27)

> 현재 기록은 **C17/C18 범위에 한정된 안전 출고 후보**입니다. GitHub의 해당 최종 HEAD CI·PR·main 병합 여부는 작업 종료 시 실제 API에서 확인하고 갱신합니다.

## 1. 왜 C Draft PR #58 전체를 main에 병합하지 않는가?

- [Draft #58](https://github.com/silverbjin/samsung_AXI/pull/58)에는 `ai/train`, P2 학습, Test-once 평가·승인 도구, private WSL2 실행기, dataset gate, P0~P6 보고서와 보류 중 모델 사용 경계 등 **30개 research 커밋**이 함께 들어 있습니다.
- `C16_FIRST_RESEARCH_PASS_CLOSED_NEGATIVE_VALIDATION_RESULT`: 모델 성능 HOLD / `C_RESEARCH_PILOT_ACCEPTED=false`. Test4 봉인, 재학습·A19·AI ON 허가 없음.
- 기존 [E PR #44](https://github.com/silverbjin/samsung_AXI/pull/44)는 **실제 WSL2 AI OFF L3 PASS**로 main 병합됨. C의 모델 미출고 상태가 AI OFF 제품의 완료를 취소하지 않음.
- 따라서 전체 research PR을 제품 main에 올리지 않고, **독립적인 `feat/smartdish-c17-c19-safe-release` 브랜치에 최소 모델 진입 보호 및 공개 보고서만 선택적으로 반영**합니다. 연구 브랜치의 정확한 SHA·CI·Owner 증거는 삭제하지 않음.

## 2. 제품 main 안전 변경 허용 목록

1. `src/smartdish_ai/smartdish_ai/model_runtime.py`: **코드에서 명시적으로 승인된 제품 모델 전체 SHA가 없으면 로딩 전 차단**. 현행 `PRODUCT_APPROVED_CHECKPOINT_SHA256=None`; C P2 실제 연구 checkpoint SHA는 불허.
2. `tests/test_c17_product_model_admission.py`: RED→GREEN 방어·UNKNOWN 확인. `tests/test_c18_model_card_contract.py`: 모델 카드의 주요 판정·자료 비포함 검수.
3. `.github/workflows/smartdish-c17-product-safety-ci.yml`: fixture-only L0, 공개 Jazzy 3패키지 빌드 L1 / NO_GOAL. Gazebo/GUI/owner WSL2 및 private B 데이터 불필요.
4. `ai/docs/C_V1_FROZEN_RESNET18_NEGATIVE_RESULT_MODEL_CARD_KO.md`: 실제 실패 연구의 **모델 미인수** 카드.
5. `docs/reports/tasks/2026-11-27_C17_PRODUCT_ADMISSION_SAFETY_EDU_KO.md` / `2026-11-27_C18_NEGATIVE_RESEARCH_MODEL_CARD_EDU_KO.md`, 본 C19 기록, `docs/handoff/C_HANDOFF.md` 최신 상태, `docs/DEVELOPMENT_LOG.md` 교육 이력.

**금지 파일 변경:** `src/smartdish_robot`, `src/smartdish_service`, `scripts/samsungaxi_*`, `ai/train/train_classifier.py`, `ai/train/evaluate.py`, 원본 dataset/split, B/A/GUI/CM/Nav2, Model `.pt`/weights/개인 승인. 향후 C 연구 파일럿 재개도 C20 새 독립 허가 경계임.

## 3. 품질 게이트 / 실제 검증

- C17 RED (#45922654643): 새 테스트6 FAIL / 기존 테스트66 PASS로 허가 누락 재현. GREEN [#45922743053](https://github.com/silverbjin/samsung_AXI/actions/runs/45922743053): 72 PASS, C 기존 UNKNOWN·D/E AI OFF 계약 보존.
- 추가 C19 L1 Jazzy 빌드 및 final main 병합 검수는 **최종 PR SHA·Actions 링크를 실제 확인한 뒤** 본 보고서 또는 PR에 추가합니다. CI PASS를 Owner 신규 WSL2 실물 PASS로 표기 금지.
- 현행 AI OFF 3구간은 기존 E Owner L3 [main 보고서](../integration/SMARTDISH_MVP_FINAL_ACCEPTANCE_KO.md)에서 이미 PASS. 다시 실물 주행하지 않음.
- C17은 **새 제품 AI ON 권한 발급이 아님**. C 모델 없이 `UNKNOWN`/직원 확인 대기 및 AI OFF 기본 유지.

## 4. C20 분리

- [GitHub Issue #59](https://github.com/silverbjin/samsung_AXI/issues/59): `[CHANGE REQUEST / NOT APPROVED]` v2 후속 연구.
- 별도 연구 승인 전 **새 데이터, A19, P2 재학습, Test4 개봉, AI ON, 임계값 재설계** 금지.
- C17~C19 필수 개발 완료가 C20을 자동 실행시키지 않음.

## 5. 완료 레이블 (검증 후 최종)

`C17_SAFE_ADMISSION_L0_L1_GREEN` / `C18_NEGATIVE_MODEL_CARD_PUBLISHED` / `C19_NARROW_SAFE_RELEASE` / `C20_CHANGE_REQUEST_OPEN_NOT_APPROVED` / `C_RESEARCH_PILOT_ACCEPTED=false` / `P3_TEST_NOT_OPENED` / `E_AI_ON=HOLD` / `AI_OFF=PROTECTED` / `PRODUCTION_CONTACT=HOLD`.
