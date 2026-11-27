# Samsung AXI — Agent-first / WSL2 최종 인수·단일 실행 운영 정책

**시행:** 2026-11-27 · **적용:** 현재 C Dataset v1 및 기존 SmartDish A/B/C/D/E의 새 개발/검증 작업. 기존 증거·API·AI OFF·각 팀 코드와 Owner 인수 원장을 변경하지 않음.

## 1. 담당 주체별 작업 계약

| 업무 | 담당 | Owner 요청 기준 |
|---|---|---|
| GitHub 원격 조회, Branch/PR, 코드 작성·TDD, fixture-only CI, 로그/배포 실패 원인 분석 | **에이전트** | Owner 실행 불필요 |
| 공개 자료/라이선스 검토, 문서·교육 보고서/아카이브 원본 SHA 검증 | **에이전트** | Owner 실행 불필요 |
| ROS Jazzy/Gazebo 공개 CI의 L0/L1 및 재현 가능한 L2 | **에이전트** | Owner 실행 불필요 |
| 비공개 데이터 원본 읽기, private 모델/checkpoint 파일 직접 SHA, WSL2 고유 GUI/CPU/GPU/로봇 인수 | **WSL2 원샷** | 정확히 해당 검증이 불가피한 경우 **1개 원샷만** |
| 독립 Test 개봉/모델 추가 학습/AI ON/Contact HOLD 해제 | **별도 명시 승인 필요** | 이전 PASS/CLI/환경 진단으로 자동 승인 불가 |

## 2. 에이전트 작업 절차

1. 사용자 의도를 반영하여 기존 Main/Feature SHA, PASS/HOLD 원장, 제출 TAR+sidecar, Actions Run부터 재사용합니다.
2. 동일 레포의 독립 feature branch에서 최소 코드 수정 및 synthetic-only 검증을 수행합니다. 설치/환경 구성을 이유로 Owner를 반복 호출하지 않습니다.
3. CI 실패 시 원본 Run 로그와 최초 실패 지점만 분석해 최소 수정→같은 CI 경계 재검. 실패를 PASS로 꾸미거나 test disable하지 않습니다.
4. 각 단위 `docs/reports/tasks` 교육 보고, 필요시 `docs/reports/issues` 최초 실패 보고, 인수 원장과 `docs/DEVELOPMENT_LOG.md` 색인을 GitHub에 남깁니다.
5. CI 준비가 완성된 이후에도 실환경/GUI 검증이 필요한 항목만 WSL2 **최종 1회**를 요청합니다. 실행기는 자동 가상환경/의존성 검수·SHA 고정·fail-fast·증거 최소 TAR+SHA 포함. 사용자 시각 검수는 사용자가 수행하되 게이트에서 제외한다는 프로젝트 기존 결정을 준수합니다.
6. 장애 발생 시 Owner는 TAR와 sidecar만 제출합니다. Agent가 재현/진단하고 다음 1회 최소 작업 여부를 판단합니다. 무한 재시도 및 통계적 반복 인수 금지.

## 3. 현재 P0~P3-pretest 재사용 상태 (2026-11-27)

- P0 42/42 PASS (기존 C private Owner), P1 CPU ResNet18 V1 `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` / Python 가상환경 PASS.
- P2 freeze 학습 **1회 PASS**. 연구 모델 Validation 1/3(33.3%), 다수 클래스 2/3(66.7%) 대비 낮아 성능 HOLD. 재학습 금지. checkpoint SHA `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c`.
- **방금 제출한 P3 pretest** `20261127T010407Z-454600671d21.tar.gz`, SHA `5874707038d2d74e2f83d0d7370dbed6ed4baf32d12c6d8164aa8357e0f84148`: sidecar 일치, `454600671d21dec78155baddfb528c1505754841` clean, exit0, `P3_PRETEST_CHECKPOINT_SHA_PASS_PERFORMANCE_HOLD`. Test 평가 승인 false/개봉 false.
- **결론:** 이 시점 추가 WSL2 점검 불필요. P3 pretest 재실행 요청 금지. P3 독립 Test 평가와 P4 연구 모델 인수는 HOLD.

## 4. 한 번에 진단해야 하는 경우만 사용할 원샷

- **공통 진단 소스:** `ai/train/owner_environment_diagnostics.py`
- **일괄 드라이버:** `scripts/smartdish_c_v1_owner_diagnostics_once.sh`
- 자동 검사: immutable SHA/clean checkout, 전용 CPU Python venv 활성, torch 2.5.1+cpu·torchvision 0.20.1+cpu·Pillow 10.2.0, WSL2 확인, P0/P1/P2 보고서 SHA·계약·P1 plan 전체 SHA, private checkpoint SHA, 전용 Torch cache 파일 존재/크기, 디스크 여유, 기존 정책/미개봉 Test.
- **하지 않는 것:** pip/apt 설치, ROS/Gazebo/GUI, 원본 Dataset 42개 재해시, model forward/학습, Test 개봉, weights/checkpoint 바이트 외부 반출, P3 Test 승인, 자동 retry.
- 수행은 **새 WSL2 의존 장애가 발생했을 때만** Owner가 단 한 번. 산출물은 `~/smartdish_c_v1_owner_diagnostic_evidence/<run>.tar.gz` 및 대응 `.sha256`; 에이전트는 이를 검토한 뒤 코드 측 원인 해결.
- 향후 P3 전용 원샷에서 진단을 따로 수행하지 않도록 기존 `scripts/smartdish_c_v1_p3_pretest_once.sh`에도 동일 진단 모듈을 내장해 두되, **이미 PASS된 pretest를 다시 실행하지 않습니다**.

## 5. 상태 레이블

`C_P0_PASS / C_P1_TECH_PASS / C_P2_EXECUTION_PASS / C_P2_MODEL_PERFORMANCE_HOLD / C_P3_PRETEST_CHECKPOINT_PASS / C_P3_TEST_NOT_AUTHORIZED_NOT_OPENED / P4_NOT_ACCEPTED / E_AI_ON_HOLD / AI_OFF_PROTECTED / A19_NOT_AUTHORIZED / PRODUCTION_CONTACT_HOLD`

CI GREEN은 코드 수준 증거에만 해당합니다. 현장/모델/안전 결과를 승격시키지 않습니다.
