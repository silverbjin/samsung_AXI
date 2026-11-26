# SmartDish B-QA03 — A15 신규 파일럿 실제 물리 데이터 품질 검수 실행 프롬프트

## 1. 역할과 목표
당신은 20년 경력의 ROS 2 Jazzy·Gazebo Harmonic·데이터 엔지니어링·컴퓨터 비전·ML 평가 전문가입니다. SmartDish_B_DATA_S7 대화에서 B-QA03을 실제 개발하십시오. A15의 Owner 원본 4장면을 읽기 전용으로 독립 검수하여 B-Q01~07 판정, 파일럿 품질, 다음 A16 확장 조건 및 C 인계 경계를 확정합니다. 분석만 하지 말고 B 코드·테스트·실제 원본 실행·CI·교육 보고서·커밋·Draft PR 갱신까지 수행하십시오.

## 2. 기준 및 입력
- repo silverbjin/samsung_AXI; B branch feat/smartdish-b-real-dataset, Draft PR #46, 기존 B QA02 HEAD c7cce70c534ec90433da2bd0c60f88672de9dc2a. A Draft #47, A15 실행 SHA 65f0fa6fbf140f8fd2553ce2d8fdf3f515918695; A 보고서 HEAD 11278fd4f484f5d89269059efc313b59f6a87f42 이후 Owner 판정 문서 참조. 최신 HEAD/CI/댓글을 먼저 read-only 확인, 중복 작업 금지.
- Platform b8ef3998973a5e33b67ddd5c5b63c3c89b837840; main 63e147289e307e0b9900ca365e9c4557c5921804; E integration/smartdish-platform-next, 6651055ea8d6d7d26375f9d288f75546c3d0d3fa. 변경 범위 기반 CI, immutable SHA isolated bootstrap, 공통 protected paths/ancestry, B CPU runtime을 준수.
- 첨부 필수: a15_pilot_evidence.tar.gz와 .sha256 (실제 Owner, SHA 828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05); 선택 첨부 SMARTDISH_A15_OWNER_RAW_REVIEW.json (SHA bd8d151b0cde1e89889fe50537ef656384eec762edafb76f7f09548c7ddcec4d), SMARTDISH_A15_OWNER_T0.png. Cloud ZIP 또는 artifact #15080076270, CI #45737733210은 비교 자료이며 Owner와 독립 표본으로 합산 금지.
- 읽을 repo 문서: A docs/reports/tasks/SMARTDISH_A15_CLOUD_OWNER_RELEASE_KO.md 및 docs/reports/acceptance/SMARTDISH_A15_OWNER_20261126_KO.md; B docs/reports/tasks/SMARTDISH_B_A14_QA02_OWNER_PHYSICS_KO.md, docs/handoff/SMARTDISH_B_A14_QA02_TO_A_C_KO.md, docs/quality/SMARTDISH_B_DACON_DATA_QUALITY_BASELINE_20261125_KO.md. B 기존 ai/scripts/audit_b_a14.py 및 tests/test_b_a14_audit.py 참고; 과거 고정 배치 검수기는 보존. 원본 없으면 실제 검수 HOLD, fixture로 대체 금지.

