# S6-FLOW-01 — TABLE_3 도착·Vision 식기 확인·복귀 상태기계 중간 보고서

- 날짜 2026-11-23 / 브랜치 feature/s6-vision-flow-20261123
- 구현 단계: ROS 비의존 상태기계·실패 폐쇄 테스트 작성. **Gazebo 통합/WSL2 검수 전.**

## 1. 요구사항
기존 S5 자동 복귀는 첫 NavigateToPose(TABLE_3) 성공 직후 두 번째 Goal을 보냅니다. S6에서는 TABLE_3 Action SUCCEEDED와 로봇 정지 확인 뒤 카메라 구독을 시작하며, 실제 Vision AI가 STACKED로 판단했을 때만 PICKUP_RETURN을 보냅니다.

## 2. 상태 전이
`NAV_TO_TABLE` → `ARRIVAL_SETTLED` → `VISION_REQUESTED` → `VISION_RESULT` → `NAV_RETURN` → `RETURNED`; 예상치 못한 순서/이미지 타임아웃/불확실한 판단이면 `HOLD`.

## 3. 코드와 안전 계약
- `scripts/s6_flow_contract.py`: ROS 없이도 재현 가능한 순수 상태 전이 함수.
- `scripts/s6_vision_ai.py`: 실제 영상에서 얻은 특징으로 지도학습된 결과만 반환합니다. 결과에 confidence/reason이 있어야 복귀를 허가합니다.
- 기존 Nav2를 이용하고 AI가 `/cmd_vel`을 직접 보내지 않습니다. 실패 시 새 Goal은 발행하지 않습니다.
- `tests/test_s6_flow_contract.py`: NOT_STACKED, UNKNOWN, TIMEOUT, 데이터 부족, 위조 결과, 낮은 confidence 모두 HOLD 검사.

## 4. 주니어 교육 포인트
1. 'Nav2 Action 성공'과 'Vision 식기 적재'는 서로 다른 요구사항입니다. 각각 독립 증거가 필요합니다.
2. 사전 조건이 만족되지 않으면 Goal을 무조건 발행하지 않는 fail-closed 전략을 사용합니다.
3. 상태 전이와 ROS 토픽 콜백 코드를 분리하면 입력 순서 오류를 빠르게 검출할 수 있습니다.
4. 긍정 예시만 테스트하는 것은 부족합니다. 부정·경계 사례로 '잘못된 자동 복귀'를 막는 것이 핵심입니다.

## 5. 검증 순서
- L0 상태 계약/부정 테스트 → S6 ML 실제 학습 모델 확보 → 실제 TABLE_3 배달→Vision 이미지→복귀→LiDAR STOP 동일 세션 L2 → 강사 WSL2 L3.
- 기존 S5 배달·복귀·STOP PASS 재사용. 성공한 S5 실행을 무리하게 수정하거나 반복 검수하지 않습니다.

## 6. 판정
코드 일부 구현 / L0 NOT_RUN / L2 NOT_RUN / L3 NOT_RUN / RTF 90% HOLD.
