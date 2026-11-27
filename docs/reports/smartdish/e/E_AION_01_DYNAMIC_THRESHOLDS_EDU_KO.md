# E-AION-01 — C STABLE/UNSTABLE 판단 최소 신뢰도 동적 변경 개발 보고서

- 기준 E branch `feat/smartdish-e-v1-owner-ai-integration`, C base main `ed59fa22`.
- 배경: 원래 C는 `confidence_min=.80`을 두 class에 동일 적용. Owner는 C20과 별도로 v1 모델을 유지하고, 통합 테스트 중 **두 클래스별 판단 기준을 동적으로 변경**할 수 있는 인터페이스를 요구.
- 정의: `stable_confidence_min`, `unstable_confidence_min`은 **softmax 상위 클래스의 confidence 최소치(0.50~1.00)**. 다른 클래스 확률/label 자체를 임의로 뒤집거나 B GT·Gazebo 물리 기준을 변경하지 않음. 기준 미달/이미지 없음/미승인 모델은 `UNKNOWN`.
- 구현: `InferenceCore.set_decision_thresholds(stable,unstable)`에서 **두 수치를 먼저 검증한 후 한꺼번에 변경**하여 일부만 바뀐 상태 방지. C `StabilityInferenceNode`는 ROS 2 parameter 변경 callback에서 유효성 검사·반영·로그 기록. 기존 `confidence_min` 초기값 0.80 계약은 보존.
- ROS 파라미터: `/smartdish_stability_inference/stable_confidence_min`, `unstable_confidence_min` (기존 `/collection/*` 7토픽 변동 없음).
- 테스트: 6개 분류 경계 케이스, 런타임 재설정 후 다음 캡처에 적용, NaN/Inf/불리언/범위 오류 원자적 거부, 모델 없음 UNKNOWN.
- 평가 경계: 편의용 판정 임계값은 **성능 개선/재학습이 아님**. Validation 33.3%는 그대로 기록하며 실제 운영 안전 지표가 아님. 승인 범위는 내부 WSL2/Gazebo 통합 시험.
- 교육: 학습 GT label(STABLE/UNSTABLE), 모델 예측 class, confidence, inference 판단 UNKNOWN은 별개의 개념입니다. 모델 클래스가 STABLE이어도 confidence가 안정 기준보다 낮으면 UNKNOWN이 됩니다.
- L0/L1 실행 결과·CI URL은 최종 실행 후 추가 보고서에서 연결.
