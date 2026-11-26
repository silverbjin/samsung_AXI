# SmartDish PLATFORM-P0 — 공통 기준·병합 정책 (KO)

## 1. 기준 및 브랜치
- main = 제품 Owner 인수 승인본. 현재 63e147289e307e0b9900ca365e9c4557c5921804. 사용자 별도 승인 및 전체 통합 CI 전에는 변경 금지.
- platform/smartdish-stable = main에서 분기한 검증된 공통 환경/계약. feature 전체를 가져오지 않는다. fix/shared-* PR의 CI와 영향 분석 완료 후 승인된 변경만 merge commit 또는 명시적 fast-forward. 기존 인수 SHA는 불변.
- A/B 공개 개발 PR #47/#46 유지. 공유 수정은 platform으로 먼저 분리, 검증 후 해당 브랜치에 merge commit으로 동기화. 강제 push, rebase, reset, branch 삭제 금지.
- 기존 C/D 브랜치는 이미 main 조상이며 보존, 신규 개발은 승인 platform 기반의 새 branch. E integration은 동일 platform 기준 및 A/B/C/D 승인 결과를 통합하는 별도 branch. C/D/E 신규 기능은 담당자가 수행.
- PR merge 후보 자체를 시험; 공통 변경은 관련 producer/consumer 및 공통 regression; 제품 main은 전체 회귀 + Owner 승인.
- 현재 실제 GitHub branch protected=false 및 rulesets=[] 조회. repo 설정 강제 보호는 관리자 권한 필요; 문서/CI만으로 branch 보호를 보장하지 않는다.

## 2. 커밋과 전파
RED → GREEN → 실제 증거 → REVIEW → 교육보고서/COMMIT → PROPAGATE. 공통 환경 수정은 기능 변경과 원자적 분리. 테스트 삭제/완화는 기존 회귀 목적 보존과 별도 검토. cherry-pick은 예외로 원본 SHA 기록. 승인된 platform의 변경을 개발 단위 시작/공통 변경 완료/인계/PR 전에 병합. 제품 release SHA와 개발 branch HEAD를 분리.

## 3. 기존 정책
IMMUTABLE_SHA_ISOLATED_BOOTSTRAP: exact 40 hex fetch, new workspace, source verification, no moving HEAD/merge, no automatic fallback, no destructive cleanup.
CHANGE_SCOPE_BASED_CI_GATE: data → B/data CI; AI → C/model CI; UI → D/UI + interface; navigation → Nav2/safety; shared contract → producer/consumer union; main → whole integration + Owner approval. Reuse prior PASS only with source/evidence/impact; unknown impact expand. No unnecessary physical reruns.
SHARED_PLATFORM_BASELINE, ATOMIC_FIX_PROPAGATION, REGRESSION_LEDGER_GATE: shared code only, append regression references, protect files at CI against trusted stable commit. Cloud software pass != native WSLg GPU pass. Visual inspection owner separate. No approval of GT.

## 4. 공통 모듈 범위
scripts/smartdish_platform/ canonical runtime/evidence/lifecycle/baseline; scripts/smartdish_platform_bootstrap.sh canonical pin checkout. Existing A13/AI OFF paths untouched at P0; future wrappers use common modules on their own reviewed branch. No blanket GUI software forcing: R03 explicitly requests software GUI client while preserving server GPU; old accepted A13 profile remains. B offline CPU, C training GPU explicit and isolate workload, D no Gazebo GUI dependency unless needed. Never change global environment or kill non-owned processes.

## 5. 브랜치 원장 (전환 기준)
main 63e1472; A prior HEAD 4c57d24 (Owner report cb62bcd); B 7048f7f; C old 271e401; D old fc8cca1; integration old 88ab0fa. A13 actual 6cb5b6b; R03 ST02 actual 194db14, UN01 actual 7c6e950. Preserve all refs/evidence. New platform pin only after common CI. No main merge or old branch delete. 
