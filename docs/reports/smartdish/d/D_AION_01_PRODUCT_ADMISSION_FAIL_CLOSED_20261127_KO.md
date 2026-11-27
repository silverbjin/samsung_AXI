# D-AION-01 — D Manager/UI 제품 진입 차단 (GREEN 설계/교육 보고서)

- 기준: main `ed59fa22bb53d1590ba10eef8f7982fcf44e7d29`, handoff PR #62.
- **RED:** 기존 Manager/UI는 `--ai-available true`만 보고 AI를 활성화. D 자체 E/C 허가 검증 없음. `tests/test_smartdish_d_aion.py`에서 정책 부재를 재현.
- **GREEN:** `product_admission.py`에 E 제품 허가 SHA와 E 승인 모델 SHA 두 상수를 **None**으로 명시. C17 `PRODUCT_APPROVED_CHECKPOINT_SHA256`와 정확히 매칭되고 별도 E 릴리스 승인 코드가 반영되기 전 `product_ai_on_authorized(True)`는 항상 false.
- **Manager:** `MissionManager(ai_available=False)` 강제, AI ON CLI 요청 시 `AI_ON_PRODUCT_NOT_AUTHORIZED` 출력, `ai_enabled=true` JSON은 `AI_NOT_AVAILABLE`로 Nav2 첫 Goal 없이 거절.
- **UI:** 같은 gate를 호출하여 체크박스 disabled. UI 요청 작성도 `ai_available and ai_var`로 이중 방어.
- **위험:** 상수 둘을 채운다고 자동으로 E 제품 출시 허가가 발생하지 않음. 현재 구현은 **보수적인 출고 전 조건**, E가 승인 영수증의 신뢰 루트·서명·provenance/권한을 별도 설계·승인해야 제품 AI ON 허가 가능. 현재 E 값 None 유지.
- **회귀:** AI OFF의 `MissionManager`, T03→RETURN→HOME·Steady Timer·7-topic ROS 계약 불변.
- **시험:** L0 mock 요청·env/CLI 우회 부정 테스트, L1 실제 Jazzy Manager `--ai-available true`가 fail-closed 되는지 제품 없는 DDS로 검증(주행 없음).
- **교육:** `request_id`와 `capture_id`는 작업 연관 ID이지 인증 토큰이 아닙니다. 모델 파일의 자기보고 `model_version`도 신뢰할 수 있는 서명이 아닙니다.
- **인수 경계:** `D_AI_ON_CONTRACT_ONLY_READY`, `PRODUCT_AI_ON_NOT_AUTHORIZED`.

## 실제 GREEN CI 및 교육용 리뷰

- 구현 SHA: `774a42914be6123ab89f71cee759b224ab1b72aa`.
- [GREEN GitHub L0/L1 #45926489996](https://github.com/silverbjin/samsung_AXI/actions/runs/45926489996): **L0 총 92 PASS**, L1 **3 ROS Jazzy 패키지 빌드 및 D Manager CLI true DENIED** `D_AION_L1_D_MANAGER_CLI_TRUE_DENIED_NO_GOAL`.
- D 상품 게이트 두 상수 `None`, C17 `None`을 반복 확인하고, 환경변수/CLI true 우회를 거부.
- 현재 E 제품 서명 영수증 검증 방법은 아직 독립 승인받지 않았으므로 이 기능은 **AI ON을 활성화하는 개발이 아닌 AI ON을 차단하는 개발**입니다.
- **RED/디버깅 이력:** 첫 신규 L0 #45926299277은 C 시험 의존 Pillow 미설치로 pytest 수집 단계 FAIL이며, 실제 기능 RED assertion 로그는 생성되지 않았습니다. 원본 불변 FSM 취약 경계는 D00 감사와 새 L0 규격으로 재현·수정했습니다. 수집 실패는 [D-DBG-AION-001](D_DBG_AION_001_CI_PIL_COLLECTION_20261127_KO.md)에 별도 보존했습니다.
