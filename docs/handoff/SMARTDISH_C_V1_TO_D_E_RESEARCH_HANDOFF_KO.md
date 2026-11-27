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
