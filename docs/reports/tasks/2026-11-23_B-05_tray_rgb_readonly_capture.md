# B-05 — 선택형 트레이 ROS RGB 읽기 전용 캡처 출고

- 날짜: 2026-11-23(KST).
- 기준: B Draft PR #37 `4c63d8a88297b7418efccb6e933c25275d9807ce` + B-06 입력 증거 보강.
- 판정: **로컬 이미지 포맷·저장 계약 PASS / 실제 ROS 트레이 토픽 NOT_RUN**.

## 개발 목표

A의 `/smartdish/tray/image_raw` 센서가 준비되면 B가 1프레임을 수집할 수 있도록 합니다. 그러나 이미지만 수신했다고 물리 안정성 정답을 확보한 것은 아니므로, 수집 결과는 `UNLABELLED`와 `NOT_OBSERVED`로만 저장합니다. 이 구분은 C가 임의 식기 이미지로 모델 학습을 시작하지 않도록 합니다.

## 구현과 선택 이유

- `ai/scripts/capture_tray_ros.py`: 읽기 전용 `sensor_msgs/Image` 구독(`qos_profile_sensor_data`), 유효 이미지 1건만 저장. 기본 토픽 `/smartdish/tray/image_raw`, 최대 120초 타임아웃, rgb8/bgr8 및 row padding 검사.
- 출력은 **`ai/data/private/` 내부로 제한**합니다. 원래 해상도의 PNG와 JSON provenance(SHA-256, topic, encoding, stamp, frame_id, `label:null`, `ground_truth:NOT_OBSERVED`)를 저장합니다.
- `tests/test_b_tray_capture.py`: ROS 설치 없이 이미지 메시지 모사 입력으로 RGB/BGR/stride/손상/출력 위치/중복 덮어쓰기 방지를 확인합니다.
- 기존 S7 전방 카메라/이미지 또는 `STACKED` 라벨을 트레이 안정성 정답으로 사용하지 않습니다.
- 다른 방안(기존 S7에서 자동 복사, C에서 임의 STABLE 반환, Gazebo 주행 신규 테스트 추가)을 배제합니다.

## 실제 로컬 검증

```bash
python3 -m compileall -q ai/scripts tests
python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py
# 실제 ROS 2 Jazzy 설치된 A 환경에서만:
ros2 topic list -t | grep /smartdish/tray/image_raw
python3 ai/scripts/capture_tray_ros.py --root . --timeout-s 15
```

- 첫 두 명령: `15 passed in 0.22s` / 컴파일 PASS.
- 실제 `rclpy`/sensor_msgs 의존성과 Gazebo 출력 프레임 수신: **NOT_RUN** (해당 실행 환경에 A 트레이 카메라 없음).
- 센서가 없을 때 예상 차단: `B_TRAY_CAMERA_TIMEOUT_NO_IMAGE`; 데이터 저장·라벨 기록 금지.
- 반대로 전방 카메라 토픽을 넣으면: `B_CAMERA_TOPIC_CONTRACT_MISMATCH` (로컬 가드 확인).
- GitHub B 전용 및 전체 Restaurant CI: 변경 PR에서 별도 확인해야 함.

## 다음 경계

A가 트레이 방향 카메라·물리적으로 다른 적재 장면/낙하 상태를 제공하면 한 장을 무라벨로 확보하고 물리 증거를 별도로 검토한 뒤 B-06 보강된 `collect_tableware.py`로 등록하십시오. 1장 성공은 모델 정확도/일반화 증거가 아니므로 최소 3개 독립 적재 그룹/클래스가 마련되어야 그룹 분할이 가능합니다.
