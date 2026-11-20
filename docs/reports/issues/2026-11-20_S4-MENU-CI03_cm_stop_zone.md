# S4-MENU-CI03 — 실 LiDAR 전방 물체와 CM STOP 판정 불일치

- RED: https://github.com/silverbjin/samsung_AXI/actions/runs/44652530997
- 완료된 근거: NORMAL/SOUP 0.23/0.11m/s, 실제 NavigateToPose 왕복, Gazebo fixture 생성, 전방 26개 LaserScan 점 관측, upstream positive command 출력과 filtered cmd_vel 수신.
- 미해결: CM `S4ForwardStop` 상태 STOP 미관측. 로봇 물리 STOP을 임의 PASS 처리하지 않음.
- 전방 각도±0.48rad 0.65m 안에 26점이 있다는 것만으로 정지 구역의 x=0.10~0.58, y=±0.28 안에 4개 이상의 점이 있다고 단정할 수 없음. 센서 frame과 polygon base frame 정합도 고려.
- 단일 후보: 외부 물리 fixture 중심 로봇 GT 전방 0.60→0.52m로 이동. `stop_polygon_points()` 실제 스캔 XY 점 수, CM 상태 메타데이터, filtered output max 추가 수집.
- Nav2 CM stop action 및 LiDAR 원본은 유지, 별도 속도 모터 제어 개발 금지. 실물리 Gazebo 재검 전 HOLD.
- 교육 포인트: 센서가 전방 물체를 관측했다고 CM STOP zone 조건이 충족됐다고 가정하면 안 됩니다. 실제 점 좌표·CM state·filtered output을 함께 대조해야 합니다.
