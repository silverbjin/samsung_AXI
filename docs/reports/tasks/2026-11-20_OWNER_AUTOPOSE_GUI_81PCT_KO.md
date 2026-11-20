# OWNER-AUTOPOSE — 개선된 S2-MAP-03 지도와 공식 AMCL 자동 초기 위치

- 원본 지도 `maps/restaurant_map.*` 및 기존 S2/S3/S4 PASS 불변.
- 개선 지도 `maps/candidates/s2_map03/restaurant_map.yaml`: 별도 실제 Gazebo SLAM 81.33%, S3 Action 왕복 Run #44666192437 PASS.
- 변경: `restaurant_demo.sh`의 `navigation` GUI 모드에서 개선 지도 선택, 공식 Nav2 AMCL `set_initial_pose: true`, `initial_pose` `(map.x=0,y=0,yaw=0)`를 GUI params overlay에서만 활성화. 기존 `demo`, CI 기본 모드는 그대로.
- 공식 참고: https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/others/configuring-amcl/
- 증거: [전용 CI #44667491665](https://github.com/silverbjin/samsung_AXI/actions/runs/44667491665) L0 PASS, L1 PASS, 실제 Gazebo L2 PASS; `S3_AMCL_AUTO_INITIAL_POSE_REAL_GAZEBO_PASS_NO_MANUAL_PUBLISH`, `RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL`.
- [Compact Artifact #14598930979](https://github.com/silverbjin/samsung_AXI/actions/runs/44667491665/artifacts/14598930979), 3,780 bytes, ZIP SHA256 `4f2397f9fe5656e1500e69f9eb7ec526c584775ddc58bf415e65d12d08fb7256`.
- GUI 스크립트: `SAMSUNG_AXI_GUI_PIN=<검수된_40자리_SHA>`를 명시하여 새 코드를 다운로드; 기존 원샷 진단 ZIP 유지.
- **OWNER_AUTOPOSE_CI=PASS**, **WSL2_GUI_L3=NOT_RUN**. GUI 스크린샷/시각 확인 없이 최종 인수 주장 금지.
- 후속: RTF 0.60~0.70 → 목표 >=0.90 실측과 WSLg D3D12 최적화. 단계 3은 별도 검수.
