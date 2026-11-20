# S5-LIVE-01 — 공개 CI + 강사 WSL2 단일 세션 통합 라이브 개발

- 기준 main: `b478e8508d60e74e701f347e54b8ba0ec1724cbc`.
- 원본 성공 보존: S2-MAP-01/02, S2-MAP-03 81.33% 실제 SLAM 지도, 새 지도 S3-AMCL/Nav2 배달·복귀, S4 메뉴 속도/Collision Monitor STOP, 강사 NO_GOAL GUI L3.
- 이번 단계는 이미 성공한 각각의 기능을 다시 구현하지 않고 **동일한 실제 Gazebo 세션**에서 연결합니다.

## 설계

1. 개선 지도 원본 SHA/World SHA/Free 연결성 검사 및 공식 AMCL 자동 초기 위치. `/initialpose` 수동 발행 금지.
2. 기존 `ci_s3_amcl_smoke.py`를 `--s5-integrated`로 재사용: 실제 센서·Nav2 Lifecycle 확인 뒤 NavigateToPose TABLE_3 (NORMAL)와 PICKUP_RETURN (SOUP), 실제 Odom 속도 비교.
3. 동일 세션에서 기존 S4 물리 원통 장애물 STOP, `/scan`→`CollisionMonitorState.STOP`→`/cmd_vel` 0→`/odom` 정지.
4. 강사 GUI에서 `owner_wsl2_once.sh live` 재사용. Goal 안전 승인 2단계: `--approve-goals` CLI + 터미널 `YES-S5-LIVE-GOALS`; 실패/취소 시 Goal 없음.
5. 기존 RTF/GPU 계측과 단일 진단 ZIP에 S5 JSON 및 최초 실패 요약 추가. GUI는 실제 실행 후 Ctrl+C까지 유지.

## 검증/출고 게이트

- L0: Python/Bash 계약 및 승인 차단 RED→GREEN.
- L1: 공개 CI 공식 Jazzy/Harmonic/ROBOTIS Waffle Pi/Nav2 빌드.
- L2: **같은 실제 Gazebo 세션**의 두 Nav2 Action, 메뉴별 실제 Odom 속도, 물리 장애물 CM STOP·필터·Odom 정지. 모든 증거가 증명됐을 때만 `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS`.
- 강사 WSL2 GUI L3: 사용자 현장에서만 검사. CI GREEN을 GUI L3 PASS라고 주장하지 않음.
- 스크립트 외 새 Planner·SLAM·Supervisor·안전 알고리즘/드라이버는 없음.

## 개발 이력

- S5 브랜치 `feature/s5-live01-integrated-20261120` 생성. 원샷·원본 S3/S4 실증 실행기 재사용, 실증 코드·CI·안전 승인 회귀·가이드만 최소 수정.
- 첫 CI 판정은 `S5_CI=HOLD`이며 실제 L0/L2 결과를 이 보고서에 추가한 뒤 승인/병합 결정.

## Cycle 01 — 첫 L0 RED→최소 수정 GREEN, 실제 Gazebo 통합 PASS

- [RED Run #44672666575](https://github.com/silverbjin/samsung_AXI/actions/runs/44672666575): L0의 기존 GUI 원샷 테스트가 오래된 `"$OWNER" navigation NORMAL` 직접 호출 문자열을 요구, 안전한 `OWNER_ARGS` 인수 배열로 이미 바뀐 실제 코드와 불일치. ROS 물리 기능 실패가 아니라 낡은 테스트 계약. 새 통합 L0 안전 계약은 통과.
- 수정: `tests/test_gui_owner_one_shot.py`의 기존 기대 문자열만 `OWNER_ARGS=(navigation NORMAL` 및 `setsid bash "$OWNER" "${OWNER_ARGS[@]}" &`로 변경. 주행/센서/안전 로직 불변.
- [GREEN Run #44672828318](https://github.com/silverbjin/samsung_AXI/actions/runs/44672828318): L0/L1/L2 PASS, 검증 SHA `213f43f4df92233fa23a1a94e5d31ce278de4c4c`. 실제 TABLE_3 5.209m / AMCL 오차 0.092m, PICKUP_RETURN 5.224m / 오차 0.052m, 두 실제 속도 p75 0.23/0.11m/s, 전방 LiDAR/STOP 폴리곤 29점, 최종 CM STOP PASS.
- 이번 S5은 최초로 한 세션의 S3 주행·S4 메뉴속도·CM 물리 STOP을 결합해 인수. 기존 별개 S3/S4 성공을 같은 세션 결과로 꾸미지 않음.

## Cycle 02 — 강사 TTY 입력·반복 증거 혼입 방지, 공개 CI 최종 GREEN

- 강사 원샷은 ROS 프로세스를 백그라운드 세션 그룹으로 소유합니다. 비대화형 Bash의 백그라운드 표준입력이 `/dev/null`로 전환될 수 있으므로, **S5에 한해** `</dev/tty` 연결을 명시했습니다. 실제 Goal은 CLI `--s5-live --approve-goals` + 터미널 `YES-S5-LIVE-GOALS` 승인이 모두 있어야 합니다.
- 이전 실행의 `s5_live_evidence.json`이 실패 ZIP에 섞이지 않도록 `SAMSUNGAXI_S5_RUN_ID` 실행 ID별로 `generated/s5/<run-id>/`에 증거를 기록하고, ZIP에는 해당 실행의 JSON/요약만 복사하도록 개선. 기존 성공 로그를 삭제하지 않음.
- [최종 GREEN Run #44673556772](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772), SHA `d0738c56716390c52710767e7a3ac7b42d1966b5`: **L0 24개 PASS, L1 공식 Jazzy/Nav2/Gazebo 빌드 PASS, L2 동일 실제 Gazebo 세션 PASS**.
- TABLE_3 NORMAL Action SUCCEEDED, 물리 Odom **5.194m**, AMCL 도착 오차 **0.138m**. PICKUP_RETURN SOUP SUCCEEDED, Odom **5.021m**, AMCL 오차 **0.267m**. 실제 Odom 속도 p75 **0.23/0.11m/s**.
- 실제 LiDAR/CM STOP 폴리곤 **29점**, `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS` 및 `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS` 모두 발생. 하류 속도/물리 변위 상한은 기존 S4 Fail-closed 계약 그대로 유지.
- Compact Artifact: [#14601770464](https://github.com/silverbjin/samsung_AXI/actions/runs/44673556772/artifacts/14601770464) (4,718 bytes, SHA256 `b3fdf4eacd0e13eafd0660239e8f817e428fb89c710f7e4cf39027cdd4b868d7`).
- **판정 `S5_LIVE01_CI=PASS`**, `S5_OWNER_WSL2_L3=NOT_RUN`. 실제 GUI에서 Goal 승인/화면/RTF/STOP 확인은 강사 현장 인수로 별도 실행해야 합니다. CI는 headless Xvfb/llvmpipe이며 WSLg 성능 근거가 아닙니다.
