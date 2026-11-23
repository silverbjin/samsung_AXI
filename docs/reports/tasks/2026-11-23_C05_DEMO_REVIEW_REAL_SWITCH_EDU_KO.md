# C05 — 더미 end-to-end 실행·실데이터 전환 설계·교육 보고서

- 날짜: 2026-11-23 / 브랜치 `feat/smartdish-c-stability` / Draft PR #39 (미병합)
- 기준: C04 계약 모드·체크포인트 분리, B pinned `4c63d8a88297b7418efccb6e933c25275d9807ce`.
- 변경: `ai/docs/MODEL_CARD_KO.md`, `MODEL_TRAINING_GUIDE_KO.md`, `docs/handoff/C_HANDOFF.md`, C 전용 CI, 디버깅 이슈 갱신 및 본 보고서.
- 상태: **C dummy L0/local end-to-end PASS; B 원본 checkout CI는 Run 결과 확인 후 확정; 물리 검증 NOT_RUN**.

## 1. 처음부터 끝까지 어디까지 연결했습니까?

로컬 shim(실제 B 브랜치 원본 소스 아님)이 B와 같은 `CONTRACT_FIXTURE` 이미지 6장을 생성했습니다. 이를 B가 정의한 `stack_id` 그룹 분할과 정확한 라벨 맵(`STABLE=0`, `UNSTABLE=1`)으로 분리하고, C의 frozen baseline/finetune 두 경로를 1 epoch씩 CPU로 실행한 뒤 mock test split으로 평가했습니다. 이어 동일 파일의 RGB 2장으로 `InferenceCore`의 JSON `request_id/capture_id/status/confidence/model_version` 경로를 검증하고 마지막으로 운영 ROS 로더가 해당 weights를 거부하는지 확인했습니다.

## 2. 측정된 로컬 결과 — 성능으로 오인 금지

| 항목 | 관측 | 해석 |
|---|---|---|
| Python/torch | CPU, torchvision 설치 상태에서 실행 | WSL2 Gazebo 증거 아님 |
| B 계약형 분할 | train/val/test 각 STABLE 1, UNSTABLE 1 | 총 6장 모두 synthetic |
| frozen ResNet18 | 학습 과정 완료 | random init — pretrained 학습 아님 |
| finetune | 학습 과정 완료 | layer4+fc 경로 확인 |
| 더미 test | 2개 샘플, Accuracy 1.0 / Macro F1 1.0 / CM `[[1,0],[0,1]]` | **MOCK_ONLY_SANITY_CHECK** — 모델 성능 없음 |
| ROS-free 계약 | `C-MOCK-REQ`/서로 다른 capture ID 2건 | JSON 상관관계 코드 경로만 PASS |
| 안전 배포 차단 | dummy checkpoint 로드시 `C_MODEL_CONTRACT_MISMATCH` | 운영 모드 FAIL-CLOSED PASS |
| A tray Gazebo image / rclpy live / D 실제 FSM | 미실행 | NOT_RUN |

결과 위치는 로컬 `/mnt/data/smartdish_c_demo_outputs/`이며, 43MB 안팎의 dummy `.pt` 두 개는 **GitHub에 보관하지 않음**. 대용량 증거 대신 실행 명령, 결과 JSON SHA, 원본 파일명, 핵심 지표만 문서화합니다. 로컬 shim 결과를 B 브랜치에서 직접 실행한 결과로 해석하지 마십시오.

## 3. 기존 임무에 영향이 없는 이유

운영 노드 `/collection/stability`는 `PHYSICS_OBSERVED`로 검증된 체크포인트만 로드합니다. 더미 모델을 설정하면 `UNKNOWN`, `confidence:null`, `model_version:none`로 처리하며, AI OFF 임무는 이 노드를 요구하지 않습니다. 오프라인 실험 스크립트는 Nav2 Goal과 `/cmd_vel`을 발행하지 않습니다.

## 4. 실데이터 전환 경계 (MVP 계획 개정)

1. B가 실제 트레이 이미지와 물리 관측 자료, 사용 권한을 승인하고 `stack_id` 누수 없는 train/val/test split을 출고합니다. 기존 B Draft PR #37은 통합 담당이 먼저 검토·병합합니다.
2. B manifest 데이터 `PHYSICS_OBSERVED`, `source=GAZEBO_TRAY|REAL_TRAY`, physics_evidence 참조·이미지 SHA·label_map·각 split 클래스가 검증되어야 합니다. 이 CSV는 근거 링크의 **진위까지 자동 검증하지 않으므로 담당자가 관측 자료를 확인**해야 합니다.
3. `--demo-fixtures` 없이 동일 `train_classifier.py`와 `evaluate.py`를 실제 data root로 실행합니다. **ImageNet pretrained frozen 1회 → finetune 1회 → test 1회** 순서를 유지합니다. 기존 dummy `.pt`는 real 학습 초기 체크포인트로도 사용하지 않습니다.
4. `MODEL_CARD_KO.md`에 실제 B SHA, split SHA, 학습 HW, epoch, Accuracy/F1/CM, 모델 버전 및 weights의 배포 권한을 기록하고 ROS의 모델 경로를 실제 weights로만 지정합니다.
5. A의 트레이 카메라에서 Gazebo RGB가 1장 이상 확인되고 D의 AI ON `UNKNOWN/UNSTABLE→NEEDS_CONFIRMATION` 분기를 통과한 뒤 선택 기능으로 인수합니다. AI OFF 기본 시연을 차단하지 않습니다.

## 5. 공통 테스트·CI 진위

GitHub Actions job은 B 원본 소스의 **정확한 SHA를 checkout**한 뒤 B의 `make-fixtures` 및 `allow-fixtures` 과정을 돌리고 C split validator가 6장을 받되, real validator는 해당 6장을 **반드시 거부**하는지 검사합니다. GitHub runner의 `--contract-only`는 의도적으로 Torch 설치·학습·ROS/Gazebo를 실행하지 않습니다. CI Run 증거는 성공 확인 후에만 보고서에 추가하십시오.

### 학생 토론

- 같은 100% 숫자여도 실제 test라면 의미가 달라지는 이유는 무엇입니까?
- 왜 더미 체크포인트를 실제 데이터 학습의 warm start로 재사용하면 안 됩니까?
- 깃허브 CI가 6장 mock 검사 PASS일 때 실제 ROS 2에서 STABLE을 출력해도 됩니까?

**결론:** 데이터 의존성은 더미 개발 단계에서 제거되었지만, 물리 검증 모델·실영상·실 ROS 연동은 계속 `BLOCKED/NOT_RUN`입니다.
