# 강사용 DEMO-01 시연 / 단계별 진단

## 0. 5~10분 설명 흐름 (S1~S5 성공 뒤에 사용)

1. **월드** — “로봇의 경로 계산보다 먼저 바닥과 테이블이 물리 충돌체여야 합니다.” `./scripts/restaurant_demo.sh world` (처음에는 여기서 종료·점검)
2. **센서** — 다른 터미널 `ros2 topic echo /scan --once`; RGB는 `/camera/image_raw`, Depth는 S2 이후 `/restaurant/rgbd/depth_image`; 값이 실제로 변해야 합니다.
3. **SLAM·AMCL** — 저장된 `maps/restaurant_map.yaml` 로딩. 지도 계산과 주행은 다른 기능임을 설명합니다.
4. **배달/복귀** — `./scripts/restaurant_demo.sh demo NORMAL`. 실제 주행과 Action Result, 오도메트리 이동을 확인한 후 테이블 도착 시 Enter로 수령 확인합니다.
5. **안전·메뉴** — Gazebo GUI에서 `human_proxy`를 경로에 이동하여 실제 감속/정지/회피를 관찰합니다. 로봇과 장애물이 충돌하면 실패로 판단합니다. 별도 실행에서 `SOUP` 속도 제한을 확인합니다.
6. **종료** — `Ctrl+C` 이후 관련 데모 프로세스 종료를 확인합니다.

## 최초 실패만 확인

| 증상 | 확인 명령 / 범위 |
|---|---|
| GUI 빈 월드 | `tail -n 80 logs/world_*.log`, `gz sdf -k src/restaurant_world/worlds/restaurant.sdf`; `GZ_SIM_RESOURCE_PATH`·WSLg GPU 표시 |
| 로봇 안 움직임 | `ros2 topic info -v /cmd_vel`, `ros2 topic echo /odom --once`, `ros2 action list` |
| 지도 안 뜸 | `ros2 topic echo /scan --once`, `/tf`, `/clock`; `maps/restaurant_map.yaml` 생성 확인 |
| Depth 없음 | `gz topic -l | grep rgbd`와 `ros2 topic list | grep rgbd` 비교, optical frame 확인 |
| CM 반응 없음 | `ros2 lifecycle get /collision_monitor`; `ros2 topic echo /collision_monitor_state --once`; 실제 물리 `/scan` 및 RGB-D PointCloud 입력 확인 |
| 종료 후 잔존 | `ps -ef | grep -E 'gz sim|ros2 launch|restaurant_delivery'`; 데모가 소유한 프로세스만 종료 |

## 완료 체크리스트 (S1~S5 순차)

- [ ] M1 SDF 월드와 실제 Waffle Pi 모델 렌더링 + Collision
- [ ] M2 실제 LiDAR /scan → 지도 파일 저장·재로딩
- [ ] M3 AMCL/TF와 실제 로봇 위치 일치
- [ ] M4 실제 1→3→1 이동 + Nav2 Action Result + /odom + GUI
- [ ] M5 NORMAL/SOUP 서로 다른 주행 속도 적용
- [ ] M6 LiDAR·Depth ROS 실제 수신 + 안전 경로 입력
- [ ] M7 물리 장애물 감속·정지 또는 회피 → 제거 후 재개
- [ ] M8 원샷·Ctrl+C 종료 확인 및 설명 가능

**지금의 판정:** `RESTAURANT_ROBOT_MVP=NOT_RUN`. M1~M8 모두 성공하고 강사 WSL2 실제 관찰 근거가 있을 때만 `RESTAURANT_ROBOT_MVP=DEMO_PASS`를 기록합니다.
