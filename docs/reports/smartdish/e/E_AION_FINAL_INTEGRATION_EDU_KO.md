# SmartDish E — C v1 Owner AI ON 제한 통합 개발·CI·교육 최종 보고서 (2026-11-27)

## 1. 수행 목적·권한과 결과
- Owner 사용자 지시에 따라 C20 별도, C v1 Validation 33.3% 성능 기준은 **이번 통합만 면제**. 수치는 그대로 기록, 모델 성능 적합성 PASS를 주장하지 않음.
- Owner는 자체 프로젝트 데이터 및 C v1 체크포인트를 **내부 WSL2/Gazebo 제한 통합**에 사용하는 권한과 E 독립 통합 심사 착수를 승인. 외부 배포·상용 판매·현실 물리 안전성 인증은 미인수.
- **코드 최종 검증 SHA**: \`4dbdeca6a0a8f8120cb42a44bd589d356726eb5d\`.
- [CI 최종 #45929414512](https://github.com/silverbjin/samsung_AXI/actions/runs/45929414512): **L0 131 PASS**, 실제 Jazzy **L1 3패키지+모델 없는 DDS 파라미터/적용 ACK PASS**.
- **판정**: \`E_OWNER_GAZEBO_INTEGRATION_APPROVED\` / \`E_OWNER_AION_CODE_L0_L1_PASS\` / \`E_OWNER_PRIVATE_MODEL_AND_L3_PENDING\`. 기존 AI OFF 3-leg PASS 보존.

## 2. 사용 도구·개발 방식
| 도구 | 사용 목적 | 결과 경계 |
|---|---|---|
| GitHub branch/PR + immutable SHA | main AI OFF 보호, C17/D 계약 변경 최소 범위 | 출고 코드 HEAD 추적 |
| Python 3, pytest | C 신뢰도 예측/UNKNOWN, model SHA/metadata, D 수동 승인 L0 | 합성 모델, 실제 성능 아님 |
| ROS 2 Jazzy rclpy + AsyncParameterClient | C 파라미터 동적 갱신과 D UI/Manager 연결 | DDS 수신 확인, GUI 시각 아님 |
| Tkinter Spinbox/Toplevel | STABLE/UNSTABLE 0.50~1.00 기준을 실행 중 변경 | 실제 화면은 Owner 검수 |
| TorchVision ResNet18 loader | 정확한 Owner P2 checkpoint SHA 후 metadata 검증 | private bytes 없음, 실제 load NOT_RUN |
| colcon/ament_python/ROS launch | C/D/A 기존 패키지 빌드 및 C+D 제한 통합 런치 | Nav2/Gazebo 자동 시작 없음 |
| Bash one-shot + Python SHA preflight | WSL2 독립 소스 PIN·원본 모델 bytes SHA 검사 | 사용자 환경 필요 |
| GitHub Actions CI | L0 synthetic/L1 actual ROS parameter service/NO_NAV2 | Owner L3 대체 불가 |

## 3. 변경된 실제 모듈
1. \`InferenceCore\`: 클래스별 confidence threshold(기본 0.80, 유효 범위 0.50~1.00), 유효성·유한값/원자적 변경·기준 미달 UNKNOWN. C의 원래 frame cache/요청 dedup 보존.
2. \`StabilityInferenceNode\`: ROS parameters \`stable_confidence_min\`, \`unstable_confidence_min\`, update callback, \`C_DYNAMIC_THRESHOLD_APPLIED\` 및 요청별 임계값 로그.
3. \`model_runtime.py\`: **제품 C17 기본 gate(None)는 그대로**, Owner v1 내부 Gazebo 프로파일 명시 시 \`6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c\`의 실제 bytes SHA를 torch import 이전 검증; Frozen/연구 status·Dataset/split/plan metadata 일치 검사. 가중치 미탑재.
4. D \`product_admission\`/Manager/UI: Owner v1 프로파일에만 AI ON 허용, 일반 제품 기본 false. STABLE/UNSTABLE/UNKNOWN/timeout 모두 직원 명시 승인 전 **TO_RETURN Goal 0**. ROS graph의 smartdish_navigation_adapter 이름 확인으로 관측자 구독 오진 차단(신원 인증은 아님).
5. GUI: AI OFF 화면은 그대로; Owner scope에서만 'STABLE / UNSTABLE 판정 기준 설정' 버튼 활성화. 팝업은 C 기존 값을 읽고 두 값을 ROS set_parameters_atomically 호출, ACK 후에만 UI 적용 완료 표시. 진행 중 임무에는 변경 거절.
6. 새 \`smartdish_e_owner_aion.launch.py\`: C+D만 시작, owner_gazebo_integration·model_path 기본 보수적. A Nav2 별도.
7. \`smartdish_e_owner_model_preflight.py\`/ \`smartdish_e_owner_aion.sh\`: model checkpoint SHA-only private preflight, 전용 worktree, SHA pin, WSLg 실행 모드; 사용자 WSL2 검수 준비.

## 4. 교육용 RED→GREEN 이력
| RED Run | 최초 원인 | 최소 조치 | 재검 |
|---|---|---|---|
| [#45928798798](https://github.com/silverbjin/samsung_AXI/actions/runs/45928798798) | InferenceCore 프레임 cache 초기화가 return 뒤로 이동 → 19 FAIL | 생성자에 5개 필드 복구 | [E-DBG-001](E_DBG_001_INFERENCE_CACHE_INITIALIZATION_EDU_KO.md) |
| [#45928898785](https://github.com/silverbjin/samsung_AXI/actions/runs/45928898785) | ROS 관측자 Subscriber를 A로 오진 → A 미연결 상태에서 논리 Goal | 실제 A node_name 및 후속 Goal 발행 경계 검사 | [E-DBG-002](E_DBG_002_DDS_ADAPTER_SUBSCRIBER_20261127_KO.md) |
| 최종 [#45929414512](https://github.com/silverbjin/samsung_AXI/actions/runs/45929414512) | L0+L1 반복 회귀 | PASS 131 + 3pkgs/DDS | E_OWNER_AION_CODE_L0_L1_PASS |

## 5. 동적 STABLE/UNSTABLE 판단 기준 예시
- STABLE 최소 0.65, UNSTABLE 최소 0.90 설정 (실제 ROS parameter ACK 확인).
- C 모델이 STABLE(0.70)을 예측하면 C는 STABLE을 발행, D Owner 모드는 유효 모델 버전·capture_id/5초를 확인 후 NEEDS_CONFIRMATION에 진입. **직원 승인 전 TO_RETURN Goal 없음**.
- C 모델이 UNSTABLE(0.70)을 예측하면 클래스 임계값 0.90 미만 → C는 UNKNOWN을 발행, 직원 확인으로 전이. 물리 정답은 변경되지 않음.
- 0.49, NaN, Inf 등은 거절, 기존 임계값 유지. 응답 모형으로 수행한 예시는 *합성 통합 계약*, 실제 weights 없는 경우 C는 항상 UNKNOWN.

## 6. 남은 Owner 최종 인수
- [E Owner 인계·명령 가이드](../../../handoff/SMARTDISH_E_OWNER_V1_AI_ON_INTEGRATION_20261127_KO.md)에 따라 정확한 private checkpoint를 동일 SHA로 검수하고 실제 ROS C 추론/GUI 작동 확인.
- A Adapter/Nav2/CM 준비는 기존 원샷·TTY 인간 승인 재사용. **A 단독 3구간 데모와 E 실제 통합을 동시에 실행하면 안 됨.**
- 단일 request_id로 C 판정·threshold·직원 confirm·A 3-leg Nav2/odom·D 10/5초·UI COMPLETED·TAR+SHA256 기록.
- Test4는 여전히 봉인; C20 연구 별도. 외부 상업·현실 접촉 안전 인수/서드파티 라이선스는 별도.

## 7. 종결 마커
- \`C_V1_PERFORMANCE_WAIVED_FOR_INTEGRATION\` (원본 33.3% 기록 유지)
- \`E_OWNER_INTERNAL_USE_SCOPE_APPROVED\` (Owner가 통제하는 자산의 내부 사용만)
- \`E_OWNER_AION_CODE_L0_L1_PASS\`
- \`E_OWNER_MODEL_BYTES_NOT_VERIFIED_IN_CI\`
- \`E_OWNER_AION_WSL2_L3_NOT_RUN\`
