# S7-FLOW-STARTUP-02 — 실제 ROS/Gazebo 시작 월드·S6 RGB 통합 (교육용 보고서)

## RED
- S6 `restaurant_demo.sh`는 기존 시나리오에서 `--s6-scene-fixture`를 전달하여 TABLE_3 도착 후 Gazebo에 식기를 생성합니다. S7 시작 월드와 중복 적용하면 생성 충돌이 발생합니다.
- 기존 Nav2 실행기는 world_file을 전달하지 않아 S7 시작 월드가 실제 Gazebo에 로딩되지 않습니다.

## GREEN 구현 이유·범위
- S7은 `SAMSUNGAXI_S7_SCENARIO=stacked|empty` 명시 시에만 S7 월드 생성 및 `--s7-world`를 전달합니다. S5/S6 기본값은 기존 `--s6-scene-fixture`를 유지합니다.
- `ci_s3_amcl_smoke.py`는 S7 월드 파일 존재/좌표/접시 개수를 **Goal 이전에 검증**하고 world_file을 Gazebo로 전달합니다. 도착 후 식기 중복 스폰을 하지 않습니다.
- `s5_ci_delayed_tty.py`도 새 S7 장면을 실제 ROS/Gazebo·Nav2 경로에 전달할 수 있습니다.
- 신규 S7 WSL2 인수 스크립트는 **사용자가 지정한 고정 Git SHA 한 개**를 엔트리 파일과 ROS 코드 양쪽에 사용하며 TTY 승인/NO_GOAL 기본 게이트를 유지합니다.
- `s7_scene` 증거로 SDF world SHA와 `fixture_preloaded_at_world_start`/`dynamic_fixture_spawn_requested=false`를 기록합니다.

## ROS 데이터 파이프라인
`original restaurant.sdf` → `generated/s7/restaurant_stacked.sdf` → `Gazebo startup entity` → `Nav2/AMCL TABLE_3` → `Odom 실제 정지` → `S6 lazy RGB subscribe` → `ML STACKED` → `PICKUP_RETURN` → `LiDAR CM STOP`.

## 초심자 실습/검증
1. S6와 S7에서 접시가 언제 생성되는지 코드의 SDF 경로와 seed_fixture 인수를 찾아 설명하십시오.
2. `SAMSUNGAXI_S7_SCENARIO`를 지정하지 않았을 때 원본 S6 경로가 달라지지 않았는지 확인하십시오.
3. `bash scripts/samsungaxi_s7_wsl2_l3_once.sh --self-test`가 고정 SHA가 없으면 fail closed 하는 이유를 설명하십시오.
4. CI L0 테스트는 정적 경로만 검증합니다. 실제 Gazebo 식기 로드/이미지/Goal은 별도 L2 증거가 필요합니다.

## 판정
G02 코드/계약 테스트/교육 보고서 동일 개발 브랜치 저장. L0 CI 전 NOT_RUN, 실제 L2 NOT_RUN. GUI 시각적 검수는 사용자 수행/자동 게이트 제외. RTF 90% HOLD.
