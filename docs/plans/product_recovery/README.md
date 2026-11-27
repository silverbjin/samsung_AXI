# SmartDish 제품 복구 개발 명세 v1.1 (2026-11-27)

이번 문서는 2026-11-27 실제 WSL2 인수 문제에 대한 개발 재개 기준이다. 기존 독립 station CI 통합을 실제 식기 회수 제품 시나리오로 확장한다. 문서 배포이며 신규 구현/CI PASS 아님.

| 읽는 순서 | 문서 |
|---|---|
| 1 | [공통 시나리오·인터페이스·안전·CI 계약](00_COMMON_CONTRACT_KO.md) |
| 2 | [E 통합 담당](01_E_DEVELOPMENT_SPEC_KO.md) |
| 3 | [A 로봇·식기·카메라](02_A_DEVELOPMENT_SPEC_KO.md) |
| 4 | [B 데이터·증거 QA](03_B_DEVELOPMENT_SPEC_KO.md) |
| 5 | [C 추론·임계값](04_C_DEVELOPMENT_SPEC_KO.md) |
| 6 | [D FSM·UI·예외](05_D_DEVELOPMENT_SPEC_KO.md) |
| 7 | [브랜치·CI·통합 및 재개 절차](06_INTEGRATION_RUNBOOK_KO.md) |

E가 공통 seed를 먼저 확정하고 A/B/C/D가 동일 seed에서 병렬 개발한다. 각 담당은 이 README, 공통 계약, 본인 명세, 통합 절차를 모두 읽는다. 기존 AI OFF 및 R1/R2 성공, C17 deny, C20/Test4, 원본 data/weight 보호. 기존 main의 S7 초기 식기 및 A13 재사용. 새 제품 profile은 실험 전용, 독립 station 사용 금지. 문서 병합으로 기능 코드를 main에 넣지 않는다.

## 문서 QA
7개 상대 링크, 역할 branch/PR base, A→C→D→B 통합 순서, 공통 ID/시간/예외 계약 및 Owner 전용 0~1 threshold가 일치하도록 검토한다. 제안 timeout/정지 수치는 신규 CI에서 실측 후 E 승인 필요. 세부 파일명은 구현 후보이며 실존 파일이라고 주장하지 않는다.
