# SmartDish C 초심자용 재현 실습 — 데이터 → ResNet18 → ROS 2 UNKNOWN

## 0. 준비 체크 (강사와 학생 모두)

기준 저장소는 `https://github.com/silverbjin/samsung_AXI`, 기능 브랜치 `feat/smartdish-c-stability`. **main 병합 전이므로 아래는 C branch에서 실행**합니다.

```bash
git clone https://github.com/silverbjin/samsung_AXI.git
cd samsung_AXI
git switch feat/smartdish-c-stability
python3 -m pip install pytest pillow numpy  # 정적/계약 테스트
python3 -m pytest -q tests/test_c_stability.py tests/test_c_mock_pipeline.py
```

기대: 기존 20개 + 더미 분리 7개, 총 `27 passed`. 이는 실제 모델 성능이나 Gazebo 시연이 아니라 **CONTRACT_PASS_ONLY**입니다. B의 분할 manifest는 main에 아직 없습니다. 실학습은 불가하지만 **별도 더미 모드**로 학습 루프를 검증할 수 있습니다.

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


## 6. B 더미로 오늘 실습하기 (C04/C05 신설)

B 브랜치를 별도 checkout으로 받아 **실제 B 생성기 코드를 읽기 전용으로 실행**합니다. 로컬 파일을 복제하거나 main에 병합하지 않습니다.

```bash
# C 브랜치 체크아웃 상태, 저장소 루트에서
python3 -m pip install pytest pillow numpy torch torchvision
python3 -m pytest -q tests/test_c_stability.py tests/test_c_mock_pipeline.py

git clone https://github.com/silverbjin/samsung_AXI.git /tmp/smartdish-b-readonly
git -C /tmp/smartdish-b-readonly checkout --detach   4c63d8a88297b7418efccb6e933c25275d9807ce

OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python3 -m ai.train.demo_fixture_pipeline   --b-script /tmp/smartdish-b-readonly/ai/scripts/prepare_dataset.py   --b-ref 4c63d8a88297b7418efccb6e933c25275d9807ce   --output /tmp/smartdish-c-mock-only --epochs 1
```

기대: `B_MOCK_ONLY_FIXTURES_CREATED` → `B_DATASET_CONTRACT_PASS` → `C_MOCK_ONLY_FROZEN_TRAINED` → `C_MOCK_ONLY_FINETUNE_TRAINED` → `C_MOCK_ONLY_TEST_EVALUATED` → `C_B_MOCK_ONLY_PIPELINE_PASS`. 숫자는 임의 fixture에서 변동 가능하며 실제 테스트 성능을 뜻하지 않습니다. 자동 원본/테스트 SHA, 분할, 모델 메타데이터, 안전 배포 거부 증거는 `/tmp/smartdish-c-mock-only/c_pipeline_result_MOCK_ONLY.json`에서 확인합니다.

더미 체크포인트는 `src/smartdish_ai/config/model.yaml`의 `model_path`로 지정하지 마십시오. 운영 노드가 거부하고 `UNKNOWN`으로 처리하는 것이 **정상**입니다. 학습 weights는 디스크 용량을 차지하므로 검수 후 `/tmp/smartdish-c-mock-only/`를 수동 정리할 수 있습니다.

## 7. 실제 물리 데이터 도착 후 그대로 전환

B 자료를 먼저 병합하거나 동일 버전 파일을 읽기 전용으로 연결한 후 `ai/data/split_manifest.csv` 및 PNG 이미지 경로가 존재하는지 확인합니다. 데이터 수집자는 `PHYSICS_OBSERVED`의 근거 자료와 사용 허가를 사람 눈으로 검토합니다. 이전 2절의 **기존 명령을 `--demo-fixtures` 없이** 다시 실행하십시오. `baseline.pt`, `finetuned.pt`는 새 작업 디렉터리에 생성하고 더미 체크포인트를 절대로 `--init-checkpoint`로 전달하지 마십시오.

실제로 훈련된 모델만 `PHYSICS_OBSERVED` 체크포인트가 되어 운영 ROS 노드에서 읽을 수 있습니다. 별도 실제 Gazebo RGB 수신과 D AI ON 경로를 확인하기 전에는 **AI_ON_OPTIONAL_PASS라고 주장하지 않습니다**.

