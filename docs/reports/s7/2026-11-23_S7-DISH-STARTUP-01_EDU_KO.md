# S7-DISH-STARTUP-01 — 시작 시점 접시 배치 (교육용 개발 보고서)

2026-11-23 / 기준 main `2c66ce96e980f39f1ec990ac28571cf2fba2baa3` / 별도 기능 브랜치.

## 현상과 요구
- S6은 TABLE_3 Nav2 SUCCEEDED 뒤 `s6_camera_gate.gate()`가 `ros2 run ros_gz_sim create`로 접시 모델을 추가합니다. 시뮬레이션 첫 장면에는 접시가 없어 실제 레스토랑과 다릅니다.
- S7은 **접시가 월드 로딩 순간부터 이미 존재**하게 만듭니다. 기존 S5/S6 월드·지도·LiDAR·속도·Collision Monitor, Robot SDF는 변경하지 않습니다.

## RED → GREEN 설계
- RED: 원본 `src/restaurant_world/worlds/restaurant.sdf`는 `table_3`만 포함하고 `s6_stacked_dishes`는 없습니다.
- GREEN 후보: `s7_scene.py`가 기존 월드를 복사해 선택한 `stacked`/`empty` 장면을 생성합니다. stacked는 기존 S6의 검증된 3단 원통형 식기 모델을 WORLD SDF에 추가합니다. empty는 원본과 같은 의미의 빈 테이블이며 `s6_stacked_dishes`가 존재하지 않습니다.
- S7 opt-in `world_file` LaunchConfiguration을 추가하되 기본값은 기존 레스토랑 SDF를 가리킵니다.
- XML 단위 검사에서 정확한 TABLE_3 좌표(2.65,-3.20), 식기 pose(2.65,-2.91), static=true, visual/collision 6쌍을 검사합니다. 이전 SDF/지도 해시 불변.

## 시스템 흐름 및 데이터 파이프라인
`restaurant.sdf (원본)` → `s7_scene.py (stacked/empty 선택)` → `generated/s7/restaurant_<scenario>.sdf` → `world.launch.py(world_file opt-in)` → Gazebo startup model load → `/restaurant/rgbd/image` (도착 후 요청형) → S6 ML Vision.

**주의:** 기존 S6은 도착 후 model spawn이었습니다. S7은 모델이 월드 파일에 있으므로 같은 이름으로 재스폰하면 안 됩니다. 다음 S7 통합 사이클에서 S6 gate의 `seed_fixture`를 명시적으로 false로 설정합니다.

## 검증 조건과 한계
- L0: Python/Launch XML, world 배치 개수·좌표·기존 world/map 불변, 중복 모델 fail closed.
- L1/L2: 실제 Gazebo 시작에서 식기 엔티티와 원본 RGB를 확인해야 실제 배치 PASS입니다. 본 단위의 정적 L0만으로 Gazebo 시연 완성이라고 주장하지 않습니다.
- GUI 시각적 검수는 사용자 담당/자동 인수 제외. CI 이미지/엔티티 증거는 기능 게이트 유지.

## 주니어 질문
1. Robot spawn과 World SDF 초기 entity 로딩은 발생 시점이 어떻게 다릅니까?
2. 원본 S6 식기 모델의 visual/collision을 모두 재사용하는 이유는?
3. 왜 WORLD를 수정하지 않고 generated/s7/별도 SDF를 작성합니까?
4. `lazy:true`가 Gazebo의 카메라 렌더러를 물리적으로 OFF한다는 뜻입니까? (아닙니다.)

## 판정
코드와 교육 보고서 동시 커밋. 정적 L0 CI 결과는 별도 Run에서만 PASS 결정. 실제 Gazebo 시작 배치 L2: NOT_RUN. 후속 S7-NEGATIVE, S7-INTEGRATED 진행 예정. `main` 미병합.
