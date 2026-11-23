# SmartDish C 초심자용 재현 실습 — 데이터 → ResNet18 → ROS 2 UNKNOWN

## 0. 준비 체크 (강사와 학생 모두)

기준 저장소는 `https://github.com/silverbjin/samsung_AXI`, 기능 브랜치 `feat/smartdish-c-stability`. **main 병합 전이므로 아래는 C branch에서 실행**합니다.

```bash
git clone https://github.com/silverbjin/samsung_AXI.git
cd samsung_AXI
git switch feat/smartdish-c-stability
python3 -m pip install pytest pillow numpy  # 정적/계약 테스트
python3 -m pytest -q tests/test_c_stability.py
```

기대: `20 passed`. 이는 실제 모델 성능이나 Gazebo 시연이 아니라 **CONTRACT_PASS_ONLY**입니다. B의 분할 manifest는 main에 아직 없으므로 AI 학습을 시도하지 않습니다.

## 1. B와 C를 연결하는 이유

B의 산출물은 ROS 메시지가 아닌 `ai/data/split_manifest.csv`와 이미지 파일입니다. B PR #37은 별도 브랜치에 있습니다. 통합 담당은 **B 병합 후** C 모델 학습을 실행합니다. 개발 실습에서 B 브랜치를 열람할 수는 있지만 B 데이터 파일을 C 브랜치에 임의 복제하지 않습니다.

필드: `sample_id, scene_id, stack_id, label, image_path, source, capture_config, license_status, ground_truth, image_sha256, split`. 같은 stack_id가 train/test에 섞이면 평가가 과대 추정되기 때문에 `C_STACK_SPLIT_LEAK`로 차단합니다. `PHYSICS_OBSERVED` 물리 근거는 운영자의 실제 리뷰가 필요하며 CSV에 경로를 적었다고 참이라고 검증되지는 않습니다.

## 2. 실제 B 물리 데이터가 확보된 이후에만 실행

```bash
# GitHub 통합 후 저장소 루트에서 시작, 실제 유효한 B split/이미지 필수
python3 -m pip install torch torchvision pillow
mkdir -p /tmp/smartdish-c-artifacts
python3 -m ai.train.train_classifier --phase frozen \
  --root . --split-manifest ai/data/split_manifest.csv \
  --out /tmp/smartdish-c-artifacts/baseline.pt \
  --report /tmp/smartdish-c-artifacts/baseline_train.json
python3 -m ai.train.train_classifier --phase finetune \
  --init-checkpoint /tmp/smartdish-c-artifacts/baseline.pt \
  --root . --split-manifest ai/data/split_manifest.csv \
  --out /tmp/smartdish-c-artifacts/finetuned.pt \
  --report /tmp/smartdish-c-artifacts/finetune_train.json
python3 -m ai.train.evaluate \
  --root . --split-manifest ai/data/split_manifest.csv \
  --checkpoint /tmp/smartdish-c-artifacts/finetuned.pt \
  --report /tmp/smartdish-c-artifacts/independent_test.json
sha256sum /tmp/smartdish-c-artifacts/finetuned.pt
```

pretrained ResNet18 weights는 최초 실행 때 torchvision에서 네트워크/캐시 접근이 필요합니다. 데이터가 없거나 권리가 확인되지 않으면 스크립트가 실패하는 것이 바른 동작입니다. 성능이 생기면 `independent_test.json`의 accuracy, macro_f1, confusion_matrix를 Model Card에 **실제 근거와 함께** 옮깁니다. test 데이터를 학습에 사용하지 않습니다.

## 3. WSL2 ROS 2 Jazzy에서 노드 시작 (현재는 예시/미실행)

```bash
# Ubuntu 24.04 / WSL2, ROS 2 Jazzy 설치 완료 환경
python3 -m venv --system-site-packages "$HOME/smartdish_c_venv"
source "$HOME/smartdish_c_venv/bin/activate"
python3 -m pip install torch torchvision pillow numpy
set +u
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select smartdish_ai
source install/setup.bash
ros2 pkg executables smartdish_ai
# 초기 model_path는 ''이므로 UNKNOWN이 정상 응답
ros2 run smartdish_ai stability_inference_node --ros-args \
  --params-file src/smartdish_ai/config/model.yaml
```

**다른 터미널**에서 ROS 설정 및 오버레이를 source한 뒤 아래를 순서대로 실행합니다. 먼저 `echo`로 구독자를 준비한 뒤 메시지를 보냅니다.

```bash
ros2 topic echo /collection/stability std_msgs/msg/String
# 세 번째 터미널에서
ros2 topic pub --once /collection/ai_check_request std_msgs/msg/String \
  '{data: "{\"request_id\":\"C-DEMO-001\",\"capture_id\":\"CAP-001\"}"}'
```

예상 JSON(실측 로그가 아닌 계약 예시): `{"request_id":"C-DEMO-001","capture_id":"CAP-001","status":"UNKNOWN","confidence":null,"model_version":"none"}`. 모델이 없는 상태에서 STABLE이 발행되면 **결함**입니다. 카메라 토픽이 없으면 같은 UNKNOWN 경로로 안전하게 처리해야 합니다.

실제 모델을 준비한 뒤 `src/smartdish_ai/config/model.yaml`의 `model_path`를 **Git에 올리지 않을 로컬 checkpoint 절대경로**로 바꿔 노드 재시작. AI ON 선택 기능을 시험하려면 A의 `/smartdish/tray/image_raw` 메시지에서 실제 인코딩, 도착 주기, 1장 이상을 `ros2 topic info -v` / `ros2 topic echo --once`로 확인합니다. 모델·카메라 미존재는 실제 검수할 수 있어도 ROS 미실행이면 **NOT_RUN**으로 남깁니다.

## 4. 자주 발생하는 오류

| 최초 메시지 | 원인 | 조치 |
|---|---|---|
| `C_SPLIT_MANIFEST_MISSING` / `C_TRAINING_NOT_RUN_NO_REAL_DATA` | B 병합/실측 데이터 없음 | 물리 증거를 가진 B 실제 샘플 준비; 가짜 데이터를 학습하지 않음 |
| `C_FIXTURE_OR_UNVERIFIED_GROUND_TRUTH` | B 합성 fixture/권리 불명 | 실제 관측 근거, 허가 확인 |
| `C_STACK_SPLIT_LEAK` | 동일 적재 스택 train/test 중복 | B가 split_manifest를 그룹 기준으로 다시 생성 |
| `C_MODEL_WEIGHTS_MISSING` | weights 경로 오류 | 로컬 checkpoint SHA·경로 확인 |
| `C_MODEL_CONTRACT_MISMATCH` | 다른 모델/라벨 순서 | MODEL_CARD의 버전·전처리와 동기화 |
| `UNKNOWN` | 미설치/오래된 영상/저신뢰/예외 | D의 NEEDS_CONFIRMATION, 직원 확인; 자동 STABLE 금지 |

## 5. 결과 해석 퀴즈

1. `20 passed`와 `INDEPENDENT_TEST_EVALUATED`는 어떻게 다릅니까?
2. 시험 결과 혼동행렬에서 행/열의 의미는 무엇입니까?
3. `capture_id`가 다른 두 요청에 동일 이미지가 쓰이면 어떤 오류가 생길까요?
4. 왜 트레이 전용 카메라 없이 TABLE_3 전방 카메라를 사용해서는 안 될까요?
