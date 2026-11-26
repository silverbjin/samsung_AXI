# B-QA03 DBG-01 — GitHub Actions shallow checkout Platform SHA 검증 실패 및 수정

## 재현 (직접 GitHub CI)
- 첫 신규 A15 QA03 scoped GitHub CI Run [#45742930426](https://github.com/silverbjin/samsung_AXI/actions/runs/45742930426), SHA `d7daf3c7bdfa8ce0e91fa4d1418e5fcd5aa94e27`, **FAIL**.
- 실패 Step: `Preflight script and immutable Platform contract`.
- 최초 오류: `fatal: ambiguous argument 'b8ef3998973a5e33b67ddd5c5b63c3c89b837840^{commit}'` (GitHub checkout 기본 fetch-depth=1).
- Source Python `scripts/smartdish_platform/baseline.py`는 신뢰된 platform baseline이 정확한 40hex로 Git 이력에 존재하며 ancestor이고 보호 경로가 변하지 않았음을 검증하는 올바른 정책. **보호 정책을 삭제/우회/완화하지 않음**.
- 같은 SHA의 기존 B 데이터 계약 CI [#45742930276](https://github.com/silverbjin/samsung_AXI/actions/runs/45742930276)는 **172/172 PASS**(기존 147 + 신규25), `MOCK_ONLY_GUARD_PASS`; 이번 A15 전용 workflow checkout 문제와 분리.

## 원인 및 최소 수정
- 현 workflow `.github/workflows/smartdish-b-a15-qa.yml`의 GitHub `actions/checkout@v4` 기본 얕은 이력에는 SHA `b8ef399...` 커밋이 없어 `git rev-parse SHA^{commit}`이 실패.
- 다른 common/baseline 정책 소스를 변경하지 않고 **A15 전용 checkout에 `fetch-depth: 0` 설정**.
- CI에서 같은 기준 `python scripts/smartdish_platform/baseline.py --baseline b8ef...`을 다시 실행. `git -c safe.directory` 또는 globally trusted directory 임시 우회 없이 검수.
- 실패 시 B Owner 원본 PASS 및 A15 물리 재실험으로 오해하지 않고 scoped CI RED→GREEN만 검증.
- Owner 원본 부재·승인0·Contact health HOLD·제품 출고 HOLD 유지.

## 완료 조건
- 새로운 SHA의 A15 전용 fixture CI PASS 및 Platform pin ancestry PASS.
- B 전체 147+25 기존/신규 계약 PASS. 결과는 같은 SHA GitHub Run ID로 확인.
- 검토/디버깅 문서·PR #46(여전히 Draft)에 기록.
