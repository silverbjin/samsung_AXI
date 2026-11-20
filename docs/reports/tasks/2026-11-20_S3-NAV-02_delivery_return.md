# S3-NAV-02 — 저장된 레스토랑 지도에서 실제 Nav2 배달·복귀

- 일자: 2026-11-20 KST
- 시작 main: 62bceefd26e11d9d5d1ecb3fe642cdd6afc0f974
- 선행 PASS: S2-MAP-02 실제 SLAM 33.3m 지도 출고, S3-AMCL-01 실제 MapServer/AMCL/TF/Action server NO-GOAL Run #44561573820.
- 목표: 공식 Nav2 NavigateToPose를 사용해 1번 픽업→3번 테이블→1번 복귀 실제 Gazebo 도착 및 물리 Odom 이동 입증.
- 교정할 기존 문제: delivery_manager.py가 World 좌표(-2.60,-2.20)를 map 좌표로 전달했음. 출고된 S2 map 원점을 사용해 새 s3_map_waypoints.yaml (pickup 0,0 / table3 5.25,0.38)을 별도로 사용.
- 검수: 지도 SHA/Free 연결, AMCL pose/TF, Nav2 액션 서버 준비를 먼저 확인한 다음에만 실제 Goal 시작; Goal status SUCCEEDED, AMCL 위치 오차, 실제 Odom 이동을 각 구간별 확인.
- 정책: WSL2 지도 재생성·CI 성공 우회 금지, 새로운 Planner/SLAM/Safety Supervisor 금지, 기존 Nav2·Collision Monitor와 LiDAR 안전 경계 보존.
- 시작 상태: S3-NAV-02 actual Goal NOT_RUN. 본 파일은 개발 시작 문서이며 결과에 따라 업데이트.

## 구현 단계 1 — 공식 Nav2 Goal 추가(검증 전)
- 기존 S3-AMCL-01 NO GOAL 동작은 기본값으로 보존하고, 별도 --exercise-goals 옵션에서만 실제 NavigateToPose Goal 전송.
- 목표는 map table3=(5.25,0.38) 접근 → map pickup=(0,0) 복귀. 기존 World 좌표를 Nav2 Goal로 보내는 오류를 교정.
- 각 Leg의 ROS Action SUCCEEDED, 실제 Odom 1m 이상 변화, AMCL 목표 위치 오차 0.75m 이내, Scan 증가, 센서 신선도 검사. 실패 시 Goal cancel+HOLD. Collision Monitor/SLAM 미변경.
- 실제 Actions 검수 전 S3-NAV-02=NOT_VERIFIED.

## S3 독립 CI 구축
- 기존 검증된 S2 33.3m 지도 생성을 반복하지 않고 S3 전용 워크플로에서 L0 맵 SHA 계약, L1 공식 Jazzy 빌드, L2 저장 지도 AMCL 사전검사 후 NavigateToPose TABLE3→PICKUP_RETURN을 실주행.
- 성공 로그 RESTAURANT_S3_NAV02_REAL_GAZEBO_DELIVERY_RETURN_PASS는 실제 Actions 출력이 확인되어야만 유효. 빌드/정적 문자열만으로 성공 주장 금지.

## Cycle 01 — S3 NavigateToPose 첫 Goal 거절 (RED)
- [Actions #44563771148](https://github.com/silverbjin/samsung_AXI/actions/runs/44563771148): L0 지도/좌표·L1 Jazzy build·L2 기존 AMCL NO GOAL 모두 GREEN, 추가 S3-NAV-02 첫 TABLE_3 Goal `NAV_ACTION_GOAL_REJECTED_TABLE_3`.
- 최초 실패 경계: Goal이 서버에서 거절됐으며 로봇 물리 주행은 아직 시작되지 않음. `ci-s3-summary.txt`에는 lifecycle_manager_navigation이 planner_server 구성 작업을 진행 중이었고 bt_navigator/Collision Monitor 등이 아직 Waiting on external lifecycle transitions로 기록됨.
- 근본 원인: NavigateToPose **서버 discovery**는 완료되었지만 Nav2 실제 Lifecycle **ACTIVE**를 기다리지 않아 첫 Goal을 너무 일찍 제출함. Action 서버 존재와 Lifecycle 활성화는 다른 인수 게이트.
- 최소 수정: S3-NAV-02 `--exercise-goals` 활성 시에만 bt_navigator/planner_server/controller_server/collision_monitor/behavior_server의 공식 `GetState` 서비스 결과 ACTIVE(3) 확인 후 Goal 허가. 150초 범위 내 활성화 안 되면 HOLD (Goal 미전송).
- AMCL NO-GOAL 검증 기준·원본 지도·SLAM·0.40m 안전 조건·Goal 도착 판정은 변경하지 않음. 재검 전 NAV-02=NOT_VERIFIED.

## Cycle 02 — Nav2 Lifecycle 게이트 수정 → 실제 Gazebo L2 GREEN
- 검증 코드 SHA `22d19347a3b76446495c1d5bfddb71280c160456`, [Actions Run #44564927414](https://github.com/silverbjin/samsung_AXI/actions/runs/44564927414), L0 map SHA/coordinate tests PASS, L1 ROS Jazzy build PASS, 기존 AMCL NO GOAL L2 PASS, 신규 S3-NAV-02 실주행 L2 PASS.
- 최초 관찰: `S3_NAV02_LIFECYCLE_ACTIVE_PREGOAL=bt_navigator,planner_server,controller_server,collision_monitor,behavior_server` 이후 첫 TABLE_3 Goal 수락.
- TABLE_3: Action `STATUS_SUCCEEDED=4`, 실제 odom 최대 변위 5.185m, AMCL 도착 추정 (5.1790,0.2014), 목표 (5.25,0.38), 거리 오차 0.192m, 추가 Scan 146개.
- PICKUP_RETURN: Action `STATUS_SUCCEEDED=4`, 실제 odom 최대 변위 5.214m, AMCL 도착 (-0.0160,-0.0644), 목표 (0,0), 거리 오차 0.066m, 추가 Scan 298개.
- 원본 증거 Artifact `samsungaxi-s3-amcl-verified-44564927414`: `generated/s3/nav_delivery.json`, `generated/s3/amcl_preflight.json`, 축약 로그. 저장 지도 PGM SHA `b20bebc872145fa674315757c61e5bb10444eb4c5067ac34d5948d679157e8d8` 동일.
- 지도 재생성·안전 게이트 완화·새 Planner 개발 없이 기존 실패 경계인 Nav2 Lifecycle 활성 판정만 교정해 해결.
- **한계:** CI 전용 NavigateToPose 주행·복귀 검증이며 `restaurant_delivery` 메뉴별 속도 정책, 실측 주행 안전거리, 강사 WSL2 GUI 최종 인수는 별도 검증 대상.

## Cycle 03 — 증거 스키마 정합 및 main 회귀 연결
- 성공 Run의 `nav_delivery.json`은 `goal_sent=true`, `delivery_return=true`임에도 기존 NO-GOAL 프리플라이트 딕셔너리에서 `kind=s3_real_gazebo_no_navigation_goal`을 그대로 이어받았음. **동작 실패가 아니라 결과 메타데이터 명칭 불일치**.
- 후속 실행 결과에서 Goal 2구간 성공 시에만 `kind=s3_real_gazebo_navigation_delivery_return`로 교정. 이전 원본 Artifact는 수정하거나 재해석하지 않고 보존.
- S3 전용 Actions가 main에도 작동하며 실제 NAV-02 주행을 검사하도록 workflow branch와 조건을 최소 확장. 코드·보고서 병합 후 main CI에서 최종 확인.
