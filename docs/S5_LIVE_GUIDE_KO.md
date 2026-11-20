# S5-LIVE-01 — 강사 Gazebo·RViz 메뉴 배달·복귀 및 안전 STOP 라이브

## 범위
- 기존 실제 Gazebo S2-MAP-03 지도(81.33%), 공식 Nav2/AMCL, NORMAL/SOUP SpeedLimit 및 Collision Monitor를 재사용합니다.
- **동일한 Gazebo 세션**에서 픽업 → 테이블3(**NORMAL 0.23m/s**) → 픽업(**SOUP 0.11m/s**)을 실제 주행하고, 실제 물리 원통 fixture로 LiDAR Scan→CM STOP→최종 /cmd_vel 0→물리 /odom 정지를 검증합니다.
- 기존 `ci_s3_amcl_smoke.py --s5-integrated` 실증 경로 재사용. 새 Planner/SLAM/Supervisor/모터제어/YOLO 없음.
- 정지 시험에서는 **기존 S4 계약과 동일하게** Collision Monitor 상류 `/cmd_vel_smoothed`에 제한된 0.08m/s 시험 입력을 넣고, 최종 하류 `/cmd_vel`은 반드시 0이어야 합니다. 해당 테스트 직후 시험 입력은 0으로 복귀합니다.

## 강사 WSL2 GitHub 고정 SHA 원샷

**주의:** `PIN`은 S5 통합 공개 CI L0/L2 GREEN이 확인된 40자리 SHA여야 합니다. 인수 전에는 Goal 실행을 승인하지 마십시오.

```bash
(
  set -Eeuo pipefail
  PIN="d0738c56716390c52710767e7a3ac7b42d1966b5"
  SCRIPT="$(mktemp --suffix=.sh)"
  trap 'rm -f "$SCRIPT"' EXIT
  curl -fL --retry 3 --connect-timeout 10 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/samsungaxi_wsl2_gui_acceptance_once.sh" -o "$SCRIPT"
  bash -n "$SCRIPT"
  SAMSUNG_AXI_GUI_PIN="$PIN" bash "$SCRIPT" --self-test
  SAMSUNG_AXI_GUI_PIN="$PIN" bash "$SCRIPT" --s5-live --approve-goals
)
```

최초 CLI 승인 후에도 Goal은 전송되지 않습니다. Gazebo 화면에서 테이블 주변 안전 경로와 RViz Map·Robot TF·Navigation ACTIVE를 확인한 뒤, 실행 터미널의 질문에 정확히 **`YES-S5-LIVE-GOALS`**를 입력해야 합니다. 승인하지 않으면 NO_GOAL로 차단됩니다.

성공 후에도 Gazebo·RViz GUI를 유지합니다. 화면 확인 후 **Ctrl+C**로 종료하면 `~/samsungaxi_gui_evidence/`에 진단 ZIP 한 개를 보존합니다.

## 근거 및 판정

- `S3_NAV02_GOAL_SUCCEEDED=TABLE_3` 및 `PICKUP_RETURN`: 실제 Nav2 NavigateToPose Action Result와 물리 Odom 최소 이동거리, AMCL 도착 오차 검증.
- `S4_MENU_NORMAL_SOUP_REAL_ODOM_SPEED_PASS`: 각각 실제 Odom p75, 유효 샘플 수와 속도 차이.
- `S4_PHYSICAL_FIXTURE_LIDAR_POINTS` 및 `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS`: 물리 Gazebo fixture + 실제 LiDAR + Collision Monitor STOP + 필터 결과/물리 정지.
- `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS`: **동일 세션에서 모든 증거가 성공한 경우에만** 발행.
- JSON은 `generated/s5/<UTC-run-id>/s5_live_evidence.json`, 현장 ZIP에는 로그·RTF·GPU·ROS 정보·S5 JSON이 포함됩니다.

### 실패 시

`SAMSUNGAXI_DIAGNOSTIC_ZIP=...` 경로의 ZIP 한 파일을 첨부하십시오. `Ctrl+C`는 Goal 송신기의 ROS/Gazebo 자식 프로세스 그룹에 신호를 보내 정상 종료합니다. 강사 WSL2에서 실제 라이브 이동·정지·GUI 인수를 확인하기 전에는 `S5_LIVE_L3=NOT_RUN`입니다.

## 확정 CI 출고 증거 (현장 L3와 구분)

- [최종 통합 공개 CI #44673556772](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772), 검증 SHA `d0738c56716390c52710767e7a3ac7b42d1966b5`, L0/L1/L2 GREEN.
- 실 Gazebo TABLE_3 NORMAL Odom **5.194m**, AMCL 오차 0.138m; PICKUP_RETURN SOUP Odom **5.021m**, AMCL 오차 0.267m. 실제 Odom p75 NORMAL 0.23m/s, SOUP 0.11m/s.
- S4 기존 물리 원통과 실제 LiDAR 전방 29점, CM STOP 구역 29점, 공식 STOP 상태→/cmd_vel 필터 0→물리 /odom 정지 PASS.
- [Compact Artifact #14601770464](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772/artifacts/14601770464) (ZIP 4,718 bytes, SHA256 `b3fdf4eacd0e13eafd0660239e8f817e428fb89c710f7e4cf39027cdd4b868d7`).
- 새 경로의 소스는 L2에서 확인되었으나 **강사 WSL2의 실제 GUI 라이브 Goal은 NOT_RUN**입니다. ZIP에 기존 실행의 JSON이 혼입되지 않도록 S5 원샷은 UTC-run-id별 별도 증거 디렉터리를 사용합니다.
