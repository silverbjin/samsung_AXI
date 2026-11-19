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

## 성공 검증과 증거 확보
- [Actions #44488688236](https://github.com/silverbjin/samsung_AXI/actions/runs/44488688236)에서 실제 Scan·Odom·Map·map→odom TF 관측, 0.381m 이동, 공식 SaveMap 및 별도 Map Server 재로딩을 완료했습니다.
- Map ZIP `restaurant-s2-real-map-44488688236`는 CI 부분 지도와 축약 로그입니다. 전체 레스토랑 점유 지도 또는 배달용 최종 지도라고 주장하지 않습니다.
- **WSL2에서는 RAM 16GB / NVIDIA RTX 3060 전용 D3D12 경로**를 사용합니다. 기존 Gazebo 세션을 종료하고 **첫 번째 Ubuntu 터미널**에서 아래 명령을 사용합니다.

```bash
cd ~/samsung_AXI
export ROS_DOMAIN_ID=58 GZ_PARTITION=restaurant_mvp
GALLIUM_DRIVER=d3d12 MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA \
  bash scripts/restaurant_demo.sh mapping
```

두 번째 Ubuntu 터미널에서 `source /opt/ros/jazzy/setup.bash`, `source ~/samsung_AXI/install/setup.bash` 이후 `/scan`, `/map`·TF 확인, 안전한 수동 주행으로 필요한 영역을 충분히 관찰한 뒤 `bash ~/samsung_AXI/scripts/s2_save_map_candidate.sh`로 후보 지도를 저장하십시오. 생성 YAML·PGM과 RViz 지도 범위를 검토하기 전 `maps/restaurant_map.yaml`로 바로 덮어쓰지 마십시오.

### 로그 압축 — 기존 EVD-01 재사용
종료 후 `~/samsung_AXI/logs/mapping_*.log` 중 이번 세션의 로그를 선택해:

```bash
cd ~/samsung_AXI
mkdir -p logs/evidence
LATEST="$(ls -t logs/mapping_*.log | head -1)"
python3 scripts/samsungaxi_evidence_bundle.py \
  --root "$PWD" --session-log "$LATEST" --since-unix "$(stat -c %Y "$LATEST")" \
  --output "$PWD/logs/evidence/s2-map-$(date -u +%Y%m%dT%H%M%SZ).zip"
```

원본 Gazebo/ROS 로그는 삭제하지 않고 최대 300KB 단위 요약 ZIP을 생성합니다. *로그 압축 자체가 SLAM 인수 PASS를 뜻하지는 않습니다.*
