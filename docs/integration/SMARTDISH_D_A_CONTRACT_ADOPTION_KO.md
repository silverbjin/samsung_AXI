# SmartDish D — 계약 v1.0 채택 및 A/C 인터페이스 판정

## 1. 단일 기준
\`SMARTDISH_MVP_INTERFACE_CONTRACT_v1.0_KO.md\` (사용자 제공 원문)을 기준으로 하며 신규 토픽/enum을 만들지 않았습니다. 샘플은 \`docs/integration/smartdish_d_contract_fixtures_v1.json\`에 포함됩니다. 전 토픽 \`std_msgs/msg/String\`, UTF-8 JSON, \`RELIABLE, VOLATILE, KEEP_LAST(10)\`.

| 토픽 | D 발행 | D 구독 | 인수 주의 |
|---|---|---|---|
| /collection/request | UI | Manager | request_id/T03/10/5/ai_enabled |
| /collection/nav_goal | Manager | A | 3가지 leg/destination 조합만 |
| /collection/nav_result | A | Manager | 실제 Nav2 완료, request_id/leg 일치 |
| /collection/status | Manager | UI | state/remaining_s/reason |
| /collection/ai_check_request | Manager | C | AI ON 만 |
| /collection/stability | C | Manager | capture_id·confidence·model_version 검증 |
| /collection/staff_confirm | UI | Manager | 직원 APPROVE_CONTINUE 또는 ABORT |

## 2. A 실제 코드와 교차 확인
- A 작업 브랜치: \`feat/smartdish-a-robot\`, Draft PR #36.
- A \`navigation_adapter.py\`는 \`/collection/nav_goal\`을 구독하고 같은 \`request_id\`/leg를 \`/collection/nav_result\`로 돌려줍니다.
- 실제 Nav2/AMCL/scan/odom/TTY 준비 뒤에만 A Goal 구독을 생성합니다. D는 구독자가 0이면 \`ADAPTER_NOT_READY_NO_GOAL\`을 반환합니다.
- 기존 S7의 \`PICKUP_RETURN\`은 신규 \`DISH_RETURN\`이 아닙니다. A의 \`DISH_RETURN\` map Pose는 현재 **null**이므로 실제 3-leg 완료를 주장하지 않습니다.
- A는 이동 및 odom 판정, D는 대기시간·UI 판정을 소유합니다.

## 3. AI 선택 기능
B는 ROS가 아닌 데이터 전달, C가 선택형 판정 노드를 소유합니다. \`STABLE/UNSTABLE/UNKNOWN\`는 S7 \`STACKED/NOT_STACKED\`와 다릅니다. C의 \`STABLE\`은 동일 capture_id와 필수 confidence(수치), model_version을 충족해야 합니다. 누락/timeout이면 직원 확인 전 진행하지 않습니다. 모델 미완성 시 \`ai_available=false\` 사용.

## 4. 제안 통합 실행 순서
\`\`\`mermaid
flowchart TD
  PRE["A Nav2/AMCL/scan/odom READY + TTY 승인"] --> SUB["A nav_goal 구독 생성"]
  SUB --> D["D Manager + Tk UI 실행"]
  D --> CLICK["T03 클릭 및 request_id 생성"]
  CLICK --> A["D nav_goal → A NavigateToPose"]
  A --> RES["A nav_result / odom 실측"]
  RES --> W["D 10초 → 반납 → 5초 → HOME"]
  W --> DONE["UI COMPLETED + 같은 ID 증거"]
\`\`\`

실주행 이전에 \`DISH_RETURN\` 좌표·접근 가능성을 A가 확정해야 합니다. D가 임의 Pose를 넣거나 Nav_Result를 만들어 우회할 수 없습니다.

## 5. 계약 수정 요청 여부
2026-11-23 기준 계약 API 변경 요청은 없습니다. D-DBG-001은 A와 D의 **입력 검증 일치**를 위한 내부 수정입니다. 실제 통합 중 새 필드가 필요해질 때만 A/B/C 영향 설명을 붙여 변경 요청을 작성합니다.
