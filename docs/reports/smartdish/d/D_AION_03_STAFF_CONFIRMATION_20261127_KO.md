# D-AION-03 — NEEDS_CONFIRMATION 직원 승인/중단 안전 계약

- **RED 조건:** UNKNOWN/UNSTABLE/5초 AI_TIMEOUT이 발생한 경우 직원 행동 전 `/collection/nav_goal`이 없어야 합니다. 잘못된 request_id/임의 action/중복 승인도 추가 Goal을 만들면 안 됩니다.
- **GREEN 확인 대상:** 기존 `MissionManager.on_staff_confirm`은 `NEEDS_CONFIRMATION`과 정확한 `request_id` 및 `APPROVE_CONTINUE/ABORT`만 허용. 승인 시 **수동으로만** TO_RETURN 1건, ABORT 시 CANCELED 및 다음 Goal 0건. 요청 중복은 거부.
- UI는 `NEEDS_CONFIRMATION`에서만 직원 버튼을 표시하고 클릭 직후 숨깁니다. 이번 작업은 디자인을 재작성하거나 사용자의 시각 인수를 반복하지 않습니다.
- `UNKNOWN`은 AI 모델이 생성한 안정/불안정 학습 클래스가 아니라 **확인 필요 응답**임을 구분합니다.
- 테스트 ID: `test_D_AION_03_manual_confirmation_boundary`, `_abort_does_not_publish_goal`, `_timeout_remains_manual_only`.
- 인증된 직원의 물리 확인 책임과 실제 현장 UI 승인 기록은 미래 E 운영 인수 범위입니다. 합성 FSM 테스트에서 직원 역할을 가장한 dict는 실제 승인 아님.
- 본 코드 범위에서 직원 승인 로직은 기존 정책을 보존하며, 실패 시 최초 오류만 수정합니다.
