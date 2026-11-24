# D-DBG-001 — A↔D request_id / AI 결과 계약 교차 검토 및 최소 수정

- 날짜: 2026-11-23
- 분류: **정적 계약 검토에서 발견된 불일치** (Gazebo 또는 ROS 실측 실패가 아님)
- 기준: D03 커밋 \`f6aaecbeef615fdf9ac837791f7af6e64367ca95\`, A branch \`feat/smartdish-a-robot\`
- 상태: 코드 수정/추가 L0 테스트 예정, 실제 통합 NOT_RUN

## 1. 관찰: 재현 가능한 계약 경계
A \`contract.py:parse_goal\`은 \`request_id == request_id.strip()\`을 요구하지만, D01 \`_valid_request\`에서는 공백 포함 ID를 허용했습니다. 예: \`" REQ-1 "\`. 이 경우 D는 요청을 수락해 Goal을 발행하지만 A는 \`INVALID_REQUEST_ID\`로 차단합니다. 안전 위반은 아니지만 서비스 관점에서는 사전에 걸러야 할 입력입니다.

추가로 D01 AI 파서는 \`status=STABLE\`과 식별자만 있으면 진행할 수 있었고, 공통 v1.0의 필수 \`confidence\`/\`model_version\` 검사와 불일치했습니다. 실제 C 신뢰도 또는 모델 버전이 없는 \`STABLE\`은 **계약 위반 입력**이므로 진행을 허용하지 않아야 합니다.

## 2. 가설과 근거
- 원인1: A와 D의 순수 Python 스키마를 서로 비교하는 테스트 부재.
- 원인2: D AI handler가 필수 필드 존재와 값 범위를 검사하지 않음.
- 근거: D \`mission_manager.py\` 소스와 A \`contract.py\`를 직접 비교.
- 미확인: Gazebo 및 C 실시간 추론에서 동일 오류가 발생했는지는 검증하지 않았습니다.

## 3. 최소 수정
- \`MissionManager._valid_request\`: 앞뒤 공백이 있는 ID 거절.
- \`MissionManager.on_stability\`: confidence(0..1 또는 null), model_version 문자열 필수. STABLE의 무신뢰 \`null/none\` 조합은 거절하고 5초 후 \`NEEDS_CONFIRMATION\`으로 fail-closed.
- \`tests/test_smartdish_d_service.py\`: 위 두 실패 사례와 정상 AI 검사 fixture 추가.
- 변경하지 않은 것: Nav2, A Adapter, S7, QoS/ROS 메시지 enum.

## 4. 검증 방법과 경계
\`\`\`bash
python3 -m pytest -q tests/test_smartdish_d_service.py tests/test_smartdish_d_ui.py
\`\`\`
L0는 \`MOCK_ONLY\`입니다. **AI 실제 추론 성능·Gazebo 주행 합격 근거 아님.** 검증 실행 SHA/링크는 D 최종 검증 보고서에 기재합니다.

## 5. 초심자 학습 포인트
1. A와 D가 같은 필드명을 쓰더라도 입력 검증 방식까지 일치해야 합니다.
2. 성공 메시지는 출력자와 식별자, 필수 필드가 맞아야만 다음 상태로 전이합니다.
3. 실패를 재현하기 위해 실제 로봇을 움직일 필요가 없습니다. 순수 계약 입력으로 먼저 문제를 격리합니다.
4. 관찰된 사실(정적 불일치)과 추정된 위험(실제 실행 중 거절 가능)을 구분합니다.
