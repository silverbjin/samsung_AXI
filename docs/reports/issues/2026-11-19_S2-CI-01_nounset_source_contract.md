# S2-CI-01 — Actions ROS setup nounset 보호 계약 실패
- 날짜: 2026-11-19 KST, 상태: **RESOLVED — 동일 L0 및 실제 L1/L2 통합 재검 PASS**
- 최초 RED: [Run #44488381423](https://github.com/silverbjin/samsung_AXI/actions/runs/44488381423) L0 테스트 1 FAIL / 24 PASS. L1/L2는 SKIPPED.
- 메시지: test_ros_setup_nounset.py / .github/workflows/restaurant-ci.yml:127 `nounset not restored`.
- 진단: `set +u` 후 `/opt/ros/jazzy/setup.bash`와 `install/setup.bash`를 연속 source하고 한 번만 `set -u`를 적용. 기존 계약은 **각 source 직전/직후** `set +u`/`set -u`를 요구.
- 최소 수정: 두 source 각각 개별 `set +u → source → set -u`로 변경. 해당 구간 외 ROS·Gazebo·SLAM 코드 무변경.
- 재검: [Run #44488688236](https://github.com/silverbjin/samsung_AXI/actions/runs/44488688236) L0 test_ros_setup_nounset.py GREEN, L1 Jazzy 빌드 PASS, L2 실제 Gazebo SLAM→SaveMap→Map Server 재로딩 PASS. 수정 범위를 넘어간 ROS 동작 변경은 없음.
- 교육 포인트: CI 실패가 로봇 기능 문제인지 환경/계약 문제인지 로그 첫 실패 경계로 분리한다. 테스트 skip이나 경고 무시로 우회하지 않는다.
