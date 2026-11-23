# SmartDish D — 일정·범위·리스크 관리 (2026-11-23)

> 담당 D / 기준 S7 main 2dd7f968dd3d24e2afb48e0917ef8c9d054ac894 / Draft PR #38

## 1. 이번 MVP에서 중요한 것
**12/02 AI OFF 실제 3-leg 성공 1회 → 12/07 기능 동결 → 12/08 리허설 → 12/09 발표.** 새 Planner/ROS msg/DB/웹서버/테이블 전면 활성화를 추가하지 않습니다. AI ON은 선택입니다.

| 날짜·마일스톤 | D 책임 | 외부 의존·승인 | 증거 및 현재 판정 |
|---|---|---|---|
| 11/23 D01~D03 | ROS 분리형 상태 머신, 7토픽·Tkinter UI | 계약 v1.0 | D 브랜치 코드 및 L0/L1, REAL_NOT_RUN |
| 11/25 T03 연결 목표 | A Subscriber READY 후 D 요청 전달 | A Adapter 및 Nav2/AMCL | A 단독 검증과 E 통합 필요 |
| 12/02 AI OFF 통합 | 10/5초·3-leg·UI COMPLETED 증거 | **A DISH_RETURN map Pose 현재 null** | BLOCKED / NOT_RUN |
| 12/03~06 예외 수정 | 최초 실패 범위만 수정 | A/C 팀 계약 영향 | 미확인 원인을 PASS로 승격 금지 |
| 12/07 기능 동결 | AI 미완성 시 AI OFF 데모 고정 | 4인 리뷰 | PLANNED |
| 12/08 리허설 | 동일 request_id와 영상 백업 | 현장 WSL2 | PLANNED |
| 12/09 발표 | PM 발표·근거 제시 | A/B/C 결과 취합 | PLANNED |

## 2. 작업 단위 및 Git 교육 이력
| ID | 코드/문서 범위 | 결과 커밋 (개발 순서) | 보고서 |
|---|---|---|---|
| D01 | 순수 FSM, 계약 pytest | 22a78f6d | docs/reports/smartdish/d/D01_MISSION_FSM_EDU_KO.md |
| D02 | ROS 2 통신·ament·fixture | e8b559be | docs/reports/smartdish/d/D02_ROS_TRANSPORT_EDU_KO.md |
| D03 | UI·픽셀 YAML·L0/L1 CI | f6aaecbe | docs/reports/smartdish/d/D03_UI_FLOORPLAN_EDU_KO.md |
| D-DBG-001 | A와 ID 검증 불일치 / AI 필수필드 | b3e9bfdb | docs/reports/smartdish/d/D_DBG_001_CONTRACT_MISMATCH_EDU_KO.md |
| D04 | 검증·인계·RTM | 후속 문서 커밋 | docs/reports/smartdish/d/D04_RELEASE_VERIFICATION_EDU_KO.md |

## 3. 요구사항 추적성 매트릭스 (RTM)
| 요구 ID | 요구사항 | 코드 | 시험 | 출고 판정 |
|---|---|---|---|---|
| D-M1 | 평면도 T03 선택·유효 request | ui_app.py / ui_layout.yaml | test_smartdish_d_ui.py, FSM invalid tests | CONTRACT_PASS_ONLY |
| D-M3 | TO_TABLE 성공 뒤 10초 대기 | MissionManager.on_nav_result/tick | test_ai_off_three_legs_exactly_wait_10_and_5 | MOCK_ONLY |
| D-M4 | DISH_RETURN 논리 Goal | LEG_DESTINATIONS | 3-leg FSM test | MOCK_ONLY / 실제 좌표 BLOCKED |
| D-M5 | 반납 SUCCESS 뒤 5초 대기 | WAIT_UNLOADING | 3-leg FSM test | MOCK_ONLY |
| D-M6 | HOME 성공 후 COMPLETED | TO_HOME result | 3-leg FSM test | MOCK_ONLY / 실제 E NOT_RUN |
| D-M7 | AI OFF 독립, AI ON 승인 | ai_enabled / staff_confirm | AI OFF/ON/timeout tests | MOCK_ONLY |
| D-ERR | 실패/중복/이전 ID 거부 | handle_request/on_nav_result | BAD/BUSY tests | MOCK_ONLY |
| A-M2 | 실제 Gazebo 주행 + odom | A Navigation Adapter | A/E 실물 인수 | NOT_RUN (D 책임 아님) |

**중요:** 계약 테스트 PASS ≠ Nav2 실제 이동 PASS. D와 A의 실제 연동에서 같은 request_id, Nav2 결과 3개, /odom 변화, UI COMPLETED가 동시에 성립해야 합니다.

## 4. 리스크 등록부
| ID | 영향 | 현재 근거 | 통제·소유 |
|---|---|---|---|
| R-D1 | 실제 회수 3-leg 차단 | A table_poses.yaml의 DISH_RETURN=null | A: map 접근점 검증 후 값 확정; E 통합 |
| R-D2 | UI 요청 유실 | RELIABLE + VOLATILE, 연결 전 pub 시 손실 | D: Manager subscriber 확인, A READY 가드 |
| R-D3 | 잘못된 성공 승격 | 가짜 Nav_Result 주입 시에도 FSM 완료 가능 | D/E: mock 증거 배제, A 실제 Result+odom 필수 |
| R-D4 | AI 미완성 | C 추론 및 tray camera 의존 | 기본 false; ON은 명시적 준비 후만 |
| R-D5 | WSLg GUI 렌더/종료 | 현장 화면 미실행 | 사용자 시각 검수; 기능 자동 게이트 제외 |
| R-D6 | 새 브랜치 충돌 | 4인 독립 작업 | 담당 경계 유지; Draft PR 후 E cherry-pick/통합 |

## 5. 변경 요청 정책
토픽·필드·enum/QoS 변경 시 공통 계약 관리자 D가 \`docs/integration/CONTRACT_CHANGE_REQUEST.md\`로 변경 전후 JSON/영향(A,B,C,D)/검증을 작성하고 **E 승인 전** 임의 변경하지 않습니다. 이번 개발에서 계약 자체의 버전 변경은 없으며 내부 입력 검증만 강화했습니다.
