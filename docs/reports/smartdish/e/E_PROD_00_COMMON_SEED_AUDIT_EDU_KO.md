# E-PROD-00 — 공통 개발 Seed 감사 및 배포 교육 보고서 (2026-11-27)

## 1. 판정
- E-PROD-00 저장소/기준선 감사 PASS, `E_PROD_COMMON_SEED_READY`: A/B/C/D 독립 개발 착수 가능.
- 공통 계약 v1.1 / schema_version=2 / profile=OWNER_PRODUCT_RECOVERY. 문서 원본은 main의 배포본과 바이트 동일. 이 보고서는 Seed 공지 및 구현 경계이며 새 운영 코드, 제품 AI ON 승인 또는 L0~L3 신규 PASS가 아니다.
- 공통 Seed는 **이 보고서를 포함하여 배포한 커밋**이다. SHA 자기 참조를 피하기 위해 정확한 전체 SHA는 신규 E Draft PR 본문에 기록한다. 아래 merge SHA는 Seed의 부모이며 실제 역할 분기에는 PR 본문의 고정 Seed SHA를 사용한다.

## 2. WHAT / WHY
기존 E R4는 실제 Nav2 3구간과 독립 Gazebo station RGB 및 CI test double 연계 성공. 사용자 WSL2에서는 실제 C v1 로딩/추론 및 T03 주행은 성공했으나 초기 접시 누락, 실제 장착 tray/camera 및 transfer 미구현, 직원 승인 대기 후 강제 종료. 제품 L3 FAIL/HOLD. 독립 station CI PASS를 단일 월드 제품 PASS로 오인하지 않는다. 기존 S7 식기 startup, A13 물리/영상, C/D runtime 개선을 재사용한다.

## 3. HOW — 실제 Git 감사
| 대상 | 실제 SHA/상태 |
|---|---|
| 문서 이전 main | a64f54145762c88fd83ce237f4d494f4f0bb33f5 |
| 현재 main / PR #65 | 1d7bbf244143aeb8a9b6c71f9c2605d53ac38b4b |
| 기존 E Draft #64 | 753cbb24c5a3d684461793731ee27fc540abd086, open/draft/unmerged |
| E 실제 기능 검증 PIN | 77a1ae256cf4a008c8cefc16a32c43bfc40c7d08 |
| 두 부모 merge | d69a3f9cbb82d06421c9ebe5f8b603245642e742 |
| 공통 계약 blob | 608bc9950d8f149e5b0a129394055ca19132633a |

- 필수 README, 00_COMMON_CONTRACT, 01_E_DEVELOPMENT_SPEC, 06_INTEGRATION_RUNBOOK 원본을 배포 SHA에서 읽었다.
- Git compare: 이전 main→문서 main, 추가 Markdown 8개만. E 기능 PIN→E head, Markdown 3개만. E head→두 부모 merge, 동일 main 명세 Markdown 8개만. 충돌/소스 코드 변경 없음. merge 부모 순서 E head, main. main과 E 기존 브랜치 모두 유지; force/reset/rebase 없음.
- 실제 PR #35 S7 startup, #44 AI OFF L3, #45 A11~13, #60 C17~19, #63 D contract, #65 docs 모두 merged. 다시 병합하지 않는다.
- 실제 Git tree 비교: 기존 main의 지도/restaurant 패키지/A 로봇/ai data/train 및 S6/S7/A/tray/AI OFF 실행 경로에 해당하는 79개 tracked blob 동일. E의 기존 C/D 변경 파일은 검증 PIN과 동일. 신규 연구 파일 및 가중치 추가 없음.
- model_runtime.py의 PRODUCT_APPROVED_CHECKPOINT_SHA256=None, product_admission.py의 E_APPROVED_PRODUCT_RELEASE_SHA256=None/E_APPROVED_MODEL_SHA256=None 확인. Owner 예외는 별도 scope 및 기존 v1 SHA만. C20 관련 #61 인계와 archived research #58 미병합 확인. #59 개별 PR 조회는 404로 직접 검증하지 못했으며 그 브랜치/PR을 변경하거나 병합하지 않았다. Test4 내용 열람 없음.

