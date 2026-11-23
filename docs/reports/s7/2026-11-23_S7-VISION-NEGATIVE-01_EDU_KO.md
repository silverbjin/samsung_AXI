# S7-VISION-NEGATIVE-01 — 빈 테이블·이미지 누락·판정 불확실성에 대한 안전 차단

## 1. RED와 학습 목표
기존 S6는 STACKED 양성 시나리오로 실증되었지만 빈 테이블에서 잘못된 복귀 Goal이 발행되는지에 대한 **실제 Gazebo 음성 반례**는 없었습니다. 
학생은 '실패했다'와 '안전하게 복귀를 차단했다'를 구별할 수 있어야 합니다.

## 2. 요구사항·상태·데이터 파이프라인
`Gazebo empty WORLD` → `Nav2 TABLE_3 Action SUCCEEDED` → `Odom settle` → `실제 RGB 임시 구독` → `NOT_STACKED / UNKNOWN` → `HOLD` → **PICKUP_RETURN Goal 0건**.
실패가 예상되어 시뮬레이션 드라이버 종료코드가 0이 아닐 수 있습니다. 단순 비정상 종료를 음성 테스트 PASS로 해석하면 안 됩니다.

## 3. 구현
- `scripts/s7_negative_contract.py`: 실제 `real_nav_legs`가 성공한 TABLE_3 1개만 있는지, `s7_scene.scenario=empty`, Vision `authorized=false`, `s6_return_goal_sent=false`, 원본 PPM의 RGB SHA256이 JSON과 같은지, `S6_VISION_HOLD_NO_RETURN_GOAL`가 실행 로그에 있는지 모두 확인.
- `tests/test_s7_negative.py`: L0에서는 **계약 검사에만 사용하는 인공 바이트**를 입력하여 잘못된 복귀 Goal·RGB 부재·오류 로그 부재가 실제 PASS로 오인되지 않는지 검사합니다. 이 L0를 실제 Vision AI 인수로 승격하지 않습니다.
- 기존 S6 ROS/TTY/Nav2 실행기는 변경하지 않습니다. 실제 L2에서는 고유 S7 빈 월드를 생성하고 기존 CI pseudo-TTY harness를 사용해 첫 Goal을 수행한 뒤 **예상되는 Vision HOLD**를 증거로 판정합니다.

## 4. 검증 근거 및 범위
- RED: 빈 테이블 반례에 대한 실제 S7 L2 증거 없음.
- GREEN L0: 계약 유닛 테스트와 원본 S6 fail-closed 상태 전이, 통합 실행기 불변 검사.
- GREEN L2: 실제 빈 테이블 PPM/Action/Goal 미발행이 모두 원본 증거로 확인될 때만 `S7_EMPTY_RGB_NO_RETURN_REAL_GAZEBO_L2_PASS`.
- 이미지 수신 실패의 UNKNOWN→HOLD는 S6 상태계약 단위 테스트로만 확인하며, **실제 이미지 누락 시험은 아직 미실행**입니다.

## 5. 초심자 실습·확인 질문
1. ROS Action 상태 4와 복귀 Goal 0건은 왜 둘 다 확인해야 하나요?
2. 모델이 NOT_STACKED로 응답한 사실만으로 Goal을 보내지 않았음을 증명할 수 있나요?
3. 빈 테이블 장면인데 이미지 SHA가 없으면 왜 실제 L2 검수에서 FAIL이어야 하나요?
4. 예측 실패가 발생했을 때 안전 정지와 자동 복귀의 차이는 무엇인가요?

## 6. 판정
코드/테스트/보고서 동일 브랜치 보존. 공식 CI 실제 Gazebo L2 실행 전에는 `L2=NOT_RUN`, CI L0 완료 전 `L0=NOT_RUN`. GUI 육안 검수는 사용자가 담당하며 자동 인수 제외. RTF 90% HOLD.
