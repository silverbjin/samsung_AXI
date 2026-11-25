# A-13-DBG-10 — 준비 장벽 리팩터링 후 정적 테스트의 잘못된 소스 시그니처 가정

- [CI #45325355574](https://github.com/silverbjin/samsung_AXI/actions/runs/45325355574), SHA `4fdd29bef2690a0e040371019b45ec57659867ab`: L0 `1 failed, 24 passed`, L1/L2 미실행.
- 첫 오류: `tests/test_smartdish_a_tray_runner.py::test_only_new_branch_and_unmodified_control`의 `assert runner.count('int(state["frame"].header.stamp.sec)*1_000_000_000+')>=2` (실제 0).
- 근본 원인: 이전 A-13 타이밍 경쟁 회귀 테스트가 Image timestamp inline 문자열이 두 번 나타나는 코드를 가정. 새 수정은 timestamp 비교를 `camera_ready()` 헬퍼로 통합했으므로 **동작과 무관한 문자열 개수 검사**가 거짓 RED를 만들었습니다. 실제 Gazebo 렌더링 실패의 근거가 아닙니다.
- 수정: `pre_event_ready(frame,clock_ns,pose_names,required_names)` 순수 함수를 분리하고 양의 stamp, clock≥stamp, 전체 Pose 명칭 조건을 **단위 테스트 5개 입력**으로 검증. 두 분기의 바이트 코드 문자열 모양을 요구하지 않도록 기존 정적 검사를 변경.
- 진단용 GZ image probe와 ROS callback 카운트는 유지. 실패한 테스트를 삭제하거나 skip하지 않았으며 실질 조건의 테스트 강도를 개선함.
- 다음 단계: 새 SHA L0 GREEN 확인→L1→실제 Gazebo L2. 실제 영상/물리 PASS를 선행 주장 금지.

## GREEN 재검

[GitHub Actions #45325486957](https://github.com/silverbjin/samsung_AXI/actions/runs/45325486957), 소스 `05779ae191ff41c922e067ec7cc5c2356dcffeaa`: **26 passed**, Jazzy L1 및 실제 Gazebo L2 네 장면 PASS. `pre_event_ready()` 정상/누락 Pose/클록 역전/제로 stamp 입력 L0 테스트 포함. 이전 RED는 테스트 계약 변경의 실패로 분리됐으며 Gazebo 원본 문제가 아님.
