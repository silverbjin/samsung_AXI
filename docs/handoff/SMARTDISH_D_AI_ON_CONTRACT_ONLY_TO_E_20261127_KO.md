# SmartDish D → E — AI ON 계약 전용 준비 인계 (2026-11-27)

> **D 판정: `D_AI_ON_CONTRACT_ONLY_READY`**  
> **제품 판정: `PRODUCT_AI_ON_NOT_AUTHORIZED`**  
> 기존 A+D/E AI OFF L3 PASS는 재사용하며 새 실주행을 수행하지 않았습니다.

## 1. 소스·원본 문서
- 기준 main: `ed59fa22bb53d1590ba10eef8f7982fcf44e7d29`.
- 작업 브랜치: `feat/smartdish-d-ai-on-contract-only` (별도 Draft PR; main 미병합).
- 필수 C→D 인계: [PR #62의 실제 원본](https://github.com/silverbjin/samsung_AXI/blob/docs/smartdish-c-to-d-ai-on-handoff-20261127/docs/handoff/SMARTDISH_C_TO_D_AI_ON_SERVICE_HANDOFF_20261127_KO.md). 해당 문서는 기준 main에는 없는 Draft 문서였으며 내용을 읽고 감사했습니다.
- C17 실제 제품 모델 승인 상수: `src/smartdish_ai/smartdish_ai/model_runtime.py`, `PRODUCT_APPROVED_CHECKPOINT_SHA256=None`.
- D 제품 조건: `src/smartdish_service/smartdish_service/product_admission.py`의 E 허가·모델 SHA `None` 보존. 별도 신뢰된 E 릴리스 승인이 없으면 Manager/UI는 AI 사용 금지.
- B Dataset 연구용 18건, C Frozen ResNet18 Validation 1/3=33.3%로 모델 채택 HOLD, Test4 봉인, C20 #59 미승인.

## 2. 변경 범위·기능
- D Manager `--ai-available true`에도 제품 영수증·C 모델 SHA 조건 미충족이면 `AI_ON_PRODUCT_NOT_AUTHORIZED` 경고, UI AI 토글 disabled.
- `ai_enabled=true` 요청 → `AI_NOT_AVAILABLE`, Nav Goal 없음.
- 순수 FSM mock 계약에서만 합성 모델 SHA를 전달할 수 있습니다. 이 SHA는 E 승인값이 아니며 실제 ROS 런타임에는 주입되지 않습니다.
- `STABLE`은 ID·capture/5초 deadline, confidence >=0.80, 사전 E 허가된 모델 전체 SHA에 연결된 `resnet18-<sha12>`가 모두 일치해야만 모의 FSM에서 진행.
- 모델 없는 C는 `UNKNOWN/confidence:null/model_version:none`; D의 `UNKNOWN/UNSTABLE/TIMEOUT`은 `NEEDS_CONFIRMATION`.
- 직원 `APPROVE_CONTINUE` 명시 행동 뒤 **추가 논리 Goal 1건**; `ABORT`/중복/타 요청 ID는 Goal 0건.
- 기존 7개 `/collection/*` 토픽과 `/smartdish/tray/image_raw`, A/D/E AI OFF, Nav2/Collision Monitor와 원샷 스크립트는 수정하지 않았습니다.

## 3. 실제 검증 결과와 한계
| 검증 | 근거 | 판정 |
|---|---|---|
| Python L0 D-AION·D/E AI OFF·C17·C 계약 | [Actions #45926489996](https://github.com/silverbjin/samsung_AXI/actions/runs/45926489996) | **92 PASS / SYNTHETIC** |
| ROS Jazzy L1 패키지 | 동일 Run | D/C/A 3 packages PASS |
| 실제 DDS D Manager `--ai-available true` | 동일 Run | 거부 응답 + Nav Goal 0, PASS |
| 실제 DDS C no model/duplicate request | 동일 Run | UNKNOWN 단일 응답, PASS |
| 실제 C 모델 추론·B 개인 데이터/영상·Test4 | 금지 | NOT_RUN / NOT_AUTHORIZED |
| 실제 제품 AI ON·Gazebo·Owner WSL2 | 금지 | NOT_RUN / NOT_AUTHORIZED |
| 기존 E AI OFF L3 | 이전 Owner 인수 보고서 원본 재사용 | PASS (재실행 안 함) |

**주의:** rclpy 테스트 DDS는 암호학적 Publisher 신원 검증이 아닙니다. 현재 상품 게이트가 닫혀 있으므로 위조 STABLE으로 실제 주행이 허용되지는 않지만, 향후 모델 승인 시에는 E가 공급자 신뢰·release receipt·signature를 별도로 설계해야 합니다.

## 4. 미래 제품 AI ON 출고 전 필수 E/PM 승인
1. C의 독립 모델 성능/권리/안전 검토 및 `C_RESEARCH_PILOT_ACCEPTED` 승인.
2. B의 연구용 이용권과 제품 사용 허가 경계 별도 확정. Test4는 승인 전 개봉 금지.
3. E가 제품 모델 전체 SHA, 승인된 E release commit/receipt 신뢰 근원, 인증된 C inference 경로와 DDS 보안 정책을 설계·승인.
4. C17 역직렬화 이전 승인 SHA/weights provenance 확인. 미승인 `.pt` 로드·재배포 금지.
5. 별도 AI ON 승인 GO 이후에만 E 한 번의 immutable SHA WSL2 원샷, TAR+SHA256 및 AI OFF 회귀/AI ON 실주행 증거 계획 수립.
6. 이번 D 작업은 이 승인들을 **발급하지 않았습니다**. C20 #59, A19, P3 Test·재학습은 별도 승인 전 금지.

## 5. 교육·디버깅 이력
- [D00 감사](../reports/smartdish/d/D_AION_00_READ_ONLY_POLICY_AUDIT_20261127_KO.md)
- [D01 제품 Gate](../reports/smartdish/d/D_AION_01_PRODUCT_ADMISSION_FAIL_CLOSED_20261127_KO.md)
- [D02 응답 신뢰/타임아웃](../reports/smartdish/d/D_AION_02_STABILITY_CONFIDENCE_FRESHNESS_20261127_KO.md)
- [D03 직원 확인](../reports/smartdish/d/D_AION_03_STAFF_CONFIRMATION_20261127_KO.md)
- [D04 모델 없는 DDS](../reports/smartdish/d/D_AION_04_MODEL_LESS_DDS_E_REGRESSION_20261127_KO.md)
- [D-DBG-AION-001 Pillow 수집 오류](../reports/smartdish/d/D_DBG_AION_001_CI_PIL_COLLECTION_20261127_KO.md)

모든 항목은 RED 최초 원인 → 최소 수정 → L0/L1 GREEN → 문서/커밋 순서로 추적하고 실제 모델·주행을 완료했다고 표현하지 않습니다.
