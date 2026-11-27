# E-AION-00 — C v1 원본 성능·사용권 감사 및 Owner 통합 승인 범위 (2026-11-27)

> **Owner instruction (this task):** C20 연구는 별도 유지. C v1 성능 33.3%는 A+C+D/E 통합 CI 실패 기준에서 제외. 기존 모델을 개선·재학습하기 전 통합을 우선 수행. C 모델 사용권과 E 제품 통합심사 착수는 Owner가 허가. 테스트 때 STABLE/UNSTABLE 판정 최소 신뢰도를 사용자 UI에서 런타임 변경 가능하도록 구현.
>
> **제품 구분:** `E_OWNER_INTEGRATION_SCOPE_APPROVED` (내부 WSL2/Gazebo 제한 검증) ≠ `C_MODEL_PERFORMANCE_PASS` ≠ `E_PRODUCT_REAL_WORLD_SAFETY_PASS`. 성능 부정적 관측은 그대로 보존.

## 1. 원본 기준·확인 범위
- 기준 main `ed59fa22bb53d1590ba10eef8f7982fcf44e7d29`. D C+D 게이트 Draft PR #63 `b0b4fec30ea52b2c535d8c93c5a0f3f41b19a8d8`, 이번 브랜치는 해당 HEAD에서 시작하므로 D 기능 이력을 재구현하지 않음.
- [C Frozen v1 모델 카드](https://github.com/silverbjin/samsung_AXI/blob/main/ai/docs/C_V1_FROZEN_RESNET18_NEGATIVE_RESULT_MODEL_CARD_KO.md), [C P2 Owner 원본 감사](https://github.com/silverbjin/samsung_AXI/blob/feat/smartdish-c-dataset-v1-pilot/docs/reports/acceptance/SMARTDISH_C_V1_P2_OWNER_ACCEPTANCE_20261127_KO.md), [B QA06](https://github.com/silverbjin/samsung_AXI/blob/feat/smartdish-b-qa06-final/docs/handoff/SMARTDISH_B_QA06_TO_C_FINAL_KO.md), [C17–C19](https://github.com/silverbjin/samsung_AXI/blob/main/docs/reports/acceptance/SMARTDISH_C17_C19_SAFE_RELEASE_20261127_KO.md).
- Dataset v1 **18개 / 5 Family**, split Train11 (8S/3U), Val3 (2S/1U), Test4(3S/1U) **봉인 유지**.
- 데이터셋 버전 SHA `c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606`, split manifest SHA `8a530b6a34788300bb507ea10aafd10a7ab5616a0c0ffc0f87b7ccf79d0db6d5`, P1 plan SHA `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019`.
- Frozen ResNet18 epoch3 최저 Val CE 0.7452375, Accuracy **1/3 = 33.3%**. 다수 STABLE 참값 기준선 2/3=66.7%. 더 높은 정확도를 계산하거나 이 관측을 PASS라고 재기록하지 않음. **이번 제한 통합에서는 성능 기준 면제, 성능 FAIL 게이트 대신 `PERFORMANCE_WAIVED_FOR_INTEGRATION` 기록.**
- 원본 체크포인트 SHA `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c`; P2 Owner TAR 원본에 체크포인트 바이트는 포함되지 않았음. **현재 접근 가능한 공개 자료로 SHA를 직접 재검산하거나 torch.load한 적 없음**. 실제 private 파일을 받을 때 바이트 hash=상기 digest 검사해야 함.
- P3 Test4 **NOT_OPENED**. 재학습, A19 생성, C20 실행, 재분할 없음. 모델 성능은 새 연구에서 개선 예정.

## 2. 사용권 인수 (Owner가 통제하는 프로젝트 범위)
| 자산 | 확인 근거 | Owner가 허가한 범위 | 범위 밖 |
|---|---|---|---|
| B가 제공한 생성 이미지·물리 로그·라벨 | B QA06 Dataset v1 `PROJECT_RESEARCH_ONLY` | 내부 개발·교육용 WSL2/Gazebo **제한 통합 검증** | 데이터 재배포·제3자 공개·별도 상업 라이선스 주장 |
| C 파생 Frozen ResNet18 checkpoint | C P2 Owner SHA·P1 plan·모델 카드 | 해당 정확한 파일의 내부 제한 통합 추론(원본 비공개) | 학습 재실행, 미검증 파일 탑재, 가중치 공개·재판매 |
| Gazebo 장면·트레이 구성 | A→B 원본 메타·Owner 제작 범위 | 내부 가상 시뮬레이션 | 제3자 asset 사용 허가 자동 확장 아님 |
| TorchVision 코드 | PyTorch Vision BSD 소스 | 라이선스 고지·조건 준수 하에 사용 | 코드 라이선스로 pretrained weight 권리를 보증하지 않음 |
| ImageNet 기반 pretrained ResNet18 weights | weights SHA `f37072fd...`·출처 확인 | **내부 비공개 평가**로 제한하여 위험 관리 | 외부 상용 제품 배포 권리는 별도 법률/원권리자 검토 필요 |
| DACON 원본 | 인용/참고 링크만 | 학습·통합에 반입하지 않음 | 원본 복제·재배포 불허 |

**법적 경계:** 사용자의 Owner 권한으로 프로젝트 자체 제작 자산을 내부 통합에 사용하는 허가를 기록합니다. TorchVision 공식 pretrained weight/ImageNet 원저작권·Gazebo 타인 제작 자산에 대한 제3자 허가까지 자동 발급되는 것은 아닙니다. 상용 외부 배포 및 실물 로봇 적용은 별도의 권리 검토/성능 인수/위험 평가가 필요합니다.

## 3. E 독립 승인 범위와 모순 방지
- **승인된 것:** E가 제한된 가상 시뮬레이션에서 v1 모델 1개 SHA를 사용할 수 있는 통합 후보를 개발하고 L0/L1 및 향후 Owner L3 인수를 수행하는 권한. 모델 정확도 임계값은 **이번 통합 CI 게이트에서 제외**. 사용자는 STABLE/UNSTABLE 각각의 confidence threshold를 실행 중 조절·기록할 수 있어야 함.
- **자동 승인하지 않은 것:** 실제 checkpoint 파일 검증 완료, C 모델 성능 적합성, 미봉인 Test 성능, 제3자 재배포 권리, 원격 센서·현실 접촉 안정, 실주행 인수 PASS.
- 기존 C17 제품 로더 경로 `PRODUCT_APPROVED_CHECKPOINT_SHA256=None`과 D E 제품 기본 `None`은 보존. **별도 `owner_gazebo_integration` scope에서만 pinned checkpoint 허가**하고 ROS/D/GUI에서 모두 명시적으로 opt-in해야 함. 미승인 모델 일반 로딩 허가 금지.
- E 실제 AI ON 최초 인수에서 모델이 STABLE을 보고해도 직원 수동 `APPROVE_CONTINUE`가 있어야 다음 `TO_RETURN` Goal이 발행되는 운영 프로파일. `UNSTABLE`, `UNKNOWN`, 5초 TIMEOUT도 동일 직원 확인.
- Dynamic criteria는 **STABLE/UNSTABLE 각각의 모델 confidence 최소값**(0.50~1.00)이며 B GT label·물리 힘/좌표 기준을 바꾸는 기능이 아님. 리미트 미만은 `UNKNOWN`; 모델 예측 클래스 자체는 임의 변경하지 않음.
- E는 UI/ROS 동적 기준 변경과 실제 C/D DDS 연결을 L0/L1에서 검증하고, 실제 WSL2·Gazebo 이미지·모델 파일은 Owner 인수로 남김.

## 4. 기술적 선행 위험·보완
- C 기존 `train_classifier.py` 체크포인트 필드 `research_release_status=UNREVIEWED_NOT_FOR_PRODUCT`; C17 제품 게이트 메타데이터는 `C_RESEARCH_PILOT_ACCEPTED`를 요구하므로 **현재 파일을 제품 경로에 로딩 불가**. 이것은 기존 정책상 정상임.
- 제한 통합 로더는 **실제 바이트 SHA를 torch import/deserialize 전 확인**하고 frozen + PHYSICS_OBSERVED + split/plan/dataset 버전 + 제한 연구 상태를 검사하는 별도 정책으로 구현. 임의 모델 path/version으로 허가되지 않음.
- D UI/Manager의 AI opt-in, ROS parameter 조절, 로그 및 E 릴리스 pin의 일치 필요.
- 제품 코드와 통합 테스트는 합성 predictor로 L0/L1 검증 가능. 실제 checkpoint 부재에서 인수 PASS를 주장하지 않음.

## 5. 다음 CI/Owner 완료 조건
1. 제한된 Owner интег 허가 코드·모델 선검증·D 통합 프로파일이 L0/L1 PASS.
2. 두 임계값을 UI에서 제어하고 실제 C ROS parameter 값이 업데이트/검증/기록됨.
3. 모델 없는 모드에서는 `UNKNOWN`/Goal 없음, 모델 잘못된 SHA는 torch.load 이전 차단.
4. 사용자 WSL2 private checkpoint가 존재하면 exact SHA를 계산하고 실제 추론·ROS 캡처 1회, 직원 확인 후 동일 request_id 3-leg E 인수 수행. **이번 GitHub CI가 대신할 수 없음**.
5. 출력 `E_OWNER_INTEGRATION_CODE_READY`는 향후 현장 `E_AI_ON_OWNER_L3_PASS`와 구분.
