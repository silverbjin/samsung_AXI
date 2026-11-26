# C-V1-ISSUE-01 — 학습 전 Test 접근 및 연구 미승인 모델 ROS 로딩 가능성

## 발생 조건 / RED 분석

기존 `ai/train/train_classifier.py`는 `read_verified_split(split_manifest,root)`로 **train/val/test 18행을 전부 검증**합니다. 이 함수는 Test 이미지 파일을 PNG로 열고 label도 검사하며, 실제 Test가 비공개일 때 모델 선택 프로세스와 증거 검수 프로세스가 분리되지 않습니다. 기존 학습 checkpoint에는 `PHYSICS_OBSERVED`만 기록하면 `smartdish_ai/model_runtime.py`가 로드할 수 있어, **학습 자체와 C의 제한 연구용 승인·E의 제품 인수를 구별하지 못하는 정책 취약점**이 있었습니다.

이는 실제 Test를 학습에 넣었다는 주장이나 제품 AI ON이 이미 출고됐다는 뜻이 아닙니다. **실제 P2/P3/P4는 한 번도 실행되지 않았습니다.** 이번 작업은 그 가능성을 사전에 차단합니다.

## 최소 수정 (RED→GREEN)

1. P0 독립 `dataset_v1_gate.py`가 별도 WSL2 Owner 프로세스에서 전체 42/42 hash와 Test 파일 형식까지 무결성만 검수합니다. 이것은 Test를 이용한 모델 선택이 아닙니다.
2. P2는 `read_verified_split(..., training_only=True)`로 원본 **CSV 바이트는 보존**하지만 `train/val` 행만 확인하고 이미지로 읽습니다. Test 이미지 파일이 삭제되거나 Test label이 유효하지 않은 음성 fixture에서도 P2 training view는 Test를 열지 않는 회귀 테스트를 추가했습니다.
3. P2 진입은 **독립 P0 보고서 SHA**, 연구 승인, plan SHA, pretrained cache **전체 SHA**, release/split SHA를 검증합니다. 학습 프로세스에서 P0를 새로 돌려 Test 이미지를 열지 않습니다. missing approval/pretrained → HOLD.
4. P3는 `--test-approval`과 `--test-lock`의 **한 번만 생성되는 잠금 파일**로 평가 시작 전에 Checkpoint/Plan/Split/threshold0.80을 봉인합니다. 실패 시 잠금 유지, 임의 재실행 금지. P3 사용 결과로 모델 재선택/가중치 튜닝 금지.
5. P4는 별도 `seal_v1_research_model.py`의 human acceptance 이후에만 research checkpoint를 생성합니다. ROS 런타임은 `C_RESEARCH_PILOT_ACCEPTED`, 정확한 Dataset v1, `production_contact=HOLD`, `E_AI_ON_approved=false`가 없으면 `C_MODEL_CONTRACT_MISMATCH`로 거부합니다.

## 중요한 경계 / 한계

- `UNKNOWN`, 타임아웃, 모델 없음 시 D 직원 확인/중단 계약 유지. C는 Goal/`cmd_vel` 발행 금지.
- P3 Test가 4건이고 U가 단 1건이므로 100% 결과도 일반화·안전 인증이 아닙니다. 자동 AI ON 출고는 별도 E 승인을 필요로 합니다.
- A/B 자료 재생산·Family split 변경·중복증강으로 표본 증식·모든 Contact HOLD 해제 및 A19 자동 실행 금지.
- 이 문서는 **코드 정책 수정의 교육 기록**입니다. 실제 P2/P3/WSL2 결과는 `NOT_RUN`으로 보존합니다.

## 초심자 실습 질문

1. Data SHA를 읽는 독립 P0와 Test 이미지의 픽셀을 학습에 제공하는 행위는 무엇이 다른가요?
2. 학습이 성공한 모델이더라도 ROS가 즉시 로딩하면 왜 위험할까요?
3. Test 1회 검사에서 실패했을 때 학습 파라미터를 고쳐 같은 Test를 다시 측정하면 왜 독립 평가가 무너질까요?

## C-V1-CI-DBG-01 — 경량 CI 의존성 누락 (원격 RED)

- 실제 RED [GitHub Run #45784287293](https://github.com/silverbjin/samsung_AXI/actions/runs/45784287293): **49 passed, 2 failed**.
- 첫 오류: `tests/test_c_stability.py::test_rgb_and_bgr_padded_rows`, `test_bad_image_encoding_and_corrupt_buffer` → `stability_inference_node.py:18`의 `ModuleNotFoundError: No module named 'numpy'`.
- 근본 원인: 기존 ROS-free 이미지 unpack 회귀를 새 L0 검증에 포함하면서 이전 C CI가 제공하던 `numpy` 설치를 누락했습니다. 코드/데이터 품질이 아니라 테스트 환경 불일치입니다.
- 최소 조치: 새 경량 CI `python -m pip install pytest pillow numpy`; 실 모델·Gazebo·private 데이터·A/B 작업은 재실행하지 않았습니다. GREEN 원격 확인 후 QA 원장에 별도로 기록합니다.