## 3. 이미 확인한 실제 Owner 상태
4/4 data PASS, 4/4 GUI PASS, all_owned_stopped=true, 서버 cleanup -11 네 장면 모두 FAIL, outer 15/15+inner64/64, source pin 일치, GT UNKNOWN_HOLD/human_approved=false, production_contact_health=HOLD. main/E 병합 HOLD(전체 회귀 #45737741379 cancelled, E 역할 승인 미완료). 물리 원본 재수집 없이 B 검수를 진행. 각 장면 raw SHA:
L15-01 99dd1d75880f6c9c14b9149da71f70c098b8234a1292c03cf353a162cb0edb77
L15-02 e22d124764777d1e0bf3c8024557cc00d134d9804425840d6eccddf1c224ec97
L15-03 fb1dc964c436fb725c1f3f78579dca150b950e1637e9b58014c78a09942e2f25
L15-04 8c3e1c5569685811f56f501a46b9be596c65707528e6471f3a0d83d2c4662425
t0 2.000s; 1.8–2.0s 안착; 외란 2.200–2.699s 500×1ms, world-Y 0.12 Nm 동일 명령; end 12.300s. Upper max displacement 0/0.8198921434956602/0/0.7811042800856003 m, cumulative path 0/1.0207173090787534/0/1.0323368975342706 m. Pose 164816, ECM refresh 164800, ROS callbacks 72951. STATIC_TRAY_COMMON_TORQUE_PILOT, 두 형상 계열 네 배치, top 640×480 단일 카메라. 동일 명령이지 측정 wrench나 실제 주행 가속도 아님. 이 수치는 참고 검수 결과이며 B는 raw에서 다시 검증하십시오.

## 4. 순차 개발 단위
### QA03-01 — Provenance/수신
새 schema registry에 정확한 Owner outer/inner hash, 실행 SHA와 verifier SHA, source class(OWNER/CI/FIXTURE), batch/trial/scene/stack/family/layout/environment ID 보존. TAR traversal/link/duplicate/overflow/unlisted file, external/internal hash, nested sidecar, manifest coverage, schema 및 linked SDF/PNG hash 검수. 원본을 수정/삭제/공개 업로드하지 않음. 실패 시 HOLD.
### QA03-02 — Input validity
PNG 실제 디코딩, RGB header/CameraInfo exact t0, measured ECM camera/tray/dish pose join, 200ms 정지 검수(2mm/.05rad는 기존 파일럿 기준, 제품 임계치 아님), footprint, actual support pair, conservative FOV와 occlusion/가림 사람 검토 분리. 두 클래스 모두 loaded domain인지 검증. 카메라 보정/투영 프레임 일관성, 단일 top vs DACON Front+Top 차이 명시. t0 이전 이미 낙하한 A14 UN-01은 학습 부적합 smoke로 보존.
### QA03-03 — Physical evidence
동일 1ms grid t0–end(4 entity 10301 samples/scene), quaternion, tray inverse transform, 위치/회전/유한차분 속도 및 누적 경로/최대 변위 독립 계산. 외란 command count/time/target/scope 검수, actual trigger 이후 관측 길이 및 반응 onset, 최종 지지/이탈 여부 확인. Contact refresh와 exact-stamp positive-pair 일치 통계 재계산; subset match와 전체 전달 구분. silent channel을 정상/NO_CONTACT로 자동 승격 금지. cleanup -11 관측 후 발생과 원본 유효성 구분; 원본 PASS 재사용.
### QA03-04 — GT 후보 검토 경계
데이터에서 observed held/ejected review finding은 기록 가능하나 scene name/offset/threshold만으로 label 생성 금지. 후보 안정성 규칙은 DACON 비교 및 비구속 연구 규칙으로 별도 기록, product threshold 아님. 사람 검토용 RGB·t0/trigger/trajectory/contact 근거 및 불확실성 worksheet 생성. 승인 없으면 rule_candidate UNKNOWN, ground_truth NOT_OPERATOR_APPROVED, approved_count=0, training_eligible=false. approval_ledger.jsonl 자동 생성 금지.
### QA03-05 — 다양성/shortcut/독립 그룹
두 형상 계열에 각각 중앙/편심, 네 layout ID 검증. Cloud와 Owner 동일 layout은 동일 group; 반복 환경은 독립 장면 증가가 아님. exact pixel/hash 및 near-duplicate, family/layout split leakage, 배경/식기 수/색/카메라/외란/파일명 등 shortcut 분석. 중앙·편심이 유일한 요인인 단순 pilot로 일반화 성능 주장 금지. DACON 통계 기준 재사용, 물리적 동등성 주장 금지. 4개로 train/valid/test 승인 분할 금지. A16 확장은 B의 품질 승인 이후 계획으로만 제안(60 독립 장면/6+ family는 기존 제안 수량, 확정 인수 기준 아님).
### QA03-06 — B-Q01~07와 C 계약
각 gate의 evidence, PASS/HOLD 및 최초 blocker 기록. Q01 provenance, Q02 input, Q03 physics, Q04 human GT, Q05 diversity, Q06 grouped split, Q07 C handoff. 이전 HOLD를 자동 PASS 승격하지 않음. 신규 A15 개선은 Q02/Q03 부분 근거로 기록하되 가림/전체 health 등 승인 범위 확인. C 입력은 향후 승인된 t0 RGB only; post-t0 Pose/velocity/Contact, trigger result, scene/seed/path/family/label 등 leakage 금지. 검토용 자료와 학습용 manifest 분리, approved train/dev/test release 금지. C dummy-only 독립 개발 허용.
### QA03-07 — 실제 개발, 테스트, CI, 출고
신규 ai/scripts/audit_b_a15.py, tests/test_b_a15_audit.py, scripts/smartdish_b_a15_qa_one_shot.sh, .github/workflows/smartdish-b-a15-qa.yml 및 필요한 schema를 B에 추가. 기존 A14 audit, B algorithm, A/C/D/E/platform/main 변경 금지. RED→GREEN→실제 Owner archive offline run→SHA 검증→review→보고서→commit/PR. 테스트: wrong pin/hash, path traversal, missing pose at t0/end, early motion, initial out-of-tray, absent support, frame/trigger drift, missing refresh, GT auto approval, duplicate family/group leakage, cleanup separate, same layout across environments. Fixture와 실제 Owner audit 명확히 구분. 실제 CI B data + A15 tests + common baseline/pin + 필요한 producer/consumer 계약. 기존 147개 B 테스트 회귀 유지. 전체 제품 CI는 main release 때 필수; 이번 독립 QA의 무관 CI 반복 금지. 새 SHA 실행기는 immutable exact checkout, CPU profile, read-only archive, exclusive output, fail-fast. 원본이나 결과의 SHA 위장 금지, 로그/실행 결과/CI Run ID 기록.
 
## 5. 결과물과 승인 경계
교육 보고서 docs/reports/tasks/SMARTDISH_B_A15_QA03_PILOT_QUALITY_KO.md, 인계 docs/handoff/SMARTDISH_B_A15_QA03_TO_A_C_KO.md, review-only JSON/worksheet, dataset card 갱신. 각 단위 독립 커밋, 실제 PR #46 댓글, 최신 B SHA와 CI/Artifact/원본/결과 해시 기록. A15 보존, B Q01~07 원장·Q02/Q03 개선과 미해결·A16 제안·C 데이터 이용 가능 여부 명시. 신규 WSL2 실험을 요구하지 말고 기존 파일로 독립적으로 가능한 작업 완료. Full product main merge는 E 승인과 full regression 및 별도 승인 이후; PR #46 Draft 유지. 교육용으로 분석과 원본 근거, 실패한 접근과 개선 이유를 남기십시오. 작업 완료/차단 사유를 사실대로 기록하십시오.
