# S2-MAP-01 — 실제 Gazebo SLAM 지도 생성·저장·재로딩
- 공식 재사용: ROS 2 Jazzy SLAM Toolbox, Nav2 Map Saver, Map Server Lifecycle. 새 SLAM/Planner 구현 없음.
- 공개 CI: S1 L2 실제 Scan/Depth → S2 /map + map→odom TF → 안전한 0.3m /odom 직진 → 공식 SaveMap 서비스 → YAML/PGM → Map Server reload OccupancyGrid.
- 성공 문자열: RESTAURANT_S2_L2_REAL_GAZEBO_SLAM_SAVE_RELOAD_PASS_NO_NAV_GOAL
- CI 짧은 이동은 **지도 파이프라인 검증**이지 전체 매장 지도 완성·AMCL·배달 시연 PASS가 아닙니다.

## 강사 WSL2 최종 전체 매장 매핑 (CI 성공 후)
  cd ~/samsung_AXI
  GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA bash scripts/restaurant_demo.sh mapping
기존 강사용 teleop으로 안전하게 통로를 관찰·탐색합니다. Gazebo 실행 중 다른 Ubuntu 터미널에서:
  source /opt/ros/jazzy/setup.bash
  source ~/samsung_AXI/install/setup.bash
  export ROS_DOMAIN_ID=58 GZ_PARTITION=restaurant_mvp
  ros2 topic echo /map --once --field info
  bash ~/samsung_AXI/scripts/s2_save_map_candidate.sh
결과는 maps/candidates/UTC/restaurant_map.yaml + pgm. 실제 지도를 RViz에서 확인한 경우에만 maps/restaurant_map으로 승격합니다.

## 실패 분리
scan 없음=브리지/물리센서, map 없음=slam_toolbox/TF, save 실패=Map Saver lifecycle, reload 실패=파일/Map Server lifecycle.
실패 시 로그는 기존 EVD-01 압축 증거 사용, docs/reports/issues 문제 해결 보고서에 최초 실패 경계 기록.
