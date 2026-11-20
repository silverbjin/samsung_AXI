# OWNER-GUI-L3 — 강사 WSL2/WSLg 실제 Gazebo·RViz GUI 최종 검수 완료

- 검수 일시: **2026-11-20 KST** (진단 파일 UTC 시작: 2026-11-20T03:51:59Z)
- 사용자 승인: 첨부 GUI 화면과 현장 ZIP 제출 후 **검수 완료 처리 요청**.
- 대상 저장소: `silverbjin/samsung_AXI`
- 실행한 고정 소스: `a64b86c82f6b73d9a1cba5c808d5748acb351139`
- 원본 진단 ZIP(비공개/사용자 제공): `samsungaxi_gui_20261120T035159Z-2823.zip`
- 원본 ZIP SHA256: `06dda92b1560609b1b10582102d6ba4ede998885f9fc86e51383cc81bfdc85ef`
- 원본 ZIP은 장비/사용자 환경 정보가 들어 있으므로 **공개 GitHub에 업로드하지 않음**. 보고서에는 핵심 결과와 digest만 보존.

## 현장 L3 증거 및 판정

| 항목 | 현장 관측/원본 ZIP 근거 | 판정 |
|---|---|---|
| Gazebo Harmonic + 레스토랑 Waffle Pi | 강사 GUI 화면에 실제 월드·로봇 표시 | PASS |
| 새 S2-MAP-03 지도 사용 | Map Server PGM 202×185, 0.05m/cell, `maps/candidates/s2_map03/restaurant_map.yaml` 로딩 | PASS |
| 지도 관측 개선 | 별도 실제 SLAM CI #44664079567에서 81.333% known, 30,394셀; 원본 출고 지도 보존 | CI PASS / GUI 표시 PASS |
| 자동 AMCL initial pose | RViz `Localization: active`, `/amcl` lifecycle `active [3]`; 강사 수동 2D Pose Estimate 입력 없이 화면 정상; 별도 NO_MANUAL_PUBLISH L2 #44667491665 | PASS |
| Nav2 | RViz `Navigation: active`, `/navigate_to_pose` Action 목록에 존재 | PASS (NO_GOAL 세션) |
| 센서/안전 Node | `/scan`, `/odom` 실제 echo; `/collision_monitor` lifecycle `active [3]` | PASS |
| WSLg GPU | `gpu_probe.txt`: `D3D12 (NVIDIA GeForce RTX 3060)`, `Accelerated: yes`; 런처 메시지 `SAMSUNGAXI_WSLG_GPU_ROUTE=D3D12_NVIDIA_ACCELERATED` | PASS |
| Gazebo RTF | 사용자 GUI 실시간 표시 92.03%; Gazebo stats 100표본 중앙값 0.9992, 평균 0.96135, 하위 10% 0.6996, 표본 73/100이 >=0.90 | 목표 중앙값 >=0.90 PASS; 지속 RTF 보장은 미검증 |
| 종료 및 원본 증거 | `RUN_RC=130` / `SHELL_RC=130` Ctrl+C, ZIP 생성 완료 | 정상 운영 종료 |

### 보완 관찰 사항 (인수 차단 아님)
- RTF 하위 10% 값은 0.6996, 최소 0.2952. *순간 성능 저하가 완전히 해소됐다는 결론은 내리지 않음*.
- `environment.txt`의 기본 GLX는 `llvmpipe`이지만 별도 `gpu_probe.txt`/실행 시 **프로세스 한정 D3D12 가속**이 확인됨. GPU 전역 설정 변경은 금지.
- 기동 초기에 TF `base_link→odom/map` 대기 및 RViz GLSL 메시지가 있었음. 이후 Nav2/Localization ACTIVE, 실 Scan/Odom 수신으로 **기동 지속 실패의 증거는 없음**. 해당 경고의 발생 자체를 수정 완료했다고 주장하지 않음.
- `status.txt`는 프로그램이 사람의 GUI 화면을 판정할 수 없어 `WSL2_GUI_ACCEPTED=NOT_RUN_UNTIL_HUMAN_VISUAL_CHECK`라고 기록함. 이번 사용자 **직접 GUI 시각 검수 승인**과 ZIP 검토 결과를 결합하여 보고서의 최종 L3 승인을 부여함. 스크립트의 당시 상태 문자열은 변경/소급 조작하지 않음.

## 승인 경계

- **`OWNER_WSL2_WSLG_GUI_L3=ACCEPTED`** — 저장된 새 지도, 자동 AMCL, Gazebo/RViz 실제 장면, LiDAR/Odom 및 90% 중앙값 RTF 확인.
- **`RTF_MEDIAN_GE_90_PERCENT=PASS`**, **`RTF_P10_GE_90_PERCENT=NO`**. 안정적인 모든 표본 90% 이상이라는 판정 아님.
- **`LIVE_GOAL_DELIVERY_RETURN_L3=NOT_RUN`**, **`LIVE_MENU_SPEED_AND_COLLISION_STOP_L3=NOT_RUN`**. S3/S4 실제 Gazebo CI PASS 증거는 보존하며 이번 NO_GOAL GUI 시연으로 별도 실행되었다고 주장하지 않음.
- S2-MAP-01/02 및 원본 `maps/restaurant_map.*`, 새 S2-MAP-03 후보, S3/S4 기반 소스/CI 변경 없음.
- 본 보고서는 **상태/원본 custody만 기록**. 새로운 검사/주행/속도 검증을 허위로 수행했다고 주장하지 않음.

## 다음 권장 개발 단위: S5-LIVE-01 (MVP 최종 라이브 운영 통합)

공식 Nav2, Collision Monitor, `restaurant_demo.sh`, `delivery_manager`, 저장 지도 및 메뉴 정책을 재사용한다. 새 Planner/SLAM/모터 컨트롤러/YOLO 구현 금지.

1. **사전 확인**: S5 live-demo만을 위한 새 GUI 세션에서 S2-MAP-03 지도의 SHA/AMCL automatic pose, Nav2/CM ACTIVE, 실제 Scan/Odom와 TF 선행 조건을 검증한다.
2. **메뉴별 실제 주행**: NORMAL 배달(픽업→TABLE_3)→복귀, SOUP 저속 배달 또는 분리된 메뉴 비교를 기존 delivery manager/Nav2로 수행. /speed_limit와 /odom을 read-only 계측한다. 사용자의 명시적 라이브 Goal 승인 전 NO_GOAL 유지.
3. **안전 정지 시연**: 기존 Collision Monitor를 통한 안전 STOP 테스트 재사용. 장애물 접근 시 /scan → CM STOP → /cmd_vel 0 → /odom 물리 정지, Goal 취소 및 안전한 종료만 검수.
4. **증거 및 인수**: 한 세션 실행 로그·Action Result·메뉴 속도·안전 이벤트·RTF 및 화면 관찰을 compact ZIP으로 보존. 성공 조건 충족 시에만 `S5_LIVE_L3=ACCEPTED`로 판정.

발표/교육 목적에서는 **NO_GOAL GUI L3 승인**과 **실제 라이브 주행 L3 미인수**를 구분하여 안내한다.
