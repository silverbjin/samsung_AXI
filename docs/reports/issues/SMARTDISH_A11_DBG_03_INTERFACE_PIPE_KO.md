# A-11-DBG-03 — ROS 2 interface show 파이프 조기 종료(BrokenPipeError)

- 최초 L1 오류: [GitHub Actions Run #45306883609](https://github.com/silverbjin/samsung_AXI/actions/runs/45306883609) (L0 **24 PASS**, L1 `smartdish_robot` colcon build **성공** 후 테스트 명령에서 exit 120).
- 실제 최초 오류: `ros2 interface show sensor_msgs/msg/Image | grep -q encoding` → `BrokenPipeError: [Errno 32] Broken pipe`, `ros2cli`의 stdout flush 실패.
- 확인된 실패 경계: ROS Image 타입이 없거나 Gazebo bridge가 고장난 것이 아닙니다. `grep -q`가 첫 일치 뒤 파이프를 일찍 닫아, 긴 ROS 타입 출력 중인 `ros2 interface show`의 Python 프로세스가 예외를 냅니다. `set -o pipefail` 때문에 명령/작업 전체가 실패합니다.
- 최소 수정: `ros2 interface show` 출력 전체를 우선 임시 파일로 수집하고, **그 파일**에 `grep -q`를 사용합니다. `pipefail`와 테스트는 그대로 유지합니다. `PYTHONUNBUFFERED` 변경이나 `|| true`로 오류 은폐하지 않습니다.
- 재검: 기존 L0 24 PASS 보존, L1 ROS 타입 검사 재실행, L2 실제 Gazebo sensor/physics 최초 실행 결과는 별도 기록.
- 교육 요점: 실패가 `colcon` 뒤의 shell pipeline에서 발생할 때, 라이브 센서/통신 실패로 오인하지 말고 최초 오류의 발생 프로세스와 종료 코드를 분리합니다.
