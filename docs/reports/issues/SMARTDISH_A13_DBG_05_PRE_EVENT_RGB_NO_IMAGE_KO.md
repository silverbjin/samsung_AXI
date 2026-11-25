# A-13-DBG-05 — 실제 Gazebo 5Hz RGB 프레임 사전 캡처 실패

- 첫 L2 실제 실행: [Actions #45307436741](https://github.com/silverbjin/samsung_AXI/actions/runs/45307436741), 소스 SHA `883617696f0776071801a5860ffec265f922ee4f`.
- L0 **24 PASS**, L1 ROS Jazzy bridge/msgs/build **PASS**. L2 Gazebo 실제 실행 ST-01 시도 후 **FAIL**, `A13_PRE_EVENT_GAZEBO_CAMERA_NO_IMAGE`. B 이미지 파일/물리 결과 없음, 정상적으로 최종 PASS 발생 안 함.
- 검토한 경계: 원본 실행기는 Gazebo control로 `multi_step:5`를 최대 35번 호출, World `max_step_size=.001s`라면 누적 **0.175시뮬레이션초**. A-11 카메라는 5Hz라 첫 **양의** timestamp 프레임이 약 0.2초 이후에 나올 수 있음. **확인된 것은 프레임 미수신, 0.175초가 원인이라는 설명은 아직 가설**. Gazebo 토픽 광고/renderer/bridge 로그를 기존 L2 증거에 담지 않아 첫 결함 경계를 확정할 수 없음.
- 최소 수정 및 계측: 초기 stepping 90회 최대·처음 프레임/pose를 관측하면 즉시 중단, 0.3초 초과 시 포기. 프레임 부재 시 실제 sim_ns, Gazebo Image 토픽 광고 여부, dish Pose 이름을 first_error에 추가. CI `ERR` trap이 새 실행의 `gazebo.log` / `bridge.log`를 진단 부분에 출력.
- 데이터 안전: 최대 시간만 느슨하게 늘리는 대신 **실제 캡처 Pose가 원래 시나리오 식기에서 0.24m 이상 하강하거나 트레이 아래로 이미 떨어졌다면 `A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED`로 실패**. 시험 이름/이미지 사후 장면으로 물리 라벨 자동 승인 금지.
- L2 GREEN 확정은 후속 GitHub 실제 Gazebo camera+pose+4 trial 원본 성공 시에만 기록. 이 디버그 자체는 **원인 가설 분리 및 보정 후보**이며 검증 전 해결 완료로 주장하지 않음.
