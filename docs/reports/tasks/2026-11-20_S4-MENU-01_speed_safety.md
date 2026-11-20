# S4-MENU-01 — Nav2 메뉴별 속도 제한·Collision Monitor 실제 안전 정지

- 작성일: 2026-11-20 KST
- 시작 main: `d526ca6c818990db6656fe75afa9ca6cd970c6af`
- 선행 불변 PASS: S2 실제 SLAM 33.3m 지도 출고, S3 배달/복귀 Nav2 CI main Run #44646848087, S1/S2 통합 회귀 Run #44646848122.
- 목표: 기존 Nav2 MPPI Controller Server + Collision Monitor 재사용. NORMAL 0.23m/s vs SOUP 0.11m/s 정책을 유지하면서 실제 Gazebo Odom 속도 분포 차이와 장애물 접근 시 CM STOP 출력/정지 동작 검증.

## 최초 소스 조사
- `delivery_manager`는 이미 `/speed_limit`에 `nav2_msgs/SpeedLimit(percentage=False)` 메시지를 보내지만, 공식 Jazzy Controller Server 기본 `speed_limit_topic`은 상대 `speed_limit`입니다. 기본 동작에서 매칭을 보장할 수 없으므로 overlay에 `/speed_limit` 명시 필요.
- 공식 nav2_bringup Jazzy collision_monitor는 `cmd_vel_smoothed` → `cmd_vel`, 실제 scan 소스, `FootprintApproach`만 기본 활성. 안전 정지를 객관적으로 확인할 최소 `S4ForwardStop` polygon을 기존 CM에 추가. 새로운 planner/control 노드 없음.
- 근거: https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/controller_server/ 및 https://docs.nav2.org/jazzy/configuration_and_development/configuration_guide/core_servers/collision_monitor/configuring_collision_monitor_node/.

## 최소 CI 검수
- L0: SpeedLimit 토픽 일치, 메뉴 정책 값, CM input/output/실 Scan source, 정상/잘못된 Odom 속도 판단 계약.
- L1: ROS Jazzy/ROBOTIS 고정 버전 및 Nav2 파라미터·프로젝트 빌드.
- L2: 단일 실제 Gazebo Map→AMCL/TF→Lifecycle ACTIVE→TABLE3(NORMAL)→PICKUP_RETURN(SOUP) 실제 Action 성공, 각 구간 Odom 속도 분포·도착·Scan 수신.
- 안전 정지: 실제 Gazebo 고정 원통 fixture를 로봇 전방 안전 구역에 생성하고 실제 LiDAR와 공식 CM state STOP, `cmd_vel_smoothed` positive 입력→`cmd_vel` 0, 물리 Odom 정지 확인. 신호/토픽/fixture 증거 없으면 FAIL.
- 테스트 fixture는 ROS/Gazebo 실제 물리 모델이며 원본 World나 지도 파일을 수정하지 않음. 정상 주행과 별도 시험에서 사용하는 경미한 단일 입력으로 한정.
- 소형 로그/JSON 증거 ZIP만 CI Artifact 보존. 실패 시 최초 실패 경계 보고서 동시 작성.

## 판정
- **S4=CI_ACCEPTED (composite evidence)**: 실제 메뉴별 속도 실증 Run #44651716546/#44652530997과 독립 실제 Gazebo 안전 STOP Run #44655038709를 연결한 CI 범위의 승인. 같은 세션의 메뉴+STOP 동시 성공이라는 주장은 하지 않음.
- 강사 SAMSUNGAXI WSL2에서는 CI 검증 SHA를 가져와 GUI 최종 인수만 수행하며 재매핑·대규모 환경 최적화 금지.

