# D-AION-00 — 제품 AI ON 승인·ROS 계약 읽기 전용 감사 (2026-11-27)

- 기준 main: `ed59fa22bb53d1590ba10eef8f7982fcf44e7d29`
- 필수 인계: [C→D 원본](https://github.com/silverbjin/samsung_AXI/blob/docs/smartdish-c-to-d-ai-on-handoff-20261127/docs/handoff/SMARTDISH_C_TO_D_AI_ON_SERVICE_HANDOFF_20261127_KO.md), Draft PR [#62](https://github.com/silverbjin/samsung_AXI/pull/62) — **main에는 아직 없는 문서**. 이를 read-only 기준으로 사용함.
- 과거 AI OFF E 인수: `docs/reports/integration/SMARTDISH_MVP_FINAL_ACCEPTANCE_KO.md`, PR [#44](https://github.com/silverbjin/samsung_AXI/pull/44), **재실행 금지**.
- C의 코드 근거: `src/smartdish_ai/smartdish_ai/model_runtime.py` → `PRODUCT_APPROVED_CHECKPOINT_SHA256 = None`; `src/smartdish_ai/config/model.yaml` → `model_path: ''`. 현재 출고 모델 없음.
- C17~C19: C의 Frozen ResNet18 1회 학습은 기술 인수만; Val 1/3=33.3% < 다수 기준 2/3=66.7%. `C_RESEARCH_PILOT_ACCEPTED=false`, P3 Test4 봉인. B Dataset v1은 **연구용 18건**이고 제품 성능 승인 아님.
- C20 #59: 변경 요청만 있고 새 데이터 생성·학습·Test 개봉 승인이 아님.

## 소스 감사 → 취약 경계 (수정 전 RED 예상)
1. `manager_node.py`: CLI `--ai-available true`가 C17/E 제품 영수증 없이 `MissionManager(ai_available=True)`를 구성합니다.
2. `ui_app.py`: 같은 CLI 불리언만으로 GUI AI Checkbutton을 활성화합니다.
3. `mission_manager.py::on_stability`: 같은 request_id/capture_id + 유효 `STABLE` + `confidence=0.1`, `model_version='fixture-v1'` 등의 값으로도 바로 TO_RETURN을 진행할 수 있습니다. D에서 모델 승인 SHA와 confidence>=0.80의 독립 검증이 없습니다.
4. AI_CHECK 시간 만료 시점의 ROS timer가 아직 실행되지 않았다면 지연 STABLE이 accepted 될 수 있으므로 수신 시 deadline 재확인이 필요합니다.
5. `request_id/capture_id`는 상관관계 식별자일 뿐 보안 인증/서명이 아닙니다. ROS 2 토픽 Publisher의 진본성은 별도 E 보안 설계 및 운영 전제입니다.

## 보존할 현재 계약
- 7개 `/collection/*`: `std_msgs/msg/String` UTF-8 JSON, RELIABLE/VOLATILE/KEEP_LAST(10). C 영상은 `/smartdish/tray/image_raw`의 `sensor_msgs/msg/Image`, sensor_data QoS.
- AI OFF T03→DISH_RETURN→HOME 주행, Map, Nav2, Collision Monitor, WSL2 L3 이전 PASS 모두 재검하지 않음.
- D AI_CHECK timeout 5초(monotonic + STEADY_TIME), C frame freshness 2초, C confidence_min 0.80. C 미승인 모델에서는 UNKNOWN/none만.
- `NEEDS_CONFIRMATION`: 직원의 명시적 `APPROVE_CONTINUE`/ `ABORT` 전에는 다음 Goal 없음.

## 개발 단위·게이트
| 단위 | 작업 | 허용 증거 |
|---|---|---|
| D-AION-01 | Manager/UI 제품 Gate, CLI 우회 방어 | synthetic RED→GREEN; 미승인 모델 사용 0회 |
| D-AION-02 | ID/capture/5초/모델 버전/SHA/저신뢰·UNKNOWN | L0 synthetic, NO_GOAL |
| D-AION-03 | 직원 승인/ABORT·중복 확인 회귀 | L0 synthetic, NO_GOAL |
| D-AION-04 | C 모델 없는 UNKNOWN 계약 + D/E AI OFF 보존 | 공개 GitHub L0 및 실제 Jazzy L1, NO_GOAL |

## 정책 및 미승인 항목
- 제품 E 승인 영수증 및 신뢰된 C Publisher 검증 방식은 **현재 미정의**. 이번에는 승인 상수 미설정 시 강제 OFF로 막고, 별도 E/PM 보안·릴리스 승인 이전 AI ON을 허용하지 않음.
- 비공개 이미지/weights, P3 Test4, C20 신규 학습, A19 생산, 실제 ROS AI ON/Gazebo/WSL2 실주행은 **NOT_RUN / NOT_AUTHORIZED**.
- 최종 기대 마커: `D_AI_ON_CONTRACT_ONLY_READY` (제품 AI ON PASS 금지).