## 8. C06 — 실제 물리 데이터 출고 여부를 한 명령으로 확인

다음은 B 소스를 덮어쓰지 않는 read-only 점검입니다. **현재 B 최신 브랜치에는 실제 물리 라벨 이미지가 0장**이므로 `BLOCKED` 종료 코드 2가 예상 결과입니다. 코드가 망가진 것이 아닙니다.

```bash
# C 전용 브랜치 작업 위치에서 실행
B_SHA=1bfc19eabe07f2a0ea8c5c8ba3509491c9dd217d
git clone https://github.com/silverbjin/samsung_AXI.git /tmp/smartdish-b-readonly || true
git -C /tmp/smartdish-b-readonly fetch origin "$B_SHA"
git -C /tmp/smartdish-b-readonly checkout --detach "$B_SHA"
python3 -m ai.train.check_real_data_readiness \
  --split-manifest /tmp/smartdish-b-readonly/ai/data/split_manifest.csv \
  --root /tmp/smartdish-b-readonly --b-ref "$B_SHA" \
  --report /tmp/smartdish-c-real-readiness.json
# 정상적인 현재 상태: C_TRAINING_NOT_RUN_NO_REAL_DATA, verdict=BLOCKED, rc=2
```

실제 데이터가 나오면 `split_manifest.csv`의 각 PNG와 `capture_config.physics_evidence`가 **C 호스트에서 열리는지**, 파일 크기와 SHA256이 맞는지 검증합니다. `CONTRACT_READY_HUMAN_REVIEW_REQUIRED`가 나오더라도 사람이 전도/낙하·접촉 관측 근거와 사용권을 승인한 후에만 2절의 frozen → finetune → independent test 명령을 실행합니다. `--demo-fixtures`는 이 단계에 절대 추가하지 않습니다.

새 오류 예시: `C_PHYSICS_EVIDENCE_FILE_MISSING`(실물 기록 파일 미전달), `C_PHYSICS_EVIDENCE_INTEGRITY_METADATA_MISSING`(B-06 SHA 필드 미등록), `C_PHYSICS_EVIDENCE_SHA_MISMATCH`(증거 파일 변경 또는 손상), `C_PHYSICS_EVIDENCE_SIZE_MISMATCH`(전송 누락/변형). 이때 **주관적 정상 판정으로 넘어가지 말고 원본을 보존**합니다.

## 9. C07 — D Mission Manager와 AI 모의 응답 연결 테스트

C는 D의 코드를 수정하지 않고, GitHub Actions에서 B, D 브랜치를 **각각 정확한 SHA로 별도 checkout**한 후 C→D 응답을 JSON으로 연결합니다. ROS 2 설치가 없어도 `UNKNOWN→NEEDS_CONFIRMATION→직원 승인` 흐름과 AI OFF 독립성이 검사됩니다. 다만 D의 가짜 Nav2 성공 이벤트를 테스트에 주입하므로 이는 `MOCK_ONLY`이고 실제 3구간 주행 증거가 아닙니다.

```bash
D_SHA=195a8ee0758e7734bb6be627ab16461893355be9
git clone https://github.com/silverbjin/samsung_AXI.git /tmp/smartdish-d-readonly || true
git -C /tmp/smartdish-d-readonly fetch origin "$D_SHA"
git -C /tmp/smartdish-d-readonly checkout --detach "$D_SHA"
SMARTDISH_D_READONLY=/tmp/smartdish-d-readonly python3 -m pytest -q \
  tests/test_c_stability.py tests/test_c_mock_pipeline.py \
  tests/test_c_real_readiness.py tests/test_c_d_cross_branch.py
```

D 체크아웃이 없으면 D 교차 테스트 파일은 로컬에서 `SKIP`됩니다. CI에서는 checkout을 필수로 만들었으므로 `SKIP`가 계약 인수를 의미하지 않습니다. 실행 후에는 각 Job의 실제 SHA와 테스트 수를 C07 개발 보고서에 기록합니다.
