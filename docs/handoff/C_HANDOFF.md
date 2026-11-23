# C 담당 → D/E SmartDish AI ON 선택 기능 인계

- 일자: 2026-11-23
- GitHub: `silverbjin/samsung_AXI`, C 브랜치 `feat/smartdish-c-stability` (main 기준 `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`)
- Draft PR: GitHub PR 생성 후 본문에서 확인, 최종 HEAD SHA도 PR 기준 확인
- B 입력 기준: `feat/smartdish-b-dataset@4c63d8a88297b7418efccb6e933c25275d9807ce`, Draft PR #37, Dataset Card v1.0, `label_map={"STABLE":0,"UNSTABLE":1}`
- **C가 소유하지 않는 것:** A World/Nav2/트레이 카메라와 D FSM/UI, B 원본 데이터. S7 `STACKED` 모델도 수정하지 않습니다.

## 계약 API

| 입력/출력 | ROS 2 메시지 | 규칙 |
|---|---|---|
| `/smartdish/tray/image_raw` | `sensor_msgs/Image` | A 트레이 RGB, `rgb8/bgr8`, `sensor_data` QoS, 최신 유효 프레임 2초 이내 |
| `/collection/ai_check_request` | `std_msgs/String` JSON | `{request_id,capture_id}`, RELIABLE/VOLATILE/KEEP_LAST(10) |
| `/collection/stability` | `std_msgs/String` JSON | `{request_id,capture_id,status,confidence,model_version}`, 동일 QoS |

중복 요청 `(request_id,capture_id)`는 이미 응답했다면 무시하며, 유효 요청 1건은 `STABLE/UNSTABLE/UNKNOWN` 중 하나만 발행합니다. 입력/모델/이미지 미준비는 `UNKNOWN, confidence:null`, 모델이 없으면 `model_version:none`. C는 Nav2/`cmd_vel`을 발행하지 않습니다. D는 `UNKNOWN/UNSTABLE/timeout`에서 **NEEDS_CONFIRMATION**을 유지하고 `APPROVE_CONTINUE` 전에는 이동을 재개하지 않습니다.

## 현재 판정

- 오프라인 Python 계약·입력 방어 테스트: `20 passed`, C L0 확인 (GitHub CI Run 별도)
- AI 실데이터: **0건**, `TRAINING_NOT_RUN`; `Accuracy/F1/Confusion Matrix=NOT_RUN`.
- Gazebo 트레이 영상: `ROS_IMAGE_LIVE_NOT_RUN`; 실제 모델 weight/version/모델 사용권=미확정.
- ROS 2 Jazzy/WSL2 노드 시동·토픽 실측: `NOT_RUN` (이 도구 환경에는 `rclpy`가 없음).
- AI OFF 완주에는 본 노드가 필요하지 않습니다. D/A 필수 MVP를 차단하지 않습니다.

## 재현·보고서

1. [`ai/docs/MODEL_TRAINING_GUIDE_KO.md`](../../ai/docs/MODEL_TRAINING_GUIDE_KO.md)에서 단위 테스트, 학습, WSL2 노드 실행 순서를 참조합니다.
2. [`ai/docs/MODEL_CARD_KO.md`](../../ai/docs/MODEL_CARD_KO.md)에서 전처리·label_map·임계치와 학습 제한을 확인합니다.
3. [`C01 학습/평가 작업보고`](../reports/tasks/2026-11-23_C01_TRAIN_EVAL_EDU_KO.md), [`C02 추론 작업보고`](../reports/tasks/2026-11-23_C02_ROS_INFERENCE_EDU_KO.md), [`C03 CI/PR 작업보고`](../reports/tasks/2026-11-23_C03_CI_DRAFT_PR_EDU_KO.md), [`C-ISSUE-01 차단 기록`](../reports/issues/2026-11-23_C_ISSUE_01_B_DATA_BLOCKED_KO.md).
4. E 통합: **B Draft PR을 먼저 검토·병합** → C Draft PR 코드 병합 → A 카메라와 D FSM을 연결. ROS 실측 결과 없이 `AI_ON_OPTIONAL_PASS`를 주장하지 않습니다.

## 미해결 외부 의존

B에서 독립 `train/val/test` 별 실제 식기 이미지와 물리 관측, 허가 확보. A에서 트레이 시야 카메라/영상 메시지 확보. 그때 C가 frozen→fine-tune→독립 test 1회→ROS 이미지 1장→D 승인 분기를 실행합니다. 사용한 이미지 데이터 SHA, B Git SHA, 모델 weight SHA와 실제 결과를 추후 보고서에 추가합니다.
