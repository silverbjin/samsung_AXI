# E-AION-03 — Owner Gazebo 전용 D Manager 진입·직원 승인 제어

- Owner는 기존 C v1 모델의 성능 33.3%를 이번 통합 게이트에서 면제함. 모델 성능 PASS로 재표기하지 않음.
- D의 기존 E 승인 상수 두 개는 계속 None. C17 기본 loader도 None. Owner 범위에만 E_OWNER_GAZEBO_MODEL_SHA256을 정확한 C v1 SHA로 고정.
- D Manager의 신규 명시적 --owner-gazebo-integration 플래그와 --ai-available true 둘 다 있을 때만 D의 AI 요청을 허용. 환경변수·임의 JSON 필드는 독립 승인 근거가 아님.
- owner_manual_confirm_ai=true인 FSM에서는 유효 STABLE도 TO_RETURN 자동 목표 전송이 아니라 NEEDS_CONFIRMATION 및 AI_STABLE_STAFF_CONFIRM_REQUIRED. UNSTABLE/UNKNOWN/Timeout 역시 직원 개입, ABORT/중복 승인 Goal 0건.
- 기존 AI OFF FSM 및 정상 STABLE 합성 L0 테스트는 그대로 유지. A Nav2/CM/3-leg 실주행 재구현·CI 실행 없음.
- 이 Owner 통합 권한은 내부 Gazebo 테스트 허가이며 실제 모델 파일·권리/가중치 외부 배포·실물 적재 안전 인증과 별개. ROS publisher 인증은 향후 E 보안 작업이 필요.

## E Owner UI 동적 threshold C→D 교차계약 보완

C의 `stable_confidence_min`은 0.50~1.00으로 조절 가능하지만, 원래 D FSM STABLE 규칙은 0.80 고정이었습니다. 이 상태에서는 C에서 0.65로 낮춰 STABLE(0.70)을 발행하더라도 D가 유효 응답을 무시해 5초 timeout으로 이어지는 **교차계약 불일치**가 발생합니다.

수정: `owner_manual_confirm_ai=true`일 때만 D가 정해진 confidence 범위(>=0.50)의 인증된 모델 버전 STABLE 응답을 받아 `NEEDS_CONFIRMATION`으로 이동합니다. 이 범위에서는 **어떤 STABLE도 자동 TO_RETURN을 만들지 않으므로** C의 정확한 threshold를 신뢰된 별도 채널로 재복사할 필요가 없습니다. C는 해당 클래스 기준 미달 시 반드시 UNKNOWN을 발행하며, D는 모델 전체 SHA pin/정확한 capture_id/5초 기한을 그대로 확인합니다.

기존 제품/합성 기본 FSM은 0.80 기준을 유지하며, 새 Owner 테스트는 0.70을 받아 직원 확인 후에만 동작함을 검증합니다. 사람/모델 응답 신원 인증이 끝났다고 주장하지 않습니다.
