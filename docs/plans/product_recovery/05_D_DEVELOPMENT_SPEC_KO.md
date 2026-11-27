# D 담당 — 식기 회수 FSM·UI·예외 처리 명세
[공통 계약](00_COMMON_CONTRACT_KO.md) 필수. 브랜치 feat/smartdish-d-product-fsm: E seed. 기존 D #63/main AI OFF, product deny, E 직원 승인 경로 재사용.
## D-PROD-00 감사
src/smartdish_service/smartdish_service/{mission_manager.py,manager_node.py,ui_app.py,product_admission.py}, 기존 E #64의 Owner 모드와 직원 causal logging 확인. 현재 WAIT_LOADING 종료 즉시 AI_CHECK, WAIT_UNLOADING 종료 즉시 HOME, NEEDS_CONFIRMATION deadline=None. UI/코어/Manager/E의 0.50 floor가 다계층에 존재. 신규 profile에서만 변경.
## D-PROD-01 FSM
TO_TABLE→정지 검증→WAIT_LOADING 10s→LOADING(LOAD_ACK)→CAPTURING(capture ACK)→AI_CHECK(exact C result)→NEEDS_CONFIRMATION(60s)→TO_RETURN→정지 확인→WAIT_UNLOADING 5s→UNLOADING(UNLOAD_ACK)→TO_HOME→COMPLETED. AI OFF recovery profile는 capture/AI/staff 생략, legacy AI OFF unchanged. 
모든 active 상태 deadline, receipt-time validation, same ID, duplicate/late rejection. hard failure SAFE_HOLD/terminal, 승인 불가; valid STABLE/UNSTABLE/threshold UNKNOWN만 explicit staff APPROVE/ABORT. D가 A의 nav_result/transfer/capture를 위조하지 않는다. cancel request exact UUID→A ack terminal & stop; cancel 미확인 lockout. 직원 미승인 timeout 60s 후 Goal 0. 새 임무는 이전 엔티티 상태 및 정지 확인 후에만. 
## D-PROD-02 UI 및 설정
T03 map, 10/5 입력, AI ON 체크, 현재 load/capture/AI/unload/remaining/error reason, 실제 Top View selected frame(해시/ID) preview, raw status/confidence/threshold, 실제 직원 승인·중단 버튼, 창 크기 최소/스크롤 대응. 상태가 active일 때 임계값 잠금; idle에서 0.00~1.00 Owner profile Spinbox + validation + C atomic set/get ACK; 제품/legacy 기준 변경 금지. C actual snapshot과 D identity/freshness/threshold check 일치. 모든 valid 결과 직원 승인 전 TO_RETURN 0, hard fail에는 승인 disabled. UI status update와 실제 button click causal log. 시각 품질 Owner 검수, 기능 버튼 노출/활성은 CI Xvfb에서 검증.
## 검수·인계
L0 모든 FSM 상태와 timeout, wrong ID/stale/duplicate, no auto-goal, boundary threshold/AI OFF regression. L1 actual DDS A/C fixtures 및 D manager/UI Xvfb functional tests. L2 E에서 실제 A/C 응답 연결 및 fault injection; synthetic nav_result로 실주행 주장 금지. UI screenshots(개인정보 없음), test/report/CI/PR, error reason 표와 인터페이스 예시를 E에 인계. 
