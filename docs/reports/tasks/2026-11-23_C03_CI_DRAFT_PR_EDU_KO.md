# C03 — 독립 GitHub CI 및 Draft PR 준비·리뷰 보고

- 날짜: 2026-11-23 / 판정 **로컬 C L0 PASS, GitHub CI는 Run 결과 확인 필요**
- base: `main@2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`
- head: `feat/smartdish-c-stability` (최종 SHA는 GitHub PR head를 단일 출처로 사용)
- 새로운 저장소를 만들지 않았고 S7 기능/안전 코드는 건드리지 않았습니다. main merge 금지.

## CI 구성과 이유

C만 테스트하는 `.github/workflows/smartdish-c-contract-ci.yml`을 추가했습니다. `pytest + Pillow + NumPy`만 설치하고 torch 사전학습 weight 다운로드, ROS/Gazebo 기동 없이 **실패 안전 계약**을 검증합니다. C의 학습 데이터와 트레이 카메라가 아직 없으므로 무거운 Gazebo 기반 AI ON 검증을 억지로 추가하지 않았습니다. 기존 `restaurant-ci.yml`이 PR에서 별도로 트리거될 수 있으나 S7 회귀의 L2 결과를 C AI ON 실제 통합 성공으로 해석하지 않습니다.

## PR 인수 요건

1. `ai/train/`, `ai/evaluation/`, `ai/docs/MODEL_*` 및 `src/smartdish_ai/` 변경만 C가 소유하며 B 원본 데이터·A World·D FSM 수정은 없습니다.
2. 코드는 컴파일/계약 테스트 **20개 로컬 PASS**. GitHub Actions 결과는 run ID가 발급되면 별도 확인하여 갱신해야 합니다.
3. 실제 데이터 수 0, `TRAINING_NOT_RUN`, `ROS_IMAGE_LIVE_NOT_RUN`, `AI_ON_OPTIONAL_PASS=NOT_RUN`을 PR 본문에 명시합니다.
4. B Draft PR #37을 먼저 검토·병합한 뒤 C PR을 통합합니다. AI OFF 필수 임무의 인수는 별도 A+D 소유입니다.
5. 학생이 코드를 따라가며 원인→테스트→보고서→커밋→PR을 역추적할 수 있도록 작업별 교육 보고서와 model card를 한 PR에서 교차 링크합니다.

## 결과/남은 작업

C GitHub CI Run과 PR 생성은 본 보고서와 같은 최초 코드 제출 이후 발생합니다. **발생하지 않은 run, SHA 또는 PR 번호를 여기에 선기입하지 않았습니다.** 추후 확인하면 PR 본문·커밋 이력으로 연결합니다. CLI smoke와 training 실측은 출고 이전에 `NOT_RUN` 유지합니다.

### 검토 질문

- 저장소의 S7 L2 PASS가 C의 실측 AI ON PASS를 보증하지 않는 이유는 무엇입니까?
- PR을 Draft로 보류하면서도 L0 계약 테스트를 먼저 수행하는 이점은 무엇입니까?
