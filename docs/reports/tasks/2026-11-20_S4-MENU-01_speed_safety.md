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
- **S4=NOT_VERIFIED**, 실제 Gazebo L2 GREEN을 확인할 때만 PASS로 변경.
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
