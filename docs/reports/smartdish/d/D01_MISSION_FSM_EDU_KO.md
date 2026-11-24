# D01 — 순수 Python Mission Manager 개발 보고서

- 담당: D / SmartDish service
- 기준선: S7 main \`2dd7f968dd3d24e2afb48e0917ef8c9d054ac894\`
- 개발 단위: D01 / 상태 머신과 v1.0 요청·결과 계약
- 검증 구분: Python MOCK_ONLY. 실제 ROS/Gazebo 주행 증거 아님.

## 문제 정의와 설계 이유
기존 S7은 2-leg 주행/영상 판정이 중심입니다. 새로운 회수 서비스는 도착 성공 후 10초와 5초를 기다려야 하며 3-leg 진행은 D가 담당해야 합니다. 의존성을 줄이려고 **핵심 FSM을 ROS 2와 Tkinter에서 분리**했습니다. 이 분리는 초심자도 같은 입력을 여러 번 재현하며 디버깅하게 해 줍니다.

## 계약/소유 경계
- D: \`request_id\`, 상태, 실시간 타이머, AI 승인, 다음 논리 목적지 발행
- A: \`table_poses.yaml\`, 실제 Nav2 SUCCEEDED/FAILED/CANCELED, odom
- D가 NAV_RESULT SUCCEEDED 또는 임의 \`x,y,yaw\`를 계산·제작하지 않습니다.
- UI 픽셀좌표와 Nav2 map 좌표는 별도 체계입니다.

## 코드 따라 읽기
1. \`handle_request\`: T03와 정수 대기시간·AI 기능 허용 여부 검사, BUSY 차단
2. \`_begin_leg\`: 세 가지 허용 \`leg → destination_id\` 매핑만 발행
3. \`on_nav_result\`: 동일 request_id와 현재 leg의 결과만 허용
4. \`_start_wait\`/\`tick\`: \`time.monotonic()\`으로 도착 뒤부터 대기
5. \`on_stability\`/\`on_staff_confirm\`: 불확실성은 사람이 승인하기 전 주행 금지
6. \`drain\`: 출력 이벤트를 UI/ROS가 소비하는 구조, 모의 테스트에서도 동일 스키마 사용

## 검증/학습 포인트
\`python3 -m pytest -q tests/test_smartdish_d_service.py\`
확인항목: 3구간 순서, 도착 전 카운트다운 금지, BUSY/중복, 잘못된 ID/leg 무시, FAILED/CANCELED 차단, AI OFF 독립, AI ON 확인·타임아웃. 테스트에서 \`SUCCEEDED\`를 넣는 것은 **모의 이벤트**이며 \`AI_OFF_REAL_RUN_PASS\`가 아닙니다.

## 실패/디버깅 추적 규칙
각 수정은 \`docs/reports/smartdish/d/\`에 재현 입력, 첫 오류, 가설/원인, 바뀐 함수, 재검증과 남은 NOT_RUN을 적습니다. 테스트 통과 로그와 커밋 SHA는 별도 후속 검증 보고서에 연결합니다.

## 초심자에게 묻는 질문
1. TIMER를 Goal 전송 시점에 시작하면 왜 잘못됩니까?
2. UUID가 같지만 leg가 다른 메시지를 왜 무시해야 합니까?
3. AI OFF에 추론 토픽이 존재할 필요가 없는 이유는 무엇입니까?
4. STATUS ERROR reason=BUSY를 발행하더라도 기존 임무 state를 바꾸면 왜 안 됩니까?
