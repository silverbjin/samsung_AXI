# A-PROD-DBG-01 — 빈 식탁 검수와 Gazebo 종료 경계
## RED / 실제 증거
- Run 45947546973 / SHA 2f4a32510d0f952d0a9bb3be5099e1ad255cb079 / artifact 15175567139 (SHA256 a7ab9a6cf83bd7be096b55e6cbdce54604f45e9f543f84def01bcc5cda32e2d2): stacked 실제 LOAD→fresh RGB→제거 성공, entity IDs 134/139/144, LOAD sim 7396000000ns, capture 7400000000ns, cleanup exit 0. LOAD 9.79s, UNLOAD 7.20s: 5s 제안 deadline 미충족. 전체 job FAIL (empty).
- Run 45947800643 / SHA 8e2baff814c9f0b8511430f1d34460d2e1880a9c / artifact 15175571810 (SHA256 9002493767e44e290600d0e95b9f06490da46bc559ff88d21675b72df1e67251): 원본 ZIP 다운로드/해시 일치 확인. stacked LOAD/capture/remove 재관측, empty fixture count=0, table/tray 각 3 RGB, table diversity=6 (이전 8 기준에 미달), clock 447 distinct, publisher 1 each, EMPTY_TABLE no mutation. 최초 실패 FORCED_CLEANUP: empty gazebo exit -9, bridge/spawn exit 0. Gazebo 로그에는 종료 signal handler 수신 기록 없음. 종료 순서 경쟁 가능성은 가설, upstream 결함 단정 금지.
- Run 45947861186 / SHA 15f6bfa8b2d85d939193ba4ddb5a9302bb89cb57: L0 21 passed, L2 skipped, artifact 15176075764. 기존 A L0/L1 45947861178 및 E fixture 45947861222, Restaurant 45947861273 success; 신규 제품 DDS PASS로 승격 금지.
## 최소 변경 / 검수
3df444a5f82c29ee8e0b4a236c87d2e9da07afce: 실제 world/control pause 요청, bridge/subscriber를 살아 있는 상태로 유지하여 렌더 업데이트 정지 경계 기록, Gazebo 먼저 SIGINT, 그 뒤 bridge 정리. 모든 exit code 0 및 forced=false 필요. 성공 증거를 이전 SHA와 구분. 수정 후 실제 CI 결과 아직 미확인.
## 교육 포인트
프로세스 종료는 신호 발송이 아니라 exit code/owned process 증거로 검수한다. empty frame 픽셀 다양성은 의미적 실패와 구별한다. 실제 물리 처리 성공도 deadline/이동/UUID/제품 ACK 검수와 구별한다. 이 보고서는 실패 사이클의 원본 근거 보존이며 제품 승인 아님.
