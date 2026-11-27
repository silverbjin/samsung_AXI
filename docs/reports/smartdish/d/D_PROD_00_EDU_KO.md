# D-PROD-00 — Seed 코드 감사 (2026-11-27)
## WHAT
Seed 57c5f57b471a92ae11adf1d2432d44aa8640d2ad, 계약 v1.1, profile OWNER_PRODUCT_RECOVERY. README, 00_COMMON_CONTRACT, 05_D_DEVELOPMENT_SPEC, 06_INTEGRATION_RUNBOOK 및 E-PROD-00 보고서를 해당 SHA에서 실제 읽었다. 독립 브랜치 생성 후 compare identical, ahead=0, behind=0.
## WHY / 최초 원인
- mission_manager.py: WAIT_LOADING tick이 즉시 AI_CHECK 또는 TO_RETURN, WAIT_UNLOADING이 즉시 TO_HOME. 물리 ACK가 없다. NEEDS_CONFIRMATION deadline=None, AI timeout이 직원 승인으로 우회 가능. Owner STABLE만 0.50 floor 및 모델 확인.
- manager_node.py: 기존 7 topic, Nav2 UUID/cancel/transfer/capture 없음. 기존 station mode graph readiness 및 steady timer 유지.
- ui_app.py: Owner threshold 0.50~1.00, atomic set ACK는 있으나 set 후 get 확인 부족. 기존 승인 action에 capture/stack identity 없음.
- product_admission.py: 제품 승인 두 pin None, Owner SHA 대조는 보호. 수정 금지.
## HOW
별도 profile 모듈/실행 경로 및 D 전용 tests/CI만 추가; 기존 legacy/AI OFF, station, C runtime, product admission, A/B/C/E 소유 코드 및 모델 권리 변경 금지. 기존 성과를 재사용하고 새 profile의 물리 결과를 위조하지 않는다.
## A/E 합의 대기 (HOLD)
실제 nav Goal UUID 수락 시 전달 경로, UUID 없는 timeout/ABORT 시 A 자체 취소/lockout, 초기 stack_id 및 READY manifest/receipt, capture 이전 staff_confirm capture_id 표현, LOAD receipt event_sim_ns와 frame stamp epoch. 공통 문서 임의 확장 금지. E가 승인 전까지 실제 DDS/L2 통합 금지; 독립 L0 fixture 개발 가능. C threshold set/get와 exact snapshot 연동은 C/E 승인 후.
## 검수
D-PROD-00 소스 감사 완료. 신규 CI/물리/Owner PASS 아님. RED run ID/artifact는 아직 없음. D-PROD-01~02 별도 검증 필요.