## Cycle 01 — L0 RED: 과거 S3 CI 분기 계약 불일치
- [Actions Run #44651503909](https://github.com/silverbjin/samsung_AXI/actions/runs/44651503909): L0 pytest 14 PASS / 1 FAIL, L1/L2 SKIPPED.
- 최초 실패: `tests/test_s3_nav_contract.py::test_nav02_ci_uses_one_gazebo_session_for_pregoal_and_goals`가 S3 NAV-02의 과거 브랜치 조건에 `main` 포함을 요구.
- S4에서는 main의 주행 검사를 S4 메뉴·안전 통합으로 대체(내부 S3 pregoal+Goal 유지)하므로 **과거 기대 문자열만 낡음**. 신규 S4 메뉴/CM 계약 자체는 PASS.
- 최소 수정: S3 브랜치에서는 S3 목표 인수 유지, main/S4에서는 S4 속도·정지 검수한다는 분기 정책에 맞춰 L0 계약 1건 수정. 주행/안전 로직 변경 없음.
- 재검 L0/L2 GREEN 전 S4=HOLD.

## Cycle 02 — 정상·국물 메뉴 속도 L2 PASS, Gazebo 생성 성공 메시지 파싱 RED
- [Run #44651716546](https://github.com/silverbjin/samsung_AXI/actions/runs/44651716546) L0 전체 PASS / L1 공식 ROS Jazzy+Nav2 build PASS / 실제 Gazebo 2구간 배달·복귀 Action SUCCEEDED.
- NORMAL 실제 /odom p75=0.23m/s, TABLE_3 odom 이동 5.133m / AMCL error 0.209m. SOUP 실제 /odom p75=0.11m/s, PICKUP_RETURN 5.074m / error 0.117m. **메뉴별 실측 속도 차이 0.12m/s (약 52% 저감) PASS**.
- 이후 안전 검사 준비 중 `ros2 run ros_gz_sim create`는 실제로 `Entity creation successful.`을 로그에 보고했으나 CI 검사기는 `created.stdout`만 확인했고 메시지는 stderr에 출력되어 `S4_GAZEBO_FIXTURE_NOT_CREATED` 오판.
- 첫 실패 경계: ROS GZ 실제 fixture 생성 실패가 아닌 CLI 성공 메시지 출력 스트림 검사 오류. 아직 Collision Monitor STOP 결과는 관측되지 않았으므로 S4 전체 PASS는 보류.
- 최소 수정: subprocess 종료 상태 rc=0 및 stdout+stderr를 합산해 `Entity creation successful`을 확인. 생성/삭제 API, SDF/World, Nav2·LiDAR/CM 속도 정책 변경 없음.
- 이후 실제 CM STOP, 필터링된 `/cmd_vel` 제로, /odom 정지를 다시 검증해 RED→GREEN 결과 확정.

## Cycle 03 — 실제 LiDAR 26점 확인, STOP 상태 미확인
- [Run #44652530997](https://github.com/silverbjin/samsung_AXI/actions/runs/44652530997): L0 PASS, L1 공식 Jazzy/Nav2 PASS, L2 NORMAL 0.23m/s/SOUP 0.11m/s p75 및 두 구간 실제 Action/Odom PASS.
- `s4_collision_fixture` 실제 Gazebo 생성 성공, 전방 LiDAR 유한 거리점 26개 수신, 테스트 상류 `cmd_vel_smoothed` 양의 속도 입력과 하류 `/cmd_vel` 125개 관측 확인.
- 그러나 `S4_CM_STOP_CHAIN_UNPROVEN` (`cm_stop=false`). 이때 전방 26점은 단지 ±0.48rad / range<=0.65m 범위의 값이며, 공식 Collision Monitor의 좁은 S4ForwardStop polygon 내부라고 직접 증명한 것은 아님.
- 수정/계측: 피처 원통 중심을 로봇 물리 GT 전방 0.60→0.52m로 이동해 STOP 사각형의 내부 관측 확률을 높이고, 실제 스캔 polar XY의 사각형 내부 점 수·CM state 최근 12개·최종 command absolute max를 오류에서 계측. 센서 가짜 데이터 없이 실패 경계 확인.
- CM 입력→출력 구조, STOP polygon 크기/임계값, Nav2·SLAM/World 원본, 메뉴 속도 정책, Cmd 속도 안전 상한은 변경하지 않음. 다음 실제 Run GREEN 전 S4=HOLD.

## Cycle 04 — SOUP Nav2 복귀 단일 ABORT / 안전 STOP 별도 L2로 축소
- [Run #44653541553](https://github.com/silverbjin/samsung_AXI/actions/runs/44653541553): L0/L1 PASS, NORMAL TABLE3 Action SUCCEEDED / 실제 Odom 5.208m / AMCL error 0.074m, SOUP 복귀 Action status 6 (ABORTED), CM fixture 시험 전에 실패.
- 기존 Run #44651716546과 #44652530997에서 NORMAL 0.23/SOUP 0.11m/s 실제 속도 비교와 두 구간 Action 모두 SUCCEEDED를 확보했고, S3 NAV 배달·복귀 기준선 #44646848087도 GREEN. 이번 단일 ABORT 원인을 로봇/Planner 고장으로 단정하지 않음.
- 안전 시험만 좁힌 `--s4-stop-only`: 동일 지도·AMCL·TF·CM Lifecycle 준비 후 **실제 Gazebo fixture+LiDAR+upstream 소규모 속도 명령→CM STOP→filtered cmd_vel 제로/odom 정지**를 단일 세션에서 검증. 기존 성공된 5m 메뉴 왕복을 재반복하지 않음.
- 공식 Nav2 소스에서 CollisionMonitorState 발행은 polygon_name 전환 때 발생할 수 있으므로 fixture 생성 **직전**부터 STOP 상태를 추적. 생성 이전 STOP zone 내부 LiDAR 점 수가 이미 4 이상이면 테스트 전제 실패로 차단.
- STOP-only GREEN 후 전체 S4 통합 Run의 오차·속도·안전 결과를 분리해 최종 판단. 범위 밖 SDF/SLAM/Planner 변경 없음.

## Cycle 05 — 공개 CI STOP-only 실제 Gazebo L2 GREEN / S4 CI 판정

- [Run #44655038709](https://github.com/silverbjin/samsung_AXI/actions/runs/44655038709), verified source `6acaeb900ae053da0e6d8688274362bdb18e9585`: L0 PASS, 공식 Jazzy/Harmonic L1 PASS, 실제 Gazebo STOP-only L2 PASS.
- 실제 Gazebo 출고 지도·LiDAR/AMCL 준비 `S3_REAL_GAZEBO_RELEASED_MAP_AND_SENSORS_PRESENT`, `RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL`.
- 물리 SDF 원통 생성 이후 전방 실제 LiDAR `S4_PHYSICAL_FIXTURE_LIDAR_POINTS=29 STOP_RECT_POINTS=29`, 이후 `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS`.
- STOP 성공 프린트는 공식 `CollisionMonitorState.STOP` + `S4ForwardStop` 확인, 실제 upstream positive Twist 확인, 하류 `/cmd_vel` >=3 샘플 모두 |linear.x|<=0.025m/s, `/odom` 물리 변위<=0.045m의 FAIL-closed 계약을 모두 통과한 경우에만 발생합니다. 개별 정확한 출력 최댓값/변위는 다운로드 가능한 Artifact JSON을 참조하며 이 보고서에 추정 값을 기입하지 않습니다.
- Compact Evidence: [Artifact #14591689820](https://github.com/silverbjin/samsung_AXI/actions/runs/44655038709/artifacts/14591689820), ZIP 6,712 bytes, SHA256 `312232b92b7b496345561a6a4c1e6d6dffb47914cd9c3b9adfcc3e819a73991c`.
- 속도 증거는 **별도 원본** [Run #44651716546](https://github.com/silverbjin/samsung_AXI/actions/runs/44651716546): NORMAL/SOUP Odom p75 0.23/0.11m/s 및 두 Nav2 Action SUCCEEDED. 동일한 속도 동작은 Run #44652530997에서도 확인됨. 이 과거 속도 PASS를 STOP 전용 Run에서 재측정했다고 주장하지 않습니다.
- 첫 실패 [Run #44652530997](https://github.com/silverbjin/samsung_AXI/actions/runs/44652530997): CM STOP 상태 미관측. 변경 범위는 실제 polygon 내부 스캔 계측, fixture 전방 위치, STOP 이벤트 유효 기간을 fixture 설치부터 관측, 그리고 실제 STOP-only CI 진입점 및 Bash 인수 배열 수정. World/map/Planner/CM 안전 출력 상한을 완화하지 않음.
- 별도 실패 [Run #44653541553](https://github.com/silverbjin/samsung_AXI/actions/runs/44653541553) SOUP 복귀 ABORT는 재현성 미확정이며, S3 이전 성공 기준선을 훼손하지 않습니다.
- **최종 판정: S4-MENU-01 = CI_ACCEPTED (두 개의 서로 다른 실제 Gazebo L2 원본 조합).** 단일 End-to-End 메뉴 속도·STOP 동시 인수나 강사 WSL2 GUI 최종 인수는 `NOT_RUN`으로 구분합니다. 향후 main 통합 CI는 별도로 관찰합니다.
