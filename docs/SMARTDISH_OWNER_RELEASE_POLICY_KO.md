# SmartDish 개발 및 Owner 출고 정책

## IMMUTABLE_SHA_ISOLATED_BOOTSTRAP
검증된 40자리 commit SHA만 직접 fetch 및 checkout한다. 개발 작업공간과 Owner 인수 작업공간을 분리하고 SHA별 및 실행별 독립 디렉터리를 만든다. 실행 전에 실제 HEAD, origin, 필요한 branch 이름, tracked clean 상태를 확인한다. 최신 HEAD fetch/merge, reset/clean, 자동 fallback, 무한 재시도 금지. 실행기와 실행 코드는 검증된 SHA에서 제공하고 CI 결과와 실행 SHA, 원본 archive SHA, 최초 실패를 기록한다.

## CHANGE_SCOPE_BASED_CI_GATE
| 변경 | 독립 Owner 출고 필수 CI |
|---|---|
| 데이터 수집기 | 데이터 수집 전용 CI |
| AI 모델 | AI 모델 전용 CI |
| UI | UI 및 인터페이스 CI |
| 자율주행 제어 | Nav2 및 안전제어 CI |
| 공통 인터페이스 | 생산자/소비자 계약 CI |
| 복수 영역 | 필요한 CI의 합집합 |
| 전체 제품 main 병합/출고 | 전체 통합 회귀 CI |

경로뿐 아니라 의존 관계와 계약의 영향 범위를 검수한다. 영향 불명확하면 범위를 확대한다. 재사용하는 PASS는 실행 SHA, Run/Artifact ID, SHA256, diff와 영향 분석을 남긴다. 미완료/실패를 PASS로 승격하지 않는다. 무관한 전체 회귀의 진행만으로 독립 인수를 차단하지 않는다. main 병합은 전체 통합 회귀 PASS 및 별도 사용자 승인 필수. 사용자 인수는 Cloud CI와 별개.

## R03 데이터 수집의 독립 판정
GUI 기본, 시각 검수는 사용자 담당. 데이터 품질, GUI, server/aux cleanup, evidence integrity, human GT를 각각 판정한다. GUI 오류를 숨기거나 모든 nonzero를 성공 처리하지 않는다. 완료된 물리 데이터가 검증되었고 모든 소유 프로세스가 정리되었을 때만 다음 독립 장면 실행을 허용할 수 있다. server SIGSEGV는 별도 FAIL/HOLD이며 전체 clean shutdown PASS를 금지한다. 원본의 실행 SHA와 재검수기 SHA를 분리한다. 자동 GT 승인/학습 누출 금지.
