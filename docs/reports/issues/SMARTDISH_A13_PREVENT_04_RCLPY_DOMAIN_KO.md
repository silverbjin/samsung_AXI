# A-13-PREVENT-04 — CI 경계 사전 리뷰: Python rclpy와 bridge 도메인 불일치 방지

- 발견 시점: L0 Python PASS 후 실제 Gazebo L2 시작 전 소스 리뷰. **실제 발생한 CI 런타임 실패 로그가 없으므로 예방 수정**으로 구분.
- 확인된 코드 위험: `subprocess.Popen(..., env=env)`를 쓰는 Gazebo/bridge에만 trial별 `ROS_DOMAIN_ID`가 지정되고, parent Python 프로세스의 `rclpy.init()`는 그 값을 전달받지 않음. 이 상태로는 서로 다른 DDS Domain을 사용하여 이미지/pose 미수신 가능.
- 최소 수정: Jazzy `rclpy.init(args=None,domain_id=int(env["ROS_DOMAIN_ID"]))`. parent 전역 환경을 변경하지 않고 ROS Context에 trial domain을 명시. 실험 끝에 `rclpy.shutdown()`과 프로세스 종료는 기존 방식 유지.
- 회귀: `tests/test_smartdish_a_tray_runner.py`에서 ROS bridge와 collector가 **동일 환경 변수**로 초기화됨을 점검.
- L2 실제 Gazebo 실행으로 최종 증명할 때까지 `NO_PHYSICAL_EVIDENCE` 상태이며, 예방 리뷰를 장애 해결 성공으로 부풀리지 않습니다.
