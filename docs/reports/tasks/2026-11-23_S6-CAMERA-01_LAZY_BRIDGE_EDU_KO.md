# S6-CAMERA-01 — 요청형 RGB 브리지 / 주니어 교육용 중간 보고서

- 날짜: 2026-11-23
- 개발 브랜치: `feature/s6-00-camera-01-20261123`
- 기준: S5 LiDAR Costmap+STOP WSL2 PASS 보존 / 새로운 S6 옵트인 경로만 신설

## 1. 실무 과제와 기존 코드 분석
원본 `bridge.yaml`은 RGB 이미지와 CameraInfo뿐 아니라 Depth 및 PointCloud2를 항상 연결합니다. 그러나 S5 Local Costmap과 Collision Monitor의 관측 입력은 이미 `/scan` 단독입니다. 식기 확인에 필요한 정보는 목적지 정지 후 RGB 영상 한 종류입니다.

## 2. 구조와 주요 데이터 계약
Gazebo rgbd_camera → 새로운 S6용 `ros_gz_bridge` lazy Image/CameraInfo → TABLE_3 정지 이후 생성되는 ROS Image 구독자 → 식기 판정 → 구독자 해제.
기존 `/scan`, `/odom`, `/clock`, `/tf`, `/cmd_vel`, `/imu`, `/joint_states` 토픽의 타입·브리지 방향을 수정하지 않았습니다.

## 3. 구현 파일과 설계 이유
- `src/restaurant_bringup/config/bridge_vision_on_demand.yaml`: RGB Image, CameraInfo에 `lazy: true`. Depth와 PointCloud2는 신규 프로필에서만 제외.
- `src/restaurant_bringup/launch/world.launch.py`: `bridge_config` 선택 인수, 기본값은 기존 `bridge.yaml`로 유지.
- `scripts/s6_camera_scene_ci.py`: 카메라가 필요한 시점에 `create_subscription`하고 완료 시 `destroy_subscription`; 실제 image encoding, step, width, height를 확인하고 PPM 및 SHA256 저장.
- `tests/test_s6_camera_contract.py`: 기존 안전 7개 브리지와 신규 브리지의 완전 동등성 및 lazy 계약.

## 4. 초심자 학습 포인트
1. ROS2 토픽의 Publisher/Subscriber 관계와 Gazebo 내부 Transport 구독은 별개의 층입니다.
2. `lazy: true`는 이미지 수요에 따라 브리지 구독을 조절하지만, Gazebo가 RGB-D 렌더링을 실제 중단했다는 증거는 아닙니다.
3. `sensor_msgs/Image`의 `encoding`, `step`, `width`, `height`를 고려하지 않고 raw byte를 이미지로 해석하면 오류가 납니다.
4. 원본 이미지의 픽셀 변화량은 '접시가 화면에 보인다'는 기초 증거일 뿐 Vision AI의 분류 정확도는 아닙니다.
5. 검증된 LiDAR 정지는 RGB와 무관하며 이미지 처리 노드가 `/cmd_vel`을 발행하면 안전 계약 위반입니다.

## 5. 재현·검증 절차 및 예상 로그
- L0: `python3 -m pytest -q tests/test_s6_camera_contract.py tests/test_static_contract.py`
- L2: 전용 GitHub Actions `restaurant-s6-ci.yml`: 실제 Gazebo가 제공하는 빈 영상과 접시 영상 촬영 및 PPM 저장.
- 기대: `S6_00_REAL_GAZEBO_DISH_VISIBLE_PASS`, `S6_CAMERA_01_LAZY_RGB_REQUEST_PASS_NO_GOAL`.
- 첫 실패: `S6_TIMEOUT_SCAN`, `S6_TIMEOUT_EMPTY_RGB_IMAGE`, `S6_DISH_FIXTURE_SPAWN_FAIL`, `S6_00_REAL_GAZEBO_DISHES_NOT_VISIBLE`를 원인 경계별로 구분.

## 6. 이번 구현 범위에서 검증하지 않는 것
- 독립 Vision AI 모델 학습/추론, Nav2 왕복 자동화, 강사 WSL2 GUI 및 GPU 렌더링 유휴 여부.
- RTF 90% 목표는 HOLD입니다. 데이터/AI 결과를 임의로 PASS 승격하지 않습니다.

## 7. 상태
- L0 계약: PASS (Run #45096063527, 정확한 SHA는 해당 Run 기록)
- L2 실제 이미지: PASS (Run #45096925265, 영상 원본 검사 완료)
- WSL2 L3: NOT_RUN (GPU·GUI 확인 전)

## 8. 정량 실증 및 아직 검증하지 않은 항목
- L0 센서 안전 계약 PASS. 기존 `/scan`, `/odom`, `/tf`, `/cmd_vel` 등 원본 브리지 설정의 동등성을 확인했습니다.
- L2: 로봇의 실제 Scan 31개, RGB 구독 생성 이전 0명, 테이블 접근 뒤 RGB 프레임 수신, `destroy_subscription` 이후 0명, Depth/PointCloud2 ROS 토픽 비브리지. `S6_CAMERA_01_LAZY_RGB_REQUEST_PASS_NO_GOAL`.
- **CameraInfo 실제 메시지 수신/렌더러 OFF/CPU·GPU 절감은 별도로 직접 측정하지 않았습니다.** 설정 계약 PASS를 물리 센서 전원 차단 PASS로 과장하면 안 됩니다.
- 실제 Gazebo 이미지의 PPM/JSON은 위 Run #45096925265 Artifact #14782884713을 사용합니다.
