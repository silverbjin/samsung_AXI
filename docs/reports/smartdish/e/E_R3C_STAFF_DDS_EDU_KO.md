# E-R3c — 직원 확인 경계의 실제 ROS DDS 검수 (교육)
## WHAT/WHY
C 모델 결과가 STABLE이어도 D가 자동 주행을 시작하지 않아야 한다. L0 FSM 테스트를 실제 DDS 메시지·타이머·노드 graph로 확장한다. 이 검증은 실제 D manager와 CI-only synthetic A/C endpoints의 계약 시험이다. A Nav2, C 실제 model inference, 물리 이동은 시험하지 않는다. 가짜 A는 정확한 node name을 CI domain 190에서만 사용하고 실제 action/velocity를 발행하지 않는다.
## HOW
원래 운영 model admission 값은 변경하지 않는다. CI child 내부의 approved_model_sha256 반환만 fixture digest로 바꾸어 실제 C17 기본 deny와 분리한다. 실제 production checkpoint SHA/model version을 위조하지 않는다. D는 운영과 동일한 mission manager 및 DDS adapter를 사용한다.
## 시험
STABLE+APPROVE_CONTINUE 1회 TO_RETURN 및 TO_HOME; STABLE+ABORT, UNSTABLE+ABORT, UNKNOWN+ABORT, wrong-model STABLE+TIMEOUT+ABORT 후속 goal 0. wrong capture/request, duplicate staff action 무효. CI 계약 시간 1/1초, 실제 R4는 10/5초. 실제 DDS event timestamps 및 exit code, no cmd_vel/Nav2 action status publisher. 
## 결과
신규 코드와 workflow 작성. 실제 CI 완료 전 NOT_RUN. R3b 실제 camera-C 동시 시험과 R3c는 서로 다른 검증 계층이며 R4에서는 실제 A navigation과 연결한다. 실제 사용자 v1 model은 final owner 전까지 비공개 유지.
## 학습
실제 DDS는 mock payload라도 메시지 발견/타이머/상태 전이 경계를 검증한다. test double의 성공을 실제 로봇 주행 성공으로 해석하지 않는다.
