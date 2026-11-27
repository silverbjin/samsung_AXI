# C16 — Dataset v1 연구 모델 1차 파일럿 기술 판정 / 종료 및 변경 관리 (2026-11-27)

> **완료 판정:** `C16_FIRST_RESEARCH_PASS_CLOSED_NEGATIVE_VALIDATION_RESULT`. C15 실험 실패 원인 분석을 근거로 **1회 frozen-head 연구 학습의 기술 검토를 종료**합니다. 이는 **모델 자체의 성공/연구 Pilot Acceptance가 아니라 실패 또는 불충분한 Validation 결과의 정직한 기록**입니다. 향후 별도 연구 버전 기획은 가능하되 현행 P2 GO 재사용 불가. Test4 **미개봉**.

## 1. 근거·변경하지 않은 계약

- C15 [집계 기반 원인 분석](2026-11-27_C15_P2_FAILURE_FORENSIC_EDU_KO.md) 및 [원본 P2 연구 실행 증거 인수](../acceptance/SMARTDISH_C_V1_P2_OWNER_ACCEPTANCE_20261127_KO.md). 실제 Owner P2 `summary.json` SHA `945f8f4aeb3b8a8e9cb1873f4353620dbd660765b3eb9688ab234a61f97a3864`; P3 read-only checkpoint seal SHA `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c`.
- 사용한 정확한 계약: Data v1 approved18/5 Family, Train11(8S3U), Val3(2S1U), Test4 sealed(3S1U), `ResNet18_Weights.IMAGENET1K_V1`, frozen-head/seed42/CPU/batch4/epochs3/lr1e-4/val CE minimum, threshold0.8. 사전 실험 lock JSON 미수정.
- 실제 Train 누적 로그 `4/11`, Val `1/3=33.3%`, STABLE majority `2/3=66.7%`, Val loss0.7452375. **신규 합격 임계값을 사후 발명하지 않으며**, 모델이 안전 위험 분류 능력을 보였다는 증거가 없다는 C 기술검수 판단임.
- 외란은 `t0` 후 가해지므로 단일 RGB 이전 영상에서 이후 물리 현상을 추정한다는 연구 문제의 표상 한계 가능성. **원인 하나로 확정하지 않음**. UNSTABLE false negative/coverage/Family-per-class 평가는 개별 예측값이 없어 UNKNOWN.
- P0/P1/P2/P3-pretest 이전 PASS 재사용, **WSL2 추가 실행 0회**, 새 model inference/train/test/물리 생성 0회, GitHub fixture-only.
  
## 2. 기술 의사결정 3가지 경로

| 경로 | 결정 | 허가 경계 |
|---|---|---|
| **A. 현행 v1 1회 frozen 연구 종료** | **기본 채택**: 부정적/불충분 Validation 결과, 학습 코드/증거/비공개 checkpoint 보존, `C_RESEARCH_PILOT_ACCEPTED=false` | 별도 Test 개봉 또는 모델 인수 없음 |
| B. 향후 새 버전 연구 | **변경 요청 후보만 작성**: 새로운 기획, 이미지 시간대·물리 양 측정·라벨/권리·Family 독립성·대표성·사전 평가 계획 재검 | **새 PM Change Request 및 사람 승인 전 개발/데이터 생성/재학습 불가** |
| C. 현재 v1의 Test4를 교육용 단일 평가 | **비권고, 미승인**: 성능 검증이 아니라 결과 서술·실패 양상 확인으로만 선택 가능 | 별도 Owner `C_P3_SINGLE_TEST_GO` 승인 + checkpoint/threshold 재봉인; Test 결과의 재학습·재선택 금지 |

**권고:** 먼저 A를 기록하고 D/E에 제품 모델 없이 UNKNOWN·직원 확인 계약만 인계합니다. 현행 실험은 실패/불충분 사례로 교육과정에 활용합니다. B와 C는 오너의 새 지시 없이는 실행하지 않습니다.

## 3. 완료 상태 vs 보류 상태

| Gate | C16 확정 상태 |
|---|---|
| C15 실패 원인 분석 | **완료** / 근본 단일 원인 `UNDETERMINED` |
| C16 연구 1차 Frozen 결산 | **완료** / `NEGATIVE_VALIDATION_RESULT` |
| P0 42/42, P1 pretrained, P2 실학습, P3 pretest | 기존 **기술 PASS** 보존 |
| P2 연구 모델 정확도/위험 분류 적합성 | `HOLD_NOT_ACCEPTED` |
| P3 단일 Test 평가 | `NOT_APPROVED`, `NOT_OPENED` |
| P4 model card/연구 checkpoint 인수 | 기술 정보 인계 가능, `C_RESEARCH_PILOT_ACCEPTED=false` |
| D/E 실제 AI ON | `HOLD` — AI OFF 3구간 제품 보존 |
| A19, Production Contact | `NOT_AUTHORIZED`, `HOLD` |

C15/C16 완료라고 전체 SmartDish C Dataset v1 P0~P6나 E AI ON이 모두 완료됐다고 표기하지 않습니다.

## 4. 향후 v2 연구 Change Request 초안 (미승인)

- **목표 재정의:** `t0` 정적 RGB만으로 미래 물리 결과를 판별할 수 있는지 독립적으로 검토. 필요하면 시점/센서 확장 가설을 구분하고 시간 역인과 누출 금지.
- **데이터 품질:** 독립 Family·적재 재질/형상/외란 방향 다양성, imbalance 및 label audit, 실제 측정 값과 명령 torque 구분, rights/재배포 범위를 먼저 확정.
- **평가 설계:** 독립 split 선등록, `UNSTABLE→STABLE` 위험/precision/recall, UNKNOWN/coverage, class imbalance baseline 사전 정의. 현재 Test4는 v1 봉인으로 유지하고 v2 최적화에 사용하지 않음.
- **개발 권한:** 어떤 새 생산(A19 포함)·학습·Test 개봉도 `PM_CHANGE_REQUEST_REQUIRED` 및 Owner 명시 승인 후 독립 repo branch/실험 lock에서 진행.
- **WSL2 원칙:** AGENTS.md의 Agent-first, private 최종 검수에만 하나의 SHA fixed one-shot + 최소 증거 TAR/sidecar. 지금 실행 요구 없음.

## 5. 구현·교육 자산

- `ai/train/c16_research_disposition.py`: C15 aggregate review만 호출하는 **표준 라이브러리·읽기 전용 기술 판정기**. Test/torch/Gazebo 접근이나 인간 승인을 생성하지 않음.
- `tests/test_c16_research_disposition.py`: altered checkpoint/Validation/Test/A19/Contact/AI OFF에 fail-closed.
- 결과문 `C16_FIRST_RESEARCH_PASS_CLOSED_NEGATIVE_VALIDATION_RESULT`는 연구의 부정적 관찰을 기록한 **기술 권고 판정**이지 제품 출시, 데이터/모델 가중치 공개, Test 실행 허가가 아님. 별도 사람이 직접 승인해야 하는 권한을 코드가 대체하지 않습니다.
- [교육용 이슈 OPEN](../issues/2026-11-27_C15_ISSUE_03_FROZEN_HEAD_PERFORMANCE_HOLD_KO.md) 유지: 해결됐다는 뜻 아님.
