# S4-MENU-CI02 — Gazebo 엔티티 생성 성공을 stderr 때문에 실패로 오인

- 원본 [Run #44651716546](https://github.com/silverbjin/samsung_AXI/actions/runs/44651716546), SHA dc7e8ca9331a79f764bc122db5a0d371c8abf56e.
- 정상/국물 모두 실제 Nav2 Action SUCCEEDED 및 Odom p75 속도 0.23 / 0.11m/s PASS.
- 이후 물리 안전 시험 준비용 공식 `ros_gz_sim create`가 `Entity creation successful.` 출력했지만, 확인 코드는 `created.stdout`만 읽음. ROS 2 CLI 로그가 `stderr`로 수집되므로 `S4_GAZEBO_FIXTURE_NOT_CREATED` 오류.
- 원인: 성공한 subprocess의 출력을 잘못 해석한 CI 성공 판정 버그. Gazebo 센서/정지 기능 자체 실패가 아님.
- 해결 후보: `returncode==0` 및 stdout·stderr 합산 메시지에서 정확한 `Entity creation successful` 동시 확인.
- 안전 STOP은 실행되지 않아 아직 미검증. 기존 메뉴 실주행 성공 증거는 보존, 스캔/충돌/물리 설정 변경 없음.
- 교육 포인트: subprocess를 이용한 외부 ROS/Gazebo CLI 판정에서는 exit code와 stdout/stderr를 분리 수집한 뒤 양쪽을 함께 해석해야 합니다.
