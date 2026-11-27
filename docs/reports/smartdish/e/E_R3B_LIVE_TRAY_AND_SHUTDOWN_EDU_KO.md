# E-R3b — 실제 센서 동시 연계 및 종료 경계 (교육용)
## WHAT / WHY
R3a는 실제 A PNG의 재생 검증이었다. R3b에서는 기존 A13 single ST-01을 변경 없이 실행하고 A 로그에서 실제 ROS_DOMAIN_ID와 post-spawn capture stamp를 획득한다. C 기존 ROS node와 independent witness가 동일 domain에 가입한다. CI only predictor는 실제 C cache bytes의 SHA를 기록하고 별도의 witness가 live bridge에서 받은 RGB hash/시각과 대조한다. probe는 image publisher를 만들지 않는다. 정적 fixture 응답은 CI_ONLY_TEST_DOUBLE로 구분하고 private model을 사용하지 않는다.
## 종료 디버깅 (실제 R3a GREEN artifact에서 발견)
C SIGTERM 이후 ExternalShutdownException, RCLError rcl_shutdown already called. 기능 응답 성공 이후 발생. rclpy.spin의 정상 종료 예외만 처리하고 context ok일 때만 shutdown, 생성 실패 시 node=None 보호. 다른 예외는 그대로 전파해 실제 모델 로딩 실패를 숨기지 않는다. R3b C process exit=0 필수.
## 실제 검수
- A 원본 code path, 실제 Gazebo/bridge, 독립 domain. 실제 publisher 한 개 및 reliable QoS. C cache stamp>=post-spawn capture, witness RGB hash 일치, 1s 이내 새 frame.
- C DDS parameter ACK, request/capture ID와 STABLE 0.75 fixture 응답, predictor가 실제 수신한 RGB hash와 witness 대조. no Goal/cmd_vel.
- A single physics PASS 및 C clean exit 0. artifact 원본 결과와 로그 보존. timeout/fail-fast.
## 물리 적용 경계
A11 optional_robot_sdf는 카메라-only provisional overlay이며 로봇 트레이의 물리 geometry/시야가 검증되지 않았다고 명시한다. A13은 독립 world. 현재 R3b는 독립 트레이 actual live sensor의 software integration이며 robot-mounted tray, 주행 중 안정성, 실제 private model inference를 승인하지 않는다. R4에는 로봇 장착 환경의 별도 A 자산/계약이 필요하며, 독립 station을 사용하면 명시적으로 구분한다.
## 결과
본 커밋의 신규 CI 실행 전 NOT_RUN. R3a PASS는 위 별도 결과 보고서의 SHA에 한정한다. 기존 main/D merge tree가 동일하여 E가 새 main merge commit을 조상으로 포함하도록 non-force merge parent 동기화 가능; code tree 외 추가 차이 없음. 최종 Owner 인수 전까지 CI 정책 유지.
