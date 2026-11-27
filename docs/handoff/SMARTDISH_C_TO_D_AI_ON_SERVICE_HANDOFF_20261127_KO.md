# SmartDish C → D — AI ON 서비스 연결 최종 인계 (C17~C20 정책 반영)

> **상태 (2026-11-27): \`D_AI_ON_CONTRACT_ONLY_READY / PRODUCT_AI_ON_NOT_AUTHORIZED\`**  
> D/E의 **AI OFF 3구간 서비스는 이미 사용자 WSL2 L3 PASS 및 main 병합 완료**. 본 문서는 D가 **지금** 수행 가능한 안전한 인터페이스·UI·회귀 검증과, **향후** C 모델이 별도로 인수되고 E 제품 허가가 발급된 뒤에만 수행할 실제 AI ON 연결을 명확히 나눈 인계서입니다. **현재 실제 AI ON 실행·모델 배포·Test 개봉을 승인하지 않습니다.**

## 0. 인계 기준 및 우선순위

- 리포지토리: [\`silverbjin/samsung_AXI\`](https://github.com/silverbjin/samsung_AXI); 문서 작성 시 확인한 **main \`ed59fa22bb53d1590ba10eef8f7982fcf44e7d29\`** (main 변경 시 GitHub에서 HEAD 재조회).
- 통합 제품 기준: [E PR #44](https://github.com/silverbjin/samsung_AXI/pull/44) 실제 AI OFF L3 3-leg 완료, [통합 인수 보고서](../reports/integration/SMARTDISH_MVP_FINAL_ACCEPTANCE_KO.md).
- C 안전 출고: [PR #60](https://github.com/silverbjin/samsung_AXI/pull/60) / [최종 문서 PR #61](https://github.com/silverbjin/samsung_AXI/pull/61) **MERGED**. 제품 코드 \`src/smartdish_ai/smartdish_ai/model_runtime.py\`의 E 승인 SHA 기본값은 **\`None\`**.
- 모델 기술 기록: [C18 Dataset v1 Frozen 모델 카드](../../ai/docs/C_V1_FROZEN_RESNET18_NEGATIVE_RESULT_MODEL_CARD_KO.md), [C19 안전 출고 원장](../reports/acceptance/SMARTDISH_C17_C19_SAFE_RELEASE_20261127_KO.md), [C 인계](C_HANDOFF.md).
- **B의 당시 상태를 대조할 원본:** [초기 B→C/E 핸드오프](B_HANDOFF.md) (2026-11-23, 당시 승인 데이터 0), [B-QA06 최종 B→C 핸드오프](https://github.com/silverbjin/samsung_AXI/blob/feat/smartdish-b-qa06-final/docs/handoff/SMARTDISH_B_QA06_TO_C_FINAL_KO.md) (2026-11-26, Owner 연구용 데이터 출고 18), [B-QA06→E](https://github.com/silverbjin/samsung_AXI/blob/feat/smartdish-b-qa06-final/docs/handoff/SMARTDISH_B_QA06_TO_E_READINESS_KO.md). **과거 B_HANDOFF의 데이터 0건과 과거 D_HANDOFF의 E 주행 미완료는 역사 기록이며, 최신 인수 상태가 아님.**
- 연구 브랜치 [C Dataset v1 PR #58](https://github.com/silverbjin/samsung_AXI/pull/58)는 **CLOSED / NOT_MERGED**, 기록만 보존. 차기 연구 [C20 Issue #59](https://github.com/silverbjin/samsung_AXI/issues/59)는 **OPEN / CHANGE REQUEST ONLY / NOT APPROVED**.
- 우선 적용: 제품 **AI OFF E L3 PASS**와 기존 A/D/E/Nav2/Collision Monitor 계약을 훼손하지 않습니다. 데이터 PASS → 학습 실행 PASS → 모델 성능/권리 인수 → E 제품 허가를 서로 독립된 게이트로 취급합니다.

## 1. B 최초 인계 대비 변경된 정책 — D가 반드시 읽을 부분

| 항목 | B 이전 인계의 실제 당시 설명 | 최신 B/C/E 근거 및 D에 적용할 정책 |
|---|---|---|
| 데이터 확보 | 최초 B 핸드오프: 실제 승인 **0건**, MOCK_ONLY 계약 fixture | **B-QA06 Dataset v1 연구용 출고 완료**: 후보20(6 Family), 승인18(5 Family), 제외2. 실제 출고는 \`PROJECT_RESEARCH_ONLY\`, **제품 모델 승인 아님** |
| 라벨/출처 | \`STABLE=0\`, \`UNSTABLE=1\`; MOCK/실물 격리 | 유지. \`UNKNOWN\`은 **추론·직원 확인 상태**, 학습 클래스 아님. \`STACKED/NOT_STACKED\`와 혼동 금지 |
| 분할/유사성 | \`stack_id\` 독립 분할 계획 | Family 분할 **Train11=8S/3U(F3/F4), Val3=2S/1U(F1), Test4=3S/1U(F2/F5)** 고정. 132개 승인 near-pair 판단에도 유사성 일반화 위험 잔존. D가 모델 성능을 일반화한 것으로 표시 금지 |
| 물리 GT | 증거·사람 검토 선행 필요 | 기존 A15/A16/A18 정적 world +Y **토크 명령 0.12Nm/0.5초**, RGB t0=2.0s, 외란 시작2.2s. 실제 주행 중 접촉력·실제 물리 안정성 **인증 아님**. Contact production \`HOLD\` 유지 |
| 연구용 C 학습 | 당시 \`NOT_RUN\` | C P0 private42/42, P1 pretrained CPU, P2 **Frozen 1회 실행**, P3 **read-only checkpoint 원본 SHA/메타데이터 검수**까지 기술 PASS. 이 기술 PASS로 D의 AI ON 토글 활성화 금지 |
| 모델 성능 | 당시 정확도 미측정 | Epoch3 **Validation 1/3=33.3%** (STABLE 다수 기준선 2/3=66.7%보다 낮음). \`C_RESEARCH_PILOT_ACCEPTED=false\`, 연구 모델 성능 \`HOLD\`. Test4 **미승인·미개봉·미평가** |
| 모델 출고 | PHYSICS_OBSERVED 체크포인트 준비 후 연결 예정 | C17 추가 강제 게이트: **E가 별도 승인한 모델 파일 전체 SHA**를 코드에 고정해야만 PyTorch 역직렬화 가능. \`PRODUCT_APPROVED_CHECKPOINT_SHA256=None\`. 기존 P2 checkpoint는 **D/E에 전달·사용 불가** |
| 서비스/제품 | A+D/E AI OFF 실제 주행 대기 | **D/E AI OFF 서비스 3구간 HOME→T03→DISH_RETURN→HOME의 실제 L3 PASS 이미 완료**. 반복 주행하지 않으며 AI ON은 별도 릴리스 |
| 후속 학습/새 데이터 | B 데이터 추가 및 C 모델 개선 방향 | **C20 #59는 새로운 변경 요청일 뿐 승인 아님.** A19 생산·재라벨·v1 재학습·P3 Test 개봉·v2 모델 학습은 각각 별도 명시 승인 전 불가 |
| WSL2 운용 | 인계 단계별 수동 실행 예시 | **Agent-first / WSL2 final-only:** 로직·CI·보고서는 Agent, 비공개 자산·최종 E Owner 인수에만 immutable SHA 고정 **원샷 1개**. 실패 시 TAR+SHA256만 제출. 성공한 AI OFF L3 및 P0/P1/P2/P3-pretest 재실행 금지 |

**B 원본 보존:** Dataset v1 SHA \`c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606\`, B release SHA \`2e9bddf2359cca7f0ccbd2f4ca2c2dc8a5704cf3b9a712864243167b31abd756\`, split SHA \`8a530b6a34788300bb507ea10aafd10a7ab5616a0c0ffc0f87b7ccf79d0db6d5\`. 18장/승인 JSON·물리 파일·\`.pt\`는 private 보관, GitHub·D UI·D 로그로 재배포 금지. C의 private checkpoint SHA \`6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c\`는 **연구 식별자**이지 제품 allowlist가 아닙니다.

## 2. 담당 책임과 현재 허용 범위

| 담당 | 소유권 | 지금 할 수 있는 것 | 지금 금지된 것 |
|---|---|---|---|
| **B Data** | 원본·GT·권리·Family 분할·Data Freeze | 기존 승인 증거 및 공개 계약 재사용 | v1 재라벨·재분할·A19 자동 추가 |
| **C AI** | 이미지 수신·추론 응답·제품 모델 진입 차단 | 모델 없음 \`UNKNOWN\` 계약, 승인 거부·중복·freshness·confidence 합성 테스트 | P2 미승인 \`.pt\` 탑재, 새 학습/개봉/Test, 연구 모델 PASS 주장 |
| **D Service/UI** | FSM·JSON 토픽·직원 확인·화면 | **실제 모델 없이** \`AI_CHECK/UNKNOWN/UNSTABLE/TIMEOUT/NEEDS_CONFIRMATION\` 계약 검증·UI 회귀, 승인 게이트 설계 | 제품 \`ai_available:=true\` 실주행·자동 안정성 승인·가짜 Nav2 성공 |
| **E Integration** | 제품 릴리스, A/C/D 실제 E2E 인수 | AI OFF 기준선 보존, 미래 AI ON 단계별 게이트 정의·CI | 명시 승인 없는 AI ON go-live, C17 승인 SHA 설정, 실물 안전 인증 |
| **A Robot** | A 트레이 RGB, Nav2, odom, CM, 주행 | 기존 AI OFF L3/토픽·카메라 계약 재사용 | C 연구 부족을 이유로 기존 지도/주행/CM 변경, Contact HOLD 우회 |

**현재 D의 완료 목표는 \`D_AI_ON_CONTRACT_ONLY_READY\`이며, \`D_AI_ON_RUNTIME_ACCEPTED\`가 아닙니다.** D/E AI OFF L3는 기존 완료 상태로 보존합니다.

## 3. 실제 ROS 2 인터페이스 (기존 v1.0 유지)

\`docs/integration/smartdish_d_contract_fixtures_v1.json\`과 현재 Python 코드 확인: **7개의 collection 토픽 모두 \`std_msgs/msg/String\`, UTF-8 JSON**, D/C/A간 **RELIABLE / VOLATILE / KEEP_LAST(10)**. 별도 트레이 영상은 \`sensor_msgs/msg/Image\`, C의 \`qos_profile_sensor_data\`.

| 토픽 | 발행 → 구독 | 핵심 필드/동작 |
|---|---|---|
| \`/collection/request\` | UI → D Manager | \`request_id,table_id="T03",table_wait_s=10,dropoff_wait_s=5,ai_enabled\`; AI OFF가 제품 기본 |
| \`/collection/nav_goal\` | D Manager → A Adapter | \`request_id,leg,destination_id\`; \`TO_TABLE/T03\`, \`TO_RETURN/DISH_RETURN\`, \`TO_HOME/HOME\` |
| \`/collection/nav_result\` | A Adapter → D Manager | \`request_id,leg,result\` (\`SUCCEEDED/FAILED/CANCELED\`), \`reason\`; D는 Nav2 완료를 꾸며내지 않음 |
| \`/collection/status\` | D Manager → UI | \`request_id,state,table_id,remaining_s,reason\`; UI는 다른 request_id 이벤트 무시 |
| \`/collection/ai_check_request\` | D Manager → C Node | \`request_id,capture_id\`; 적재 대기 완료 뒤 AI ON 선택 요청일 때만 발생 |
| \`/collection/stability\` | C Node → D Manager | \`request_id,capture_id,status,confidence,model_version\`; status \`STABLE/UNSTABLE/UNKNOWN\` |
| \`/collection/staff_confirm\` | UI → D Manager | \`request_id,action\` (\`APPROVE_CONTINUE/ABORT\`); \`NEEDS_CONFIRMATION\` 상태에서만 허용 |
| \`/smartdish/tray/image_raw\` | A Tray Camera → C Node | \`sensor_msgs/Image\` \`rgb8/bgr8\`; 영상 미준비·유효기간 초과·중복 시 C \`UNKNOWN\` |

모델 없는 C의 유효 응답 예시는 아래와 같습니다. **이 예시는 현재 허용된 계약 테스트용이며, 안정성 모델의 예측값이 아닙니다.**

\`\`\`json
{"request_id":"REQ-001","capture_id":"REQ-001-AI-1","status":"UNKNOWN","confidence":null,"model_version":"none"}
\`\`\`

현재 코드상의 중요한 정량 계약:
- D \`MissionManager(ai_timeout_s=5.0)\`이 \`AI_CHECK\`에서 5초 경과 시 \`NEEDS_CONFIRMATION\` + \`AI_TIMEOUT\`을 발행. D의 내부 주기는 0.2초(steady timer/monotonic).
- C \`InferenceCore(confidence_min=0.80,max_image_age_s=2.0)\`는 최신 RGB 수신 프레임이 2초 초과·사용된 프레임·잘못된 형식·없음/미승인 모델·confidence 미달이면 \`UNKNOWN\`. 중복 \`(request_id,capture_id)\` 응답은 억제.
- C 출력이 \`STABLE\`이더라도 이 상태를 D가 실제로 소비하려면 **먼저 외부 E 승인 모델의 진본성/운영 권리/성능 인수**가 선행돼야 합니다. 현재는 그러한 모델 없음.

## 4. D 상태 전이와 위험 시나리오

\`\`\`mermaid
flowchart TD
    START["AI OFF: 기존 3-leg L3 PASS 유지"] --> REQUEST["T03 요청 / TO_TABLE"]
    REQUEST --> LOAD["SUCCEEDED → WAIT_LOADING 10 s"]
    LOAD --> MODE{"해당 미션에서 AI 활성화?"}
    MODE -- "false (현재 제품)" --> RETURN["TO_RETURN → WAIT_UNLOADING 5 s → TO_HOME"]
    MODE -- "true (별도 E 승인 후만)" --> CHECK["AI_CHECK / 5 s deadline"]
    CHECK -- "실제 승인 모델의 유효 STABLE" --> RETURN
    CHECK -- "UNSTABLE / UNKNOWN / TIMEOUT" --> CONFIRM["NEEDS_CONFIRMATION / 추가 Nav Goal 보류"]
    CONFIRM -- "직원 APPROVE_CONTINUE" --> RETURN
    CONFIRM -- "직원 ABORT" --> ABORT["CANCELED / 다음 Goal 없음"]
    RETURN --> DONE["COMPLETED 또는 Nav 실패 별도 처리"]
\`\`\`

현행 D \`mission_manager.py\`에는 중요한 **추가 제품 방어가 필요한 지점**이 있습니다.

1. \`--ai-available true\`는 **현재 CLI boolean**이며 C17 모델 SHA 승인 또는 E 릴리스 영수증을 Manager가 직접 검증하지 않습니다.
2. D의 \`on_stability()\`는 같은 \`request_id\`/\`capture_id\`, 허용된 status, 유한한 0~1 confidence, \`model_version!="none"\`인 STABLE이면 **바로 TO_RETURN을 발행**합니다. D 자체에서 \`confidence>=0.80\` 또는 승인된 모델 version/SHA를 **독립적으로 검사하지 않습니다**. 현재 C 노드는 0.80 하한을 강제하지만, D의 공급자 인증이 자동 충족되는 것은 아닙니다.
3. 임의 노드가 \`/collection/stability\`에 형식상 유효한 STABLE을 퍼블리시할 경우의 제품 위험을 고려해야 합니다. \`request_id/capture_id\`는 **상관관계 ID이지 보안 서명/모델 인가 토큰이 아닙니다.**
4. \`UNSTABLE/UNKNOWN\`과 AI timeout은 \`NEEDS_CONFIRMATION\`으로 이동하며, 직원 확인 \`APPROVE_CONTINUE\`가 들어오면 다음 Goal을 발행하는 현재 기능은 유지됩니다. 직원에게 물리 확인의 책임과 근거를 표시하도록 UI/운영 절차를 정해야 하며 자동 승인으로 대체하지 않습니다.
5. **위 1~3번은 이번 인계 과정에서 발견한 코드상 미완료 제품 게이트**입니다. 기존 AI OFF L3의 실패로 판정하지 않고, 미래 AI ON 실주행 전 D/E에서 별도 수정·CI·리뷰가 필요합니다.

**D/E 후속 설계 권고(미구현):** \`AI_ON_PRODUCT_RELEASE_ACCEPTED\` 영수증(승인 모델 전체 SHA, 권리/모델 인수 상태, 사용기한 또는 출시 버전, E 코드 SHA)을 신뢰 가능한 부팅 설정으로 검증하지 못하면 \`ai_available=false\`를 강제하고 UI 토글을 비활성화합니다. D의 유효 STABLE 진행은 (a) 승인된 C 공급자, (b) 모델 버전과 제품 SHA 매칭, (c) confidence 하한, (d) 현재 미션 ID/새 capture ID, (e) 응답기한을 모두 통과한 경우로 한정해야 합니다. 구체적 영수증 서명·배포 방법은 E 보안/릴리스 설계 사항이며 **기존 7토픽 계약을 무단 변경하지 않습니다**.

## 5. D가 지금 수행 가능한 개발·검수

**조건부 D AI ON 서비스 개발을 시작할 수 있는 항목**(GitHub Agent·fixture-only CI, 실제 제품 AI ON/Goal 없음):

| 단위 | 개발/검수 | PASS 증거 |
|---|---|---|
| **D-AION-00** | main HEAD/C17·B-QA06/Owner 증거 및 E AI OFF 인수 원장 읽기 전용 확정 | 정확 SHA/상태 \`AI_OFF=PASS,AI_ON=HOLD\` |
| **D-AION-01** | 승인된 E 제품 영수증 없으면 Manager/UI \`ai_available=false\` 강제하는 **독립 제품 준비 게이트 설계/단위 테스트** | CLI true만으로 실제 AI 상태 활성 불가, 미승인 \`.pt\`/path 입력 무효 |
| **D-AION-02** | 7토픽/ID/capture/5초 timeout/2초 이미지 freshness/중복/부정확한 STABLE/저신뢰 경계 합성 검증 | 미승인·조작 응답으로 **추가 nav_goal이 발행되지 않음** |
| **D-AION-03** | \`NEEDS_CONFIRMATION\` UI, 직원 \`APPROVE_CONTINUE/ABORT\`, \`UNSTABLE/UNKNOWN/AI_TIMEOUT\` 사유/로그/중복 클릭 | 직원 명시 행위 이전 Goal 없음, ABORT 다음 Goal 없음 |
| **D-AION-04** | C 모델 없는 DDS \`UNKNOWN\` 노드와 D 합동 **NO_GOAL** CI, E A/D/C 3패키지 Jazzy L1 및 AI OFF 회귀 | fixture-only L0 / Jazzy L1 PASS, 실제 모델 성능 아님 |
| **D-AION-05** | 실제 모델을 위한 미래 E 최종 인수 시나리오/원샷·TAR SHA 계약 문서화 | **READY_ON_APPROVAL**, 아직 실행 금지 |

개발 중 주의: 기존 \`src/smartdish_robot\`, \`src/smartdish_service\`의 AI OFF 경로, \`src/smartdish_ai\`의 C17 거부 게이트, \`Nav2/Collision Monitor\`, 기존 S7 HOME→T03→DISH_RETURN→HOME를 재구현하지 않습니다. 필요한 D 보호 기능만 독립 feature branch/PR에서 최소 수정합니다. 서비스 AI ON 실주행은 지금 시행하지 않습니다.

## 6. 실제 AI ON 전 필수 선행 승인 (현재 모두 HOLD)

| 승인 경계 | 소유자 | 현재 | D가 받아야 하는 증거 |
|---|---|---|---|
| **B Dataset release** | B/PM | v1 연구용 Owner 인수 PASS | SHA/승인 범위/비재배포; **제품 모델 허가와 구분** |
| **C 연구 학습 실행** | C/Owner | P2 기술 PASS | \`TRAINED\` + checkpoint 원본 SHA, **품질 PASS 아님** |
| **C 모델 성능/위험 평가** | C/PM | **HOLD** (Val1/3), Test4 미개봉 | 사용 조건의 독립성, 오류/UNKNOWN/coverage/안전 위험 정량 평가 및 사람 승인 |
| **C 연구 모델 채택/이용권** | C/PM | \`C_RESEARCH_PILOT_ACCEPTED=false\` | 모델 카드·정확 weights SHA·권리 검토·사용 제한/비공개 공급망 |
| **E AI ON 제품 허가** | E/PM | **NOT_APPROVED** | 독립 승인 모델 SHA allowlist, 코드/릴리스 PIN, C17 provenance gate, 실패 시 AI OFF |
| **D/E 실제 AI ON 합동 인수** | D/E Owner | **NOT_RUN/NOT_AUTHORIZED** | 별도 GO 후 요청→실제 C inference→D 상태/직원 확인→A nav_goal, 실패/회귀 포함 WSL2 L3 단일 최종 증거 |

C20 [Issue #59](https://github.com/silverbjin/samsung_AXI/issues/59)는 새 Dataset v2/학습/GT/평가 프로토콜을 위한 변경 **요청**입니다. 이를 읽거나 계약 문서를 작성하는 행위는 \`C20_DATA_PRODUCTION_GO\`, \`C20_RESEARCH_TRAIN_GO\`, \`C20_TEST_SINGLE_GO\`, \`E_AI_ON_GO\`의 발급이 아닙니다.

## 7. 인수 테스트 매트릭스 — 지금 vs 미래

| 시나리오 | 현재 수행 가능 | 필수 예상 결과 |
|---|---|---|
| UI AI OFF 기본 T03→반납→HOME | 기존 E L3 증거 재사용 | 3개 실제 Nav2 \`SUCCEEDED\` + 동일 request_id/UI COMPLETED 보존 |
| \`ai_enabled=true\` but Manager \`ai_available=false\` | L0/L1 | \`AI_NOT_AVAILABLE\`, **첫 Goal 없음** |
| C 모델 없음/승인되지 않은 SHA | L0/L1, NO_GOAL | C \`UNKNOWN, confidence:null, model_version:none\`; D 직원 확인 경로만 |
| 낮은 confidence/오래된 영상/중복 capture | L0/L1, NO_GOAL | \`UNKNOWN\` 또는 응답 무시→timeout/직원 확인, 추가 Goal 없음 |
| ID 불일치/중복 STABLE/가짜 모델 버전 | L0/L1, NO_GOAL | 미인가 결과 **추가 Goal 없음**; 현재 D 코드의 보강 대상 |
| \`UNSTABLE\`/UNKNOWN/timeout 직원 확인 | L0/L1, NO_GOAL | \`NEEDS_CONFIRMATION\`, 이후 수동 승인/ABORT 분기만 |
| 실제 승인 모델의 \`STABLE\` | **미래** 별도 C/E GO 후 | 신뢰된 C 모델/파일 SHA/임계값/ID 확인, 이후만 TO_RETURN |
| 실제 AI ON 3구간 + AI OFF 회귀 | **미래** 별도 E GO 및 최종 Owner 원샷 | E의 별도 L2/L3 인수 증거 및 비공개 원본 격리 |

**검증 결과 표현:** \`D_AI_ON_CONTRACT_ONLY_PASS\`는 제품 \`AI_ON_PASS\`가 아닙니다. CI fixture는 실제 C 가중치/카메라/Gazebo/사용자 WSL2 L3 인수를 대체하지 않습니다.

## 8. 변경 관리 및 WSL2 최소 작업 정책

- Agent 우선: 기존 GitHub main/PR/CI/보고서 검토, D 전용 RED→GREEN→REFACTOR→REVIEW→COMMIT, 교육 보고, API 변경/회귀 분석을 **Agent가 수행**합니다.
- 기본 검증: synthetic-only L0, ROS 2 Jazzy L1, 공개 자산만으로 가능한 NO_GOAL L2. 새 비공개 데이터·권리 없는 가중치·실제 Test4·A19 수집을 요구하지 않습니다.
- 실제 물리/사람 확인이 기술적으로 필수인 E 최종 인수만 immutable 40자리 SHA checkout, 사전 환경·센서/모델 승인 검사, Fail-Fast, **TAR + \`.sha256\` 자동 패키징**을 하는 WSL2 **한 개 원샷**으로 제안합니다. 무한 반복 및 기존 PASS 재실행 금지.
- D의 AI ON 작업에 A/B/C/E 기능 수정을 묶어 main으로 일괄 병합하지 않습니다. 필요한 인터페이스 확장이나 승인 영수증 계약은 **영향 범위·보안 위험·기존 7토픽 유지 여부를 적은 별도 E/PM 변경 요청**으로 관리합니다.
- 기존 WSL2 E L3 실주행 AI OFF는 **재실행하지 않음**. 시각 QA는 사용자 수행이되 자동 인수 게이트에서 제외한다는 현 프로젝트 정책 유지. 권한 없는 실물 Goal 시험을 하지 않습니다.
- 연구 모델에 대한 P3 Test 평가 및 C20 데이터·학습 작업은 이 D 인계의 범위에 포함되지 않습니다.

## 9. D 담당에게 바로 전달할 실행 프롬프트

> **당신은 SmartDish D Service/UI 담당 ROS 2 Jazzy·ROS 서비스 계약·UI·CI 전문가입니다.**  
> 저장소 \`silverbjin/samsung_AXI\` 최신 main과 본 \`SMARTDISH_C_TO_D_AI_ON_SERVICE_HANDOFF_20261127_KO.md\`, \`docs/handoff/D_HANDOFF.md\`, \`docs/handoff/C_HANDOFF.md\`, B-QA06 최종 B→C 인계, \`C18\` 모델 카드 및 \`C19\` 승인 SHA 보호 코드를 먼저 읽으십시오.  
> 기존 E의 AI OFF L3 PASS 및 S7 3구간·Nav2/Collision Monitor·D UI 레이아웃을 변경하지 않습니다. C17 \`PRODUCT_APPROVED_CHECKPOINT_SHA256=None\`과 C 모델 \`C_RESEARCH_PILOT_ACCEPTED=false\`를 보존합니다.  
> D-AION-00~04를 새로운 D feature branch에서 **실제 모델 없이, Nav2 Goal 없는 synthetic/ROS 계약 CI 중심으로** 개발·검증하십시오. 먼저 현행 \`MissionManager\`의 \`ai_available=true\`가 외부 모델 승인과 독립이라는 점, D가 \`STABLE\` confidence/model SHA를 독립적으로 검사하지 않는 점을 RED 테스트로 재현하십시오. 현행 7토픽과 \`request_id/capture_id\`·직원 확인 규칙을 보존하면서, 승인된 제품 모델/신뢰된 C 공급자 없는 응답이 추가 Goal을 유발하지 않도록 보강하십시오.  
> 단위 개발 완료마다 교육 보고서와 실제 CI 결과·PASS/HOLD를 남기고, D/E 코드 경계를 넘는 변경은 PM 승인 전 HOLD하십시오. **현재 실제 AI ON, C 미승인 checkpoint 다운로드·적재, P3 Test4 개봉, 재학습, A19 및 WSL2 실행을 하지 마십시오.** 최종 E AI ON 실제 인수는 C 성능·모델 권리·제품 승인·릴리스 SHA가 별도로 통과한 이후에만 제안하십시오.

## 10. D 수신 체크리스트

- [ ] 최신 main SHA/PR #44(E AI OFF), #60/#61(C17~C19) 읽기 완료
- [ ] B-QA06 연구용 승인18/제외2, \`Train11/Val3/Test4 sealed\`, 비공개/권리 경계 이해
- [ ] C18 \`Val1/3\`, \`C_RESEARCH_PILOT_ACCEPTED=false\`, 모델 없음 상태 확인
- [ ] 제품 모델 SHA allowlist \`None\` 및 \`E_AI_ON=HOLD\` 확인
- [ ] 7-topic JSON/QoS, image \`sensor_data\` QoS, TTL 2초/AI timeout 5초 확인
- [ ] D boolean-only 활성/임의 \`STABLE\` 허용 문제를 별도 미완료 게이트로 등록
- [ ] UNKNOWN/UNSTABLE/TIMEOUT 직원 확인/ABORT, 잘못된 ID/중복/저신뢰 fail-closed 계획
- [ ] D-AION-00~04 fixture-only CI·문서·독립 PR 작업 계획
- [ ] 실제 AI ON GO는 미발급, C20 #59 미승인, A19/Contact HOLD/AI OFF 보호 유지
- [ ] Owner WSL2 신규 요청 **0회**. 최종 허가 전 실제 Goal/모델 사용 금지

**D 인수 판정:** \`D_AI_ON_SERVICE_HANDOFF_READY_CONTRACT_ONLY\`  
**제품 판정:** \`AI_OFF_E_L3_PASS / C_MODEL_PERFORMANCE_HOLD / C_P3_TEST_SEALED / C20_CR_NOT_APPROVED / E_AI_ON_NOT_AUTHORIZED\`.
