# C14 — Owner P3-pretest 인수 및 Agent-first WSL2 최소 실행 통합 (2026-11-27)

## 목표 및 최초 증거

사용자가 **환경 점검을 반복 요구하지 말고 에이전트가 최대한 개발을 진행하라**는 운영 정책을 명시했습니다. 방금 제출한 P3 pretest TAR `20261127T010407Z-454600671d21.tar.gz`는 Agent에서 직접 SHA256 `5874707038d2d74e2f83d0d7370dbed6ed4baf32d12c6d8164aa8357e0f84148` 산출하여 sidecar와 일치. 정상 TAR 6개 파일(checkout/execution/pretest report/stdout/stderr), pretest report SHA `be765acc2d83f4bf52c665a3bcd916f42271a490dae2c9307830c6a716e77abb`, exit0, clean, checkpoint SHA `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c` 일치 기록.

Owner 제출 `P3_PRETEST_CHECKPOINT_SHA_PASS_PERFORMANCE_HOLD`는 **원본 checkpoint read-only SHA+metadata 확인**이며 Test를 열지 않음. Test 승인/열림 false, model accepted false, 성능 HOLD. 3 epoch P2 단 한 번 완료, Validation1/3 vs STABLE majority2/3.

## 구현

1. `AGENTS.md`, `docs/REPORTING_POLICY.md`, `docs/policies/SMARTDISH_AGENT_FIRST_WSL2_FINAL_ONLY_POLICY_KO.md`에 **Agent-first** 우선순위/역할/근거 경계를 명시.
2. `ai/train/owner_environment_diagnostics.py`: 비공개 P0/P1/P2 영수증·P1 계획·checkpoint SHA, 고립 venv/CPU package·WSL2·전용 weight cache 존재, Test 미개봉/AI OFF 정책을 **읽기 전용 한 번** 검사. Torch pretrained 전체 재해시/42개 private 이미지 재검은 재사용하는 기존 PASS에 맡김.
3. `scripts/smartdish_c_v1_owner_diagnostics_once.sh`: WSL2 필요시 **하나의 immutable PIN command**. venv 자동 활성, isolated temp checkout, fail-fast, TAR+SHA sidecar 자동 생성; checkpoint·이미지·approval·weights 바이트 외부 제출 없음.
4. 향후 `scripts/smartdish_c_v1_p3_pretest_once.sh` 호출 시 환경진단을 내부에 통합함. **지금 이미 P3 pretest PASS라서 재실행은 요구하지 않음.**
5. `tests/test_c_owner_environment_diagnostics.py`, 기존 C Dataset v1 fixture-only CI에 0개 실물 파일로 drift/비허가 경계 테스트.

## 결과/인수 경계

- CI: 공개 fixture-only Python tests/compileall/Bash syntax 필요, **WSL2 추가 실행 NOT_REQUESTED**.
- WSL2 제출 원본 P3 pretest: SHA 검증 및 clean/exit0 **PASS**.
- 모델 성능 HOLD, P3 실제 Test4 개봉/평가 미승인, P4 모델 출고 HOLD.
- A19 NOT_AUTHORIZED, Contact HOLD, Data Freeze A18 마지막, AI OFF PROTECTED 및 main/PR 미병합을 유지.

### 교육적 결정 이유

비공개 Owner 환경은 CI에서 재현할 수 없지만, 이미 성공한 파일의 SHA·실행 기록을 재사용하면 사용자의 WSL2 반복 시간을 줄일 수 있습니다. 단일 런처에 환경 진단과 필요한 검수·자동 아카이브를 묶으면 여러 터미널의 수동 조작 오류를 없애고, 새로운 실패의 최초 원인만 확보할 수 있습니다. 실환경이 없을 때 CI만으로 Model PASS를 주장하지 않는 것이 핵심입니다.
