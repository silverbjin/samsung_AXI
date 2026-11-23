# S6 G09 — Nav2 서비스 응답 지연·초기화 경합 최소 개선 교육 보고서

2026-11-23 / 새 브랜치 `fix/s6-nav2-controlplane-stability-20261123` / 기존 S6 기능 성공 SHA `937fbf025cefec01489c40bc5104c39e3d4709be`는 불변.

## RED: 별개의 두 최초 실패
- [CI #45104473441, Attempt 1](https://github.com/silverbjin/samsung_AXI/actions/runs/45104473441): TABLE_3 Action SUCCEEDED와 Vision STACKED까지 정상. PICKUP_RETURN 4.8596m 후 Action status 6(ABORT), AMCL error 0.3774m. `bt_navigator`의 `Timed out while waiting for action server to acknowledge goal request for follow_path`가 최초 실패. 로그는 controller 20Hz loop missed 경고 다수. 안전 STOP 최종 검증은 이 세션에서 NOT_RUN.
- [동일 CI Attempt 2](https://github.com/silverbjin/samsung_AXI/actions/runs/45104473441): Goal 전 200초 `TIMEOUT_CLOCK_SCAN_ODOM_RELEASED_MAP`. map_server `/map_server/change_state` response timeout 후 `planner_server` lifecycle bringup 실패, `/map` TF 없음. 이 2차 실행은 AI·Goal에 도달하지 못함.
- 첫 시나리오는 성공과 실패가 섞여 있으므로 두 시도 중 한 번만 성공했다고 전체 L2 PASS로 처리할 수 없습니다.

## 외부 근거와 원인 미확정
- 공식 Jazzy [BT Navigator 문서](https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/configuring_bt_navigator/)에는 `default_server_timeout=20ms`가 BT Action Goal 수락 대기 기본 설정으로 명시됩니다. 실제 실패는 이 단계에서 발생해 조정 후보로 판단합니다.
- 공식 Jazzy `nav2_lifecycle_manager` 소스에는 최신 main의 `service_timeout` 파라미터가 없으므로 **검증되지 않은 파라미터 추가를 금지**합니다. ROS Jazzy 코드: https://raw.githubusercontent.com/ros-navigation/navigation2/jazzy/nav2_lifecycle_manager/src/lifecycle_manager.cpp.
- [Upstream Issue #6556](https://github.com/ros-navigation/navigation2/issues/6556)은 lifecycle 서비스 응답 타임아웃과 과중한 CPU·DDS 초기화 경합을 논의합니다. 이번 CI의 CPU가 실제로 과부하였는지는 계측되지 않아 **원인은 여전히 가설**입니다.

## GREEN 후보: 바꾸는 부분과 바꾸지 않는 부분
- scripts/prepare_nav2_params.py에 `--s6-bt-ack-ms 200` 옵트인: BT Goal 수락 대기만 20→200ms. LiDAR Collision Monitor, 주행 속도/Goal tolerances, Planner, controller frequency 및 지도는 변경하지 않음. S5 기존 기본값 20ms 보존.
- navigation.launch.py에 `s6_stagger_nav_start` opt-in: S6에서 Gazebo 서버와 ROS 센서가 시작된 뒤 Nav2 stack launch 10초 지연. S5 기본값 false: 기존 Nav2 시작 경로 유지.
- scripts/ci_s3_amcl_smoke.py는 S6 실행일 때만 stagger 인수 전달. scripts/restaurant_demo.sh도 S6 live에서만 200ms 설정.
- S6 실제 Gazebo L2 workflow에서 새 opt-in 설정을 확인하고 실제 TABLE_3 → RGB STACKED → PICKUP_RETURN → LiDAR STOP을 반복 없이 1회 수행합니다.

## RED → GREEN 게이트
- L0: 입력 유효범위 20~500ms, 미지정=원본값 20ms, 기존 S5 기본 Launch 경로, 별도 S6 TimerAction 계약.
- L1: Jazzy 공식 Nav2 params에서 bt_navigator.default_server_timeout ==200, local_costmap.observation_sources=scan, Collision Monitor 원본 안전 설정 동일.
- L2: 2개 real Nav2 Goal, 실제 카메라 이미지+모델, 물리 STOP과 완전한 증거가 동시에 PASS여야 GREEN.
- 실제 WSL2 Qt/WSLg OpenGL 회귀는 별도 GUI L3. RTF 90% 및 Vision 범용 일반화는 HOLD.

## 주니어 개발자 퀴즈
1. `map_server`가 이미 INACTIVE에 도달했더라도 lifecycle 서비스 응답이 타임아웃되면 어떤 상태가 될 수 있습니까? 실제 `get_state`를 관측해야 알 수 있습니다.
2. `default_server_timeout`을 200ms로 증가하는 것은 주행 제한 속도나 정지 임계값 변경인가요? 아닙니다. Nav2 내부 Action 승인 통신만 변경합니다.
3. Nav2가 너무 빨리 시작되는 부하를 줄이기 위해 10초를 지연하면 무엇이 증명되나요? 아직 없습니다. CI의 실제 런타임 근거가 필요합니다.

## 상태 (개발 직후)
코드/교육 보고서 커밋 완료. G09 신규 L0/L1/L2=PASS(같은 기능 시나리오의 CI 실증). WSL2 L3=NOT_RUN. Main 병합 HOLD.

## GREEN — 새 SHA의 실제 Gazebo L2 원본 확인 (2026-11-23)
- L0 최초 `966029e...`는 test 파일의 Python 문자열 인용 오류로 실패. 최소 수정 `9d402a991d1ee0a1c46027abe91a55266b69d9bd` 후 정적 L0 PASS.
- [실제 Gazebo S6 Run #45106929216](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216), 검증 런타임 SHA **`9d402a991d1ee0a1c46027abe91a55266b69d9bd`**. L0/L1/L2 모두 SUCCESS.
- TABLE_3 Action SUCCEEDED 5.137m, AMCL error 0.206m, Scan 241개 추가; 실제 도착 후 정지 확인 다음 RGB 320×240 **3프레임** 수신.
- Vision `STACKED`, confidence `0.6652`, image SHA256 `4922a3f48d75ceb8206e67b20c54b35b54595a2eb51649f5566f827d6454e7a5`; 이 판정 뒤에만 PICKUP_RETURN Goal 전송.
- PICKUP_RETURN Action SUCCEEDED 5.054m, AMCL error 0.160m; NORMAL/SOUP p75 = 0.23/0.11m/s.
- LiDAR 장애물 29점 → CM STOP, 필터링 `/cmd_vel` 최대 0.0m/s(68개 표본), 정지 중 Odom 이동 0.0m. `S6_VISION_REAL_GAZEBO_L2_INTEGRATED_PASS` 및 `S6_REAL_GAZEBO_TABLE_VISION_RETURN_L2_PASS` 확인.
- [원본 Artifact #14787673933](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216/artifacts/14787673933) ZIP SHA256 `a9ee749ef91586b27a19de04e6e2cc902176701d3f66971c4225ab1a96cd528c`; 생성된 `nav2.yaml` BT `default_server_timeout=200`, Local Costmap scan-only, CM cmd_vel_smoothed→cmd_vel 증명.
- 제한: 해당 1회 실증 PASS는 OpenGL/NVIDIA/WSLg 직접 검증이 아니며 첫 두 실패가 장기적으로 절대 재발하지 않는다는 통계적 증거도 아닙니다. 그러나 기존 실패 경계가 없는 완전한 실제 L2 주행 성공을 확보했습니다.
