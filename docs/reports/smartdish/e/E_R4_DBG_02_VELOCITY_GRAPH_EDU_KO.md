# E-R4 DBG-02 — 실제 velocity graph 안전 게이트
## RED
Run [45937470292](https://github.com/silverbjin/samsung_AXI/actions/runs/45937470292), SHA 2e7cd5dffcb7eb3e62da4db1d25f42e358e79814, artifact 15171461641 (검증 ZIP SHA256 `4303fcb635b5715491fbd2dc34cf63a369b3a01bc2e0501cdf514606c67178dc`).
- CM inactive(2) → active(3), BT navigator inactive(2) → active(3), 각각 3.08/3.52초 소요. DBG-01의 수정 검증 성공.
- 다음 실패: E_R4_TIMEOUT_CM_SOLE_CMD_VEL. 실제 publisher 목록은 이전 증거에 없으므로 원인 미확정. Goal/leg/UUID 0, nav2 exit 0.
- 입력 nav2.yaml은 cmd_vel_smoothed → cmd_vel, ROS→GZ bridge이며 기존 S7 설정을 유지한다. Nav2 launch 내부 실제 endpoint는 추측하지 않는다.
## 조치
4개 velocity topic의 publisher/subscriber node, namespace, type, endpoint GID를 변동 시 로그 및 JSON에 기록하고 실제 설치된 nav2 navigation_launch.py를 증거에 포함. /cmd_vel sole collision_monitor 조건은 그대로 유지. 안전 확인 전 A TTY/Goal을 실행하지 않는다. 실제 endpoint를 근거로 필요 시 CI/공식 Nav2 remap을 독립 검토한다.
## GREEN 조건
기존 R4 게이트 전부 충족 또는 명확한 원인 증거. 이번 commit은 진단 강화이며 통합 PASS 주장이 아니다.
