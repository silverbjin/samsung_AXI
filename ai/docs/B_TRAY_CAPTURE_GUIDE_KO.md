# SmartDish B — A 트레이 RGB 카메라 준비 후 원본 캡처 가이드

## 1. 목적과 금지사항

이 스크립트는 센서 메세지를 **파일로만 저장**합니다. 로봇 Goal·속도·임무·AI 추론·라벨에는 관여하지 않습니다. 기존 S7의 정면 카메라는 트레이를 관측한다는 보장이 없습니다. Gazebo 화면에 식기가 보이거나 이미지 한 장이 저장돼도 `STABLE` 정답으로 인정하지 않습니다.

## 2. 선수조건 (A 담당 확인)

A가 `/smartdish/tray/image_raw` (`sensor_msgs/msg/Image`)를 실제 트레이 방향으로 내보내고, 물리 상태를 관측할 SDF/장면을 준비해야 합니다. 현재 A 브랜치의 이 기능은 미완성으로 확인되어 **현장 시험 NOT_RUN**입니다.

```bash
# ROS 2 Jazzy / Ubuntu 24.04, 저장소 루트
source /opt/ros/jazzy/setup.bash
ros2 topic list -t | grep /smartdish/tray/image_raw
ros2 topic info -v /smartdish/tray/image_raw
python3 -m pip install --user Pillow   # 이미 설치되면 생략
python3 ai/scripts/capture_tray_ros.py --root . --timeout-s 15 \
  --output ai/data/private/tray_unlabelled.png
```

- 수신 성공: `B_TRAY_CAPTURE_UNLABELLED_SAVED` + 이미지 SHA, 원본 픽셀 크기/인코딩/스탬프.
- 수신 실패: `B_TRAY_CAPTURE_BLOCKED` + 오류 코드. 카메라 준비/토픽/QoS를 확인하고 재실행합니다.
- 스크립트는 **1프레임만** 저장하고 바로 종료합니다. 반복 수집은 다른 파일명으로 지정합니다. 기존 파일 덮어쓰기는 차단합니다.
- 원본 PNG/JSON은 `ai/data/private/`에 저장되어 Git에서 제외됩니다. 이 저장 직후에도 manifest에는 아무 라벨도 추가되지 않습니다.

## 3. 별도 물리 안정성 검수 및 라벨링

같은 `stack_id`의 트레이 상태를 시뮬레이션 전/후에 관찰하고 지지면, 편심, 기울기, 이탈/전도/낙하 여부를 확인합니다. 전문가가 기준을 근거로 결정한 뒤 관련 관측 파일(예: `pose_after_settle.log`, 비공개 관리)을 독립 생성합니다. 생성한 파일이 비어 있으면 수집기가 등록을 차단합니다.

```bash
# /path/to/pose_after_settle.log는 실제로 존재하는 기록 파일이어야 합니다.
python3 ai/scripts/collect_tableware.py \
  --image ai/data/private/tray_unlabelled.png --root . \
  --manifest ai/data/manifest.csv --label STABLE \
  --scene-id scene-001 --stack-id stack-001 \
  --source GAZEBO_TRAY --license-status OWNED \
  --physics-evidence /path/to/pose_after_settle.log \
  --camera /smartdish/tray/image_raw
```

최종 PNG가 224×224 RGB로 전처리되며 `capture_config.physics_evidence_sha256`이 기록됩니다. **파일 존재와 SHA 일치는 사실성 검증이 아니라 감사 추적 근거**입니다. 같은 장면 프레임을 서로 다른 학습/시험 그룹에 넣지 마십시오.

## 4. 교육용 실패 시나리오

- `/camera/image_raw`로 바꾸어 시도 → `B_CAMERA_TOPIC_CONTRACT_MISMATCH`.
- 실제 토픽 부재 → `B_TRAY_CAMERA_TIMEOUT_NO_IMAGE` (ROS runtime이 없는 PC라면 `B_ROS_JAZZY_RUNTIME_NOT_AVAILABLE`).
- 관측 근거 없는 `--physics-evidence bogus.log` → `B_PHYSICS_EVIDENCE_FILE_MISSING`.
- 동일 PNG 재수집 → `B_DUPLICATE_IMAGE`.

실패 로그와 첫 관측 증거를 보고서에 남기고, 이미지·영상 원본이나 개인 정보를 GitHub로 업로드하지 마십시오. 원본 분석은 비공개 상태에서 수행하고 승인된 메타데이터만 공유합니다.
