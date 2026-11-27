# B 담당 — 제품 통합 데이터·물리 증거 QA 명세
[공통 계약](00_COMMON_CONTRACT_KO.md) 필수. 브랜치 feat/smartdish-b-product-evidence-qa: E seed에서 분기. 기존 B research/QA04~06 브랜치 및 PR #46은 별도 보존. 새 학습 데이터 수집/재학습이 E의 차단 조건이 아니다.
## B-PROD-00 감사
기존 A13 원본 hash/PNG/pose pipeline, DATASET_CARD, B usage, B research manifest를 읽는다. A13 independent world와 제품 robot-mounted world 구분. 기존 데이터를 이동하거나 변경하지 않는다.
## B-PROD-01 읽기 전용 evidence validator
후보 ai/scripts/verify_product_collection_evidence.py 및 tests/test_smartdish_b_product_evidence.py. TAR/sidecar SHA, 안전 archive path(절대경로/.. /symlink 금지), 내부 파일 SHA/size, source SHA/run_id/world_id, stack/entity lifecycle, transfer/capture/request IDs, exact frame hash/canonical RGB, t_load<t_frame<=t_infer(동일 sim stamp domain 및 monotonic causal receipt 분리), pose relative to tray, return receipt, 3 UUID/odom evidence를 교차 검증. 성공/실패 모두 machine-readable QA JSON, 최초 오류 및 scope 기록. 독립 station frame, stale frame, duplicate stack, 누락/조작 hash, label/rights 누락을 별도 reason으로 차단. B는 제어/Goal/AI 판정 발행 없음.
## B-PROD-02 데이터 거버넌스 및 인계
실행 증거와 학습 샘플은 별개. 기본 manifest에는 자동 등록 금지. 제품 영상은 INTEGRATION_EVIDENCE_ONLY, 기존 dataset/split 및 Test4 sealed 유지. 이후 별도 연구 승인 시 사람 STABLE/UNSTABLE 및 사용권 OWNED 확인, stack_id group split, 독립 물리 관측/출처로만 등록. S7 fixture, CI double 판정, scene name은 GT 아님. C 성능 33.3% 개선을 이 작업의 게이트로 삼지 않음.
## 검수
L0 정상/손상/중복/권리/시각 도메인 fixture; L1 실제 A/E artifact schema 검증(ROS 실행 불필요); L2 E actual artifact read-only 교차 QA. CI에서 생성된 비개인 synthetic data 또는 승인된 actual Gazebo artifacts만. private raw 및 checkpoint Git 공개 금지. 각 cycle 교육 MD와 QA JSON schema, 실제 Run/Artifact 및 검증 SHA를 E에 전달. A가 아직 미완료면 fixture QA만 PASS, actual evidence HOLD.
