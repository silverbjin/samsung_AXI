# D-PROD-01 — 물리 영수증 기반 제품 복구 FSM (교육용)
## WHAT
공통 Seed 57c5f57b471a92ae11adf1d2432d44aa8640d2ad / 계약 v1.1. 독립 모듈 product_recovery_fsm.py, product_recovery_transport.py. 기존 mission_manager.py, manager_node.py, ui_app.py, product_admission.py, 기존 AI OFF 및 station runner 변경 없음.
## WHY
기존 시간 기반 흐름은 식기 이동/촬영/하역을 입증하지 않는다. 기존 AI timeout은 수동 승인 경로로 들어가고 직원 대기가 무기한이었다. 신규 FSM은 ACK 이후에만 진행하고 hard failure는 추가 Goal 차단.
## HOW
TO_TABLE → WAIT_LOADING(최소 10s) → LOADING → CAPTURING → AI_CHECK → NEEDS_CONFIRMATION(60s) → TO_RETURN → WAIT_UNLOADING(최소 5s) → UNLOADING → TO_HOME → COMPLETED. Recovery AI OFF만 capture/AI/staff 생략. 120s nav, LOAD/UNLOAD/CAPTURE/AI/CANCEL 각 5s는 초기 설정; 실측 미확정. Deadline steady clock 및 receipt-time 검수. 정확한 request/stack/transfer/capture/stamp/hash, 유효 raw confidence, 모델 version, threshold snapshot 확인. ACK의 증거 파일/실제 entity pose 검증은 A/B/E 책임; D는 메시지 계약 검증만.
정상 C 응답 STABLE/UNSTABLE/threshold UNKNOWN만 explicit staff approve. CANCELING은 이미 수락한 UUID로 실제 A 취소 요청 후 ACK/terminal/stop 확인. 미확보 UUID는 SAFE_HOLD_UNVERIFIED; 신규 임무 금지. terminal 이후 자동 rearm 금지.
## RED → GREEN
| cycle | 실제 source SHA | CI run | 결과 | artifact ID / zip digest |
|---|---|---|---|---|
| 1 RED | e4fd7aacaf279dfbfd5237182c162598b89223ee | [45946923985](https://github.com/silverbjin/samsung_AXI/actions/runs/45946923985) | 신규 모듈 미구현 ModuleNotFoundError | 15174663744 / 61eb246831cc583f3aa1351062e203a22522d705431f2e0c35ff3cd0397dd834 |
| 1 GREEN | 7ff3f7e88219db7af1cf070e2b69ebf73f214283 | [45946993493](https://github.com/silverbjin/samsung_AXI/actions/runs/45946993493) | 8 fixture tests OK | 15174709941 / 9f494387b279ee6e7a027567127ff3658985510417b47a2df8c9199bcc20ff3e |
| 2 RED | ef04a53f919b666852d34f299a5aa02af7ac7f4b | [45947079847](https://github.com/silverbjin/samsung_AXI/actions/runs/45947079847) | 13 tests, 1 FAIL: reused terminal Goal UUID accepted (AssertionError True is not false) | 15174858725 / 4f04fe66520a972d4ffa9c3c2e914630d1afb526130a16adec00f9f712cc4931 |
| 2 GREEN | da924a2a7d47d01d156ac24386bc1f209d120eda | [45947092721](https://github.com/silverbjin/samsung_AXI/actions/runs/45947092721) | 13 fixture tests OK; terminal UUID reuse block | 15174838947 / 5213c3016d75f3b0e5b5526dcbea32e2e925c77cff284bd40283839fddbb1053 |
실제 PR run/job log와 Artifact metadata 확인. Digest는 GitHub upload artifact ZIP digest(다운로드 후 독립 재해시 아님). 각 결과는 해당 SHA의 L0 only, 실제 물리/실주행/모델/Owner PASS가 아니다.
## 교육 포인트
TDD 첫 RED는 구현 없는 import 오류이며, 두 번째 RED는 진짜 논리 오류이다. 상태가 바뀌어도 이전 action UUID를 재사용할 수 없도록 used_goals를 기록한다. C 결과의 confidence 값은 성능 보장이 아니며 정상 호출인지와 snapshot 일치가 별도 필요.
## REVIEW / HOLD
A/E 실제 accepted UUID transport 및 초기 stack/READY receipt, pre-capture ABORT 표현, unknown UUID A 자체 취소, restart/physical entity count/RETURNED receipt 계약 미확정. #66 comment 7210800035, #67 comment 7210877505, #69 comment 7210877968에 협의 요청. D 전용 ROS adapter는 명시적인 arm_verified 및 bind_accepted_goal 경계를 제공하고 실제 E 연결 전 standalone manager launch 금지. L1 installed DDS fixture 및 Xvfb는 별도 최종 원장. L2/L3 NOT_RUN. E 승인 전 merge 금지.