## 4. 재사용하는 CI 원장 (새 실행 아님)
| 증거 | 결과 / 범위 |
|---|---|
| [R4 45939257386](https://github.com/silverbjin/samsung_AXI/actions/runs/45939257386) | SUCCESS, exact 77a1ae256cf4a008c8cefc16a32c43bfc40c7d08, 실제 Nav2+독립 station CI double |
| [E L0/L1 45939257362](https://github.com/silverbjin/samsung_AXI/actions/runs/45939257362) | SUCCESS, exact 77a1ae256cf4a008c8cefc16a32c43bfc40c7d08, 기존 보고서 기준 L0 150 / installed source / DDS |
| [Restaurant 45939954749](https://github.com/silverbjin/samsung_AXI/actions/runs/45939954749) | SUCCESS, exact 753cbb24c5a3d684461793731ee27fc540abd086; L0 및 L1 build+L2 actual no-goal smoke success, map publish skipped |
| 기존 Owner AI OFF L3, R1/R2 | 기존 원본 인수 근거 재사용; 재실행하지 않음 |
| 신규 single-world L0/L1/L2/L3 | NOT_RUN; 새 기능 구현 후 CI/Owner 검증 |

G0은 Git ancestry/blob/문서 기준 감사이다. 동일 소스의 Gazebo 재실행을 요구하지 않는다. 신규 Draft PR의 자동 CI는 별도 상태로 기록하며 실행 중/취소를 PASS로 처리하지 않는다.

## 5. 보호 범위 및 담당별 인계
| 역할 | 고정 신규 브랜치 | 파일 소유 및 시작 단위 |
|---|---|---|
| E | integration/smartdish-product-recovery | common contract, 통합 runner/witness/CI, E-PROD-01 |
| A | feat/smartdish-a-product-collection | smartdish_robot, generated world/robot/bridge, A-PROD-00 |
| B | feat/smartdish-b-product-evidence-qa | ai evidence verifier/QA, B-PROD-00 |
| C | feat/smartdish-c-product-inference | smartdish_ai/추론, C-PROD-00 |
| D | feat/smartdish-d-product-fsm | smartdish_service/FSM/UI, D-PROD-00 |

각 담당은 PR 본문에 기록된 동일 immutable Seed에서 분기. 역할 branch는 각 담당이 직접 생성; PR base=integration/smartdish-product-recovery. E만 통합. A→C→D→B 순. main 대상 기능 PR 금지. A14~18/B 연구/C20/Test4/모델 권리 보호. 기존 AI OFF 및 station runner 변경 금지. 필요 시 E 합의 후 선택적 최소 이식. 공통 계약 v1.1 원본은 동결하고 변경은 E review docs PR로 관리한다.

## 6. 실제 감사에서 확인한 후속 구현 주의사항
- 기존 R4 runner는 독립 station partition을 만든다. 이를 제품 실행기로 사용하지 않는다. 실제 단일 world, 장착 카메라, 식기 이동을 새 경로에서 검증한다.
- 기존 E R4 workflow push filter는 옛 E 브랜치 전용이다. 각 역할은 신규 branch 및 integration PR에 실제로 trigger되는 역할 CI를 작성/검수한다. E 신규 product workflow에서 single-world scope를 검증한다. 기존 성공 CI를 신규 브랜치 검증으로 표기 금지.
- 기존 A navigation_adapter의 취소는 interruption cancelTask 중심이고 terminal ACK 계약은 아직 없다. A/D는 nav_goal 수락 시 실제 UUID를 D가 확보하는 방법, UUID 확인 전 timeout 시 A의 자체 취소/lockout, terminal과 stop receipt 순서를 E와 합의해야 한다. 신규 메시지/필드 변경은 공통 문서 PR 승인 후 적용. UUID 추측·가짜 result 금지.
- 초기 stack_id를 D가 알 수 있도록 A의 초기 entity manifest/receipt와 공통 설정을 연결하고, capture 이전 ABORT correlation 및 READY 출처는 A/D/E 협의. 공통 계약에 없는 필드의 독자 확장은 금지. 이 항목은 해당 경계 통합 전 차단이며 독립 감사/fixture/물리 구현을 시작하는 데는 차단이 아니다.
- 기존 station bootstrap은 이전 두 PIN만 이동 허용하며 현재 Owner 실패 실행 PIN 77a1ae25는 허용하지 않는다. E-PROD-03에서 새 독립 작업경로 또는 검증된 clean descendant 전환을 설계. 기존 사용자 파일/venv 보존, 새 torch 설치 금지. 지금 사용자에게 실행 요청하지 않는다.
- 제안 deadline/stop 수치는 실제 CI로 검증 후 확정. 0.00 threshold는 정상 predictor 결과의 통합 확인용일 뿐 모델 성능/권리/안전 우회가 아니다.

## 7. 교육 포인트 및 다음 단계
두 부모 merge는 서로 다른 기능/문서 이력을 보존한다. Git source-equivalence 감사와 런타임 성공은 다르다. Seed는 개발자 모두가 같은 코드로 출발하도록 만드는 계약이지 제품 인수 증거가 아니다.
A/B/C/D 착수 후 각자 RED→분석→최소 수정→CI GREEN→REVIEW→교육 MD/commit→Draft PR. E는 actual artifact, SHA, 권리/범위 검수 후 역할별 PR을 통합한다. G1~G5 NOT_RUN, Owner product L3 HOLD, 제품 AI ON admission DENIED. 최종 Owner 1회 인수 및 명시 승인 전 main 병합 금지.
