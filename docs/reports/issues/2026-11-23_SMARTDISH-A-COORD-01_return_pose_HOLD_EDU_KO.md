# SMARTDISH-A-COORD-01 — 신규 DISH_RETURN 접근 Pose 검증 보류

- 날짜: 2026-11-23 KST
- 상태: **HOLD / ROS·Gazebo 물리 주행 NOT_RUN** (기존 소프트웨어 결함으로 단정하지 않음)
- 기준: S7 main `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`
- 담당: A Robot; 수신: D Mission Manager

## 1. 미충족 요구와 영향

SmartDish AI OFF는 `HOME → T03 → DISH_RETURN → HOME`의 실제 3-leg 이동이 필수입니다. 기존 S7은 `PICKUP_RETURN`이 HOME에 해당하는 2-leg만 검증했습니다. 기존 `src/restaurant_delivery/config/s3_map_waypoints.yaml`은 HOME(0,0,0)과 T03(5.25,0.38,-1.5708)의 map 좌표를 제공하지만 **별도의 DISH_RETURN은 없습니다**.

## 2. 관찰된 사실과 가설의 분리

- 사실: A 신규 `table_poses.yaml`에 `DISH_RETURN: {x: null,y: null,yaw: null}`.
- 사실: 계약 L0에서 `resolve_pose(...,"DISH_RETURN")`은 `UNCONFIGURED_DESTINATION`을 발생시키며 [#45118875792](https://github.com/silverbjin/samsung_AXI/actions/runs/45118875792) L0 PASS를 얻었습니다.
- 사실: `src/restaurant_world/config/tables.yaml`은 별도 World 좌표이므로 바로 `map` 목표로 사용하면 안 됩니다.
- 미확정: 어느 매장 통로가 반납 지점 접근에 적합한지, 장애물·Nav2 costmap/복귀 경로가 실제로 연결되는지, 현장 도면 실측 축척.
- 실물 Goal 실패 **관측 없음**: 아직 주행하지 않았기 때문입니다. 따라서 `NAV2_FAILED` 원인 분석 보고서가 아닙니다.

## 3. 선택한 안전 조치와 배제한 방법

좌표 0을 채우거나 픽셀→미터 비율을 임의 계산하지 않고 `null` 상태를 유지하며 요청 시 `FAILED/UNCONFIGURED_DESTINATION`을 발행하도록 했습니다. 이는 '목표를 모른다'는 상황을 '성공한 좌표'로 조작하지 않는 설계입니다. 이미 검증된 HOME/T03이나 기존 S7 안전 계층을 덮어쓰지 않았습니다.

## 4. 종료 조건 — 검증 작업 순서

1. 기존 S7 고정 map/AMCL/Nav2로 실제 Gazebo 기동; 사용한 World/Map/SHA 기록.
2. `map` 시야의 주방 카운터 인근 충돌 없는 통로에서 접근 Pose x/y/yaw 실측, 스폰·회전·Footprint Clearance 확인.
3. `table_poses.yaml` 업데이트, 계약 pytest L0 수행.
4. 실제 A 3-leg Nav2 Action `SUCCEEDED` 3건과 구간별 `/odom` 이동 로그 확인. Goal 미발행/실패 시 최초 오류만 수집.
5. D와 같은 `request_id` 3개 결과, 10초/5초 타이머 및 UI `COMPLETED`까지 확인하면 A+D AI OFF 완주 판정.

- 결과: 1~5 **아직 미실행 / L2 NOT_RUN**, 이 이슈는 HOLD.
- 임의 속도·RTF/FPS·GUI 렌더링 반복은 이번 완료 기준이 아닙니다.

## 5. 교육 포인트

좌표값의 출처와 좌표계는 알고리즘보다 먼저 검증해야 합니다. 코드가 성공해도 `map`이 아니라 `world`의 숫자라면 로봇은 엉뚱한 지점으로 갈 수 있습니다. 모르는 Pose를 `null`로 보존하고 미실행을 그대로 기록하는 것이 재현 가능한 개발 이력의 출발점입니다.
