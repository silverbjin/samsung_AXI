# S6 G08 — 실제 Gazebo L2 PICKUP_RETURN ABORT 재현 및 원인 경계 교육 보고서

## RED: 실패한 CI 원본
- 변경 코드 SHA: 611ac7b9edf5aa275dc4dbbde86530a573165a77, Run #45104473441 (1차 L2 FAIL).
- 원본 artifact #14787034063, ZIP SHA256 f1f90813cc7891238a104325f240d5730f7749a10f497a698e9a00a98b5bf80e.
- 동일 실행의 TABLE_3 Goal 성공(5.116m, AMCL 오차 0.182m), 실제 RGB 3프레임의 STACKED confidence 0.6659, return 권한/Goal 발행은 성공.
- 그러나 PICKUP_RETURN 중 Action 상태 6(ABORTED), 물리 이동 4.8596m, 목표 오차 0.3774m, 직전 피드백 거리 0.419m. 목적지 도착은 확인되지 않았습니다.
- 실제 센서 최신성: scan 0.131s, Odom 0.068s. number_of_recoveries=0. 임의로 센서 stale이라 단정하면 안 됩니다.
- ci-s3-summary.txt에는 controller_server의 반복된 control-loop missed rate 경고, bt_navigator의 'Timed out while waiting for action server to acknowledge goal request for follow_path', ActionServer abort/Goal failed가 있습니다.
- Nav2 error_code=0, error_msg=null이므로 **정확한 내부 실패 원인은 이 요약만으로 미확정**입니다. 최근 120개 error context는 전체 trace가 아닙니다.

## 진단과 가설
1. FollowPath action goal acknowledgement 대기가 CI/RMW 부하 또는 controller executor 지연과 겹쳤을 가능성을 조사해야 합니다. 원인은 미확정입니다.
2. S6 GUI 관련 수정은 headless CI에서 GUI 옵션이 false이므로 Qt XCB 경로가 실행되지 않습니다. 따라서 이를 OpenGL 수정이 직접 Nav2 abort를 만들었다고 단정할 근거는 없습니다.
3. 이전 **동일 시나리오**의 런타임 SHA 937fbf025cefec01489c40bc5104c39e3d4709be에서는 CI #45098202033 L2 PASS였으므로, 우선 같은 611ac SHA의 정확히 한 번의 독립 재실행으로 재현성을 분리합니다.

## 최소 코드와 GREEN 조건
- scripts/s6_nav2_return_abort_classifier.py: 실제 JSON+CI 로그에서 follow_path ack timeout을 식별하되, abort를 성공으로 승격하지 않습니다.
- tests/test_s6_nav2_return_abort_classifier.py: Action=6, 목표 오차, 센서 freshness, 오류 원인 미확정 계약 테스트.
- GitHub Actions 기존 실패 L2 Job만 동일 SHA로 재실행했습니다. 재실행은 1회, 안전/지도/Planner/Goal 시간 제한을 임의로 변경하지 않습니다.
- GREEN 기준은 실제 Action 2개 SUCCEEDED + Vision STACKED + CM STOP + output/odom 증거가 모두 갖춰진 **완전히 정상 종료된 독립 런**입니다. 재실행이 실패하면 full Nav2 server trace를 최소 추가 계측하고, 원인 확인 전 임계값을 완화하지 않습니다.

## 주니어 교육용 실습
1. `action_status=6`과 `nav2_error_code=0`은 서로 모순되지 않을 수 있습니다. ROS Action 상태와 오류 payload를 구분하십시오.
2. 첫 TABLE_3 성공과 Vision 추론 성공만으로 전체 S6 완료라고 판정하면 어떤 문제가 생깁니까?
3. FollowPath ack timeout과 주행 경로가 막힌 현상을 구분하려면 서버 로그/TF/실제 Goal feedback에서 무엇을 검사해야 합니까?
4. 커밋이 동일한 1차와 2차 실증의 결과가 다르면, 성공 증거를 보존하면서 어떤 반복 범위를 정의해야 합니까?

## 판정
- G08 실패 증거 분류: PASS, 실제 PICKUP_RETURN: FAIL. 동일 SHA L2 1회 재실행: RUNNING/NOT_VERIFIED(보고서 작성 시점).
- 이미 성공한 S5/S6 원본과 지도는 보존. WSL2 GUI OpenGL L3: NOT_RUN. RTF 90%: HOLD. main 병합: HOLD.
