# E-PROD-01 — 통합 착수 감사 및 승인 계약 (2026-11-27)

## 판정
G0_ROLE_ANCESTRY_AND_OWNERSHIP_PASS / E_PROD_01_CONTRACT_APPROVED_IMPLEMENTATION_HOLD. 통합 승인, 실제 L2/L3는 별개. E #66 및 역할 PR은 Draft. main 변경 금지.
## 실제 Git 읽기 전용 감사
공통 Seed 57c5f57b471a92ae11adf1d2432d44aa8640d2ad, E #66 HEAD 동일, main 1d7bbf244143aeb8a9b6c71f9c2605d53ac38b4b.
모든 역할 compare merge-base 정확히 Seed, behind=0. A 36 ahead/32 files (A package/setup/scripts/tests/workflows/reports), C 16/11 (C package/tests/workflow/reports), D 24/13 (D package/tests/workflow/reports), B 9/6 (B QA/tests/workflow/reports). 다른 역할 및 legacy 원본 변경 없음.
| 역할/PR | 인계 HEAD | 검증 기능 PIN | CI Run / Artifact / 범위 |
|---|---|---|---|
| A #67 | 90c61742cd1a35a7a63a6c137f38c352fe2b7eaf | 0c243fa59377632ba1265867c8dd2143a5b4d93e | 45949631220/15176372495 L0 31 PASS; 45949408207/15176391936 actual DDS fixture L1; 45949631109/15175473677 regression PASS; 45949123061/15175289984 stationary L2 PASS @218ce2bf70cdd21cc4ed47cf4bb70715b6e36684; 45948745467/15175876889 cleanup PASS |
| C #69 | d7ac84e4b80a3231b9720cfa92833e7ee304acdd | fcb766c720039c85ec75ef88c06b6a7574b81f34 | 45947310986/15175441067,15174738960 L0/L1 success CI_DOUBLE_PRODUCT_DDS |
| D #70 | 213597dfc507b8f86ae8a833d0d0f45ef99dfba1 | f3194402d4120ec3ca07691c5ffa2dc8bb0d7cdd | 45947646581 L0 and L1 completed success, 15175916107 and 15175362721; no Nav2/Gazebo/model |
| B #68 | b0b217292ebf7c8ec7847c36f583ce69a9adb022 | 3e56b8ae64e3a33a64a0cdcdfa37f6057789f105 | 45947001135/15175385628 L0 fixture success; final report HEAD 45947084265/15175575370 success |
A legacy E A+D 45949631142 success; A nav 45949407809 success; Restaurant 45949631215 L0 success, L1/L2 and map job cancelled. Required regression not complete, no merge authorization yet.
Artifact SHA256 from live GitHub metadata (not independently rehashed in E):
- A 15176372495 b4eda99585fe7b12c5eb25e50164184f9059668a58847632a62614be01a46792; 15176391936 500bcd53a1ec57ba1036c99e4bfecd3354840d57bc3744a719f53a2684cfb3c9; 15175473677 7551480108c8b3b40f7e8683505cb6192b25e8df50ed097b98ffedd6404e4196; 15175289984 7bcd2f61bab6d34d5eb169db65a6c56cd1677a12bef950797de02d50c4b5e1d9; 15175876889 815c08b389533906eb14015b505b20693d3ad75bd51af5b6311a4b533a41cb06.
- C 15175441067 97b880f00c4c6d942631bb73bca6e02bfabfc67238a3c648824df0c61cb17db6; 15174738960 a70d348431eca9c50a3e2183ee810a1b4fce2ea98df1b01c077f63208e6b7112.
- D 15175916107 d0af304e74077562403c565cc3637f9bf7bfbc41d200cc9082c0e21248c5d3ef; 15175362721 f6c32a5997fa2d4ba22348bbfe78f6220efa6b0fea67faf389288c85f640841a.
- B 15175385628 1e802abbbb347f4c629325c1056056af6c092661368d65ad962894db1aeca16f; 15175575370 3a68e5ddc555e54baf3c7ceb045be91a8f581e2a24c48fd23c7c027d1e3edd88.
## WHAT/WHY
A actual stationary load/unload 9.79/7.20, 8.43/6.13, 8.374/7.097 s; 기존 A/D 5s 불충족. 실제 통합 실패를 실행했다고 주장하지 않는다. code inspection: D CANCELING 5s vs A 10s cancel and 3s stop; D on_nav_result accepts UUID without accepted hook; UI/FSM rejects all pre-capture ABORT; A terminal status across topics can arrive before goal. E accepts Owner-only amendment below. 
## HOW / approved contract addendum v1.1.1 (wire schema 2/profile unchanged)
1. Product transfer LOAD=20s, UNLOAD=20s steady deadline; 10/5s wait separate, late ACK invalid, no retry. A local deadline starts receipt dispatch, D starts request; D earlier deadline authoritative; A must observe SAFE_HOLD and halt further physical steps; no late ACK promotion. Actual integrated proof mandatory, no performance gate relaxation.
2. Actual Nav2 UUID only from accepted handle via in-process hook. D requires bound exact UUID before accepting normal terminal result; if D rejects late accepted hook, A cancels exact handle and drains terminal/stop. D CANCELING=15s (10s A cancellation budget + 3s stop + 2s transport margin), unresolved motion remains SAFE_HOLD_UNVERIFIED. Pre-UUID ABORT/timeout sends correlated status; A latches terminal per request even if status precedes goal. No fabricated UUID/no global cancel. Terminal failure with unverified stop remains unverified; no next goal.
3. A arm_verified after real entity observation (3 table dishes / 0 tray, or empty negative scenario), fresh clock/odom/scan/AMCL/robot-mounted RGB, CM actual ACTIVE+sole publisher. E validates actual READY receipt bytes/hash/stack_id/run/source, then D arm_verified. Empty startup allowed only to exercise negative scenario. No generated manifest-only READY.
4. Staff ABORT: request_id+stack_id exact, capture_id JSON null only when FSM capture_id is None (including AI OFF); explicit field required. APPROVE_CONTINUE requires nonempty exact capture_id, valid inference and NEEDS_CONFIRMATION. Pending pre-dispatch threshold query ABORT must not release goal; UI sends abort for active request including pending. Fail-closed on mismatches. Transfer FAILED permits unknown location, [] ids and null counts/stamp; never interpreted as ACK. Actual counts/IDs only.
5. C actual set/get snapshot prior to mission, UI lock, C mission lock; D verifies result snapshot and model identity, independent deadline, no model override. E must verify model_available, reuse existing C CPU venv and dual import/receipt checks; no reinstall; CI double only. Product gate still DENIED; Test4 sealed.
6. E composition: A owns step thread, D owns separate executor and deadline. Route accepted UUID to D owning thread with bounded handshake (no concurrent spin or unsynchronized FSM writes). E cancellation teardown must retain A action polling until quiescent or record unverified. No new ROS topic required. Review actual transport ordering and failures in L1.
## REVIEW and next gates
A and D role fixes + tests required before merge. C/B scope limited approvals pending latest final checks and actual interfaces. A→C→D→B sequentially, E merge base sync and relevant CI. L2 moving tray/costmap/CM clearance, exact physical receipts and C/B actual evidence pending. Historical R1/R2, R4 station, AI OFF protected; no WSL2 run or main merge.
No new test execution at this documentation commit. Next: role contract implementation, concentrated L0/L1 then E single-world. This report will be updated after actual results.
