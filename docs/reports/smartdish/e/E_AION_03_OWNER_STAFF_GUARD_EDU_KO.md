# E-AION-03 — Owner Gazebo 전용 D Manager 진입·직원 승인 제어

- Owner는 기존 C v1 모델의 성능 33.3%를 이번 통합 게이트에서 면제함. 모델 성능 PASS로 재표기하지 않음.
- D의 기존 E 승인 상수 두 개는 계속 None. C17 기본 loader도 None. Owner 범위에만 E_OWNER_GAZEBO_MODEL_SHA256을 정확한 C v1 SHA로 고정.
- D Manager의 신규 명시적 --owner-gazebo-integration 플래그와 --ai-available true 둘 다 있을 때만 D의 AI 요청을 허용. 환경변수·임의 JSON 필드는 독립 승인 근거가 아님.
- owner_manual_confirm_ai=true인 FSM에서는 유효 STABLE도 TO_RETURN 자동 목표 전송이 아니라 NEEDS_CONFIRMATION 및 AI_STABLE_STAFF_CONFIRM_REQUIRED. UNSTABLE/UNKNOWN/Timeout 역시 직원 개입, ABORT/중복 승인 Goal 0건.
- 기존 AI OFF FSM 및 정상 STABLE 합성 L0 테스트는 그대로 유지. A Nav2/CM/3-leg 실주행 재구현·CI 실행 없음.
- 이 Owner 통합 권한은 내부 Gazebo 테스트 허가이며 실제 모델 파일·권리/가중치 외부 배포·실물 적재 안전 인증과 별개. ROS publisher 인증은 향후 E 보안 작업이 필요.
