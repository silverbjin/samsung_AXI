# OWNER-AUTOPOSE — WSL2 GUI 2D Pose Estimate 자동화
- 기준: S2-MAP-03 81.33% 물리 지도 후보 실제 Gazebo Run #44664079567 + S3 candidate two-action GREEN #44666192437.
- 문제: RViz 화면에서 강사가 2D Pose Estimate 버튼을 눌러야 초기 AMCL pose가 확보됨.
- 조치: 기존 `prepare_nav2_params.py --auto-initial-pose`에만 공식 AMCL `set_initial_pose: true`, `initial_pose: {x:0,y:0,z:0,yaw:0}` 적용. GUI navigation 모드에서만 개선 지도 `maps/candidates/s2_map03/restaurant_map.yaml` 사용하고 자동 활성. 기존 기본 원래 지도/S3/S4 CI 주행 모드 및 메뉴 로직은 불변.
- 재현 실패 경계: 별도 초기 위치 주입을 전혀 하지 않았을 때 AMCL pose/TF가 생성되는지 실증해야 함.
- 실제 공개 CI: [Run #44667491665](https://github.com/silverbjin/samsung_AXI/actions/runs/44667491665), L0 PASS, official ROS Jazzy+Nav2+Gazebo Harmonic L1 PASS, 실제 Gazebo L2 PASS.
- 실제 로그: `S3_REAL_GAZEBO_RELEASED_MAP_AND_SENSORS_PRESENT`, `S3_AMCL_AUTO_INITIAL_POSE_REAL_GAZEBO_PASS_NO_MANUAL_PUBLISH`, `RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL`.
- Evidence Artifact [#14598930979](https://github.com/silverbjin/samsung_AXI/actions/runs/44667491665/artifacts/14598930979), ZIP SHA256 `4f2397f9fe5656e1500e69f9eb7ec526c584775ddc58bf415e65d12d08fb7256`.
- USER GUI 시각 확인: NOT_RUN. 자동 초기 위치는 고정 Gazebo 출발 위치와 지도 출고 좌표가 일치하는 현 시나리오에 한정. 다른 로봇 출발 위치에서는 정확한 pose가 별도로 필요.
- NO_GOAL: GUI owner runner에는 자동 NavigateToPose 전송 없음. RTF 90% 목표는 다음 별도 단계.
