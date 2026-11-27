# C17 — 미승인 안정성 모델의 제품 진입 차단 (2026-11-27)

## 1. 계약/목적

- 현재 main D/E 통합: [E PR #44](https://github.com/silverbjin/samsung_AXI/pull/44) 병합, AI OFF 3구간 WSL2 L3 PASS, A/D/E 원본 코드 불변.
- C Dataset v1 frozen 연구는 `C16_FIRST_RESEARCH_PASS_CLOSED_NEGATIVE_VALIDATION_RESULT`, **모델 인수 HOLD**, Test4 밀봉. P2 checkpoint SHA `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c`는 **출고 허가가 아닌 연구 증거**.
- C17의 의무는 실제 모델을 만드는 것이 아니라 **제품용 ROS inference 런타임이 미승인 가중치를 로딩하지 못하도록 보수적으로 보호**하는 것. E AI ON 승인·실모델 점검은 수행하지 않음.

## 2. RED → GREEN 재현 및 최소 수정

**RED:** [CI #45922654643](https://github.com/silverbjin/samsung_AXI/actions/runs/45922654643), test-first SHA `7487060d435d0544bdce24aebca8dfc5cd16a09e`: 새 승인 방어 테스트 **6 FAILED**, 기존 AI OFF/D/E/C 테스트 **66 PASS**. 최초 오류: `C17_E_PRODUCT_RELEASE_GUARD_MISSING` 및 미승인 파일을 평가하려는 과정에서 `No module named torch`. 이는 실 가중치 문제로 추정하지 않고 **승인 검사가 torch import보다 먼저 이뤄지지 않는 코드 경계** 문제로 분류.

**GREEN:** `src/smartdish_ai/smartdish_ai/model_runtime.py` 소스 SHA `bef2a0bab07d8fb24ef174a2c7b9dfbfe89f6725`. `PRODUCT_APPROVED_CHECKPOINT_SHA256=None`을 기본값으로 고정하고, `require_product_model_release`가 **실제 파일 바이트 SHA256 전체를 E 별도 코드 릴리스로 승인된 checksum과 비교**하도록 구현. 승인 checksum이 없으면 `C_PRODUCT_MODEL_NOT_APPROVED`로 torch import/가중치 역직렬화/모델 추론 **이전**에 fail-closed. 가중치 파일의 자체 메타데이터로 승인할 수 없음.

검증 구조:
1. 제품 gate: checksum null/불일치/비형식은 거부 (`PRODUCT_APPROVED_CHECKPOINT_SHA256=None`은 의도된 현행 출고값). 새로운 checksum을 채우려면 **새 독립 E 승인·PR 리뷰·새 제품 릴리스**가 필요. 환경 변수나 사용자 임의 `.pt` 메타데이터로 enable 불가.
2. 사전 provenance gate: 만약 미래 제품 승인이 내려오더라도 `research_release_status=C_RESEARCH_PILOT_ACCEPTED`, `PHYSICS_OBSERVED`, 연구 사용 범위, 모델 형태/라벨/normalize 등 요구. 하지만 이 메타데이터만으론 제품 승인이 되지 않음.
3. C ROS `stability_inference_node.py`는 `load_predictor` 오류를 기존대로 받아서 `InferenceCore(None)`을 생성하므로 **`UNKNOWN`/confidence null/model_version none**. D `MissionManager(ai_available=False)` 및 A/E 3-leg AI OFF 계약은 수정하지 않음.

**GREEN CI:** [#45922743053](https://github.com/silverbjin/samsung_AXI/actions/runs/45922743053) **72 PASS**, 기존 66 계약 포함, 모델 학습/PNG/B 증거/Gazebo/WSL2 불필요. 여기에 포함된 ROS 없는 모델 미탑재 UNKNOWN 테스트는 실제 Nav2/GUI 재인수 증거를 생성하지 않음.

## 3. 코드 인수/교육 체크포인트

- 단순히 `checkpoint.get("PHYSICS_OBSERVED")` 여부는 **증거 출처 자기 주장**일 수 있음. 먼저 외부 승인된 **파일 전체 digest**를 보아야 함.
- 제품 승인 유무는 C research approval·데이터 이용권과 분리. 현재 제품 허가 `NONE`; `P2` checkpoint는 설령 가중치 파일의 메타데이터를 변조해도 제품에 자동 탑재되지 않음.
- AI OFF에서 C node의 `model_path`가 비어 있으면 기존 미탑재 UNKNOWN 경로 사용. 가중치를 직접 ROS 파라미터에 넣어도 승인되지 않으면 UNKNOWN.
- 별도 E AI ON 제품 출시가 미래에 명시적으로 승인되는 경우 **새 AI ON 인수·별도 review·서명/공급망/배포 정책**이 필요. C17 계약 테스트 PASS가 미래 제품 release를 자동 승인하지 않음.

**상태:** `C17_PRODUCT_CHECKPOINT_ADMISSION_PROTECTED`, `AI_OFF=PROTECTED`, `E_AI_ON=HOLD`, `A19=NOT_AUTHORIZED`, `P3_TEST=SEALED`, `PRODUCTION_CONTACT=HOLD`.
