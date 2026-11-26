# A15 — 실제 WSL2 Owner 인수 원장 (2026-11-26 KST)

## 근거와 판정
- 실제 실행 SHA 65f0fa6fbf140f8fd2553ce2d8fdf3f515918695; 기존 보고서 HEAD 11278fd4f484f5d89269059efc313b59f6a87f42; stable b8ef3998973a5e33b67ddd5c5b63c3c89b837840.
- 제출 파일 a15_pilot_evidence.tar.gz, .sha256. Outer SHA256 828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05; sidecar 일치; outer 15/15, inner 64/64; 4 inner sidecar 일치. 원본을 로컬에서 직접 읽고 경로/중복/manifest coverage 검수, 배치/개별 verdict 일치, source/scene identity 및 scenario.sdf/PNG 연결 해시 확인. 원본은 GitHub에 공개하지 않음.
- 독립 검수 JSON SHA256 bd8d151b0cde1e89889fe50537ef656384eec762edafb76f7f09548c7ddcec4d.
- 실제 RGB 640x480 4장 시각 검토: 모두 초기 적재, 프레임 내부; 상단 카메라의 자연스러운 하단 식기 가림은 남음. exact t0 2.000s, CameraInfo skew 0, 실제 지지 pair 둘 다 t0에서 확인. 1.8~2.0s 안착 변위 0; t0~12.3s 1ms pose 4 entity × 10301 × 4 =164816, contact 4 topic ×10300×4=164800. ROS callback 72951, same stamp positive pair subset 통계 원본 재계산 일치; full delivery/engine registration 미입증. 독립 검사에서 상대 선변위/누적 거리, quaternion 유효성, 고정 tray, 시간격자, t0 지지 pair, 500개 동일 torque command 기록을 검수; 전체 회전 미분이나 실제 토크 측정은 아님.

| Scene | Inner SHA256 | files | upper max displacement m | upper path m | raw ROS callbacks |
|---|---|---:|---:|---:|---:|
|L15-01|99dd1d75880f6c9c14b9149da71f70c098b8234a1292c03cf353a162cb0edb77|16|0|0|15935|
|L15-02|e22d124764777d1e0bf3c8024557cc00d134d9804425840d6eccddf1c224ec97|16|0.8198921434956602|1.0207173090787534|21085|
|L15-03|fb1dc964c436fb725c1f3f78579dca150b950e1637e9b58014c78a09942e2f25|16|0|0|15554|
|L15-04|8c3e1c5569685811f56f501a46b9be596c65707528e6471f3a0d83d2c4662425|16|0.7811042800856003|1.0323368975342706|20377|

Cloud #45737733210 artifact #15080076270 same execution pin. Owner relative displacement and path agree to floating-point precision. Four distinct pixel hashes in Owner only; Cloud/Owner repeats of same four physical layouts must remain same groups. No eight independent samples.

## 종료 및 제품 승인
All 4 GUI and 8 bridges exit 0, all 4 server exit -11 on cleanup after data acquisition, all owned stopped true. Actual server inherited D3D12/NVIDIA; GUI llvmpipe/XCB/software. No evidence of native device-removal root fix; server log lacks definitive teardown stack trace. No cleanup PASS. Batch exit0 is data contract success, not clean shutdown. Preserve data and GUI PASS, cleanup FAIL, production contact health HOLD, GT UNKNOWN_HOLD, human_approved false. No repeated physical experiments. Separate targeted teardown diagnostic only if needed for release; no full data rerun.
- A15_DATA_OWNER=PASS 4/4; A15_GUI_OWNER=PASS 4/4; A15_CLEANUP_OWNER=FAIL 0/4; A15_PILOT_DATA_ACCEPTED_REVIEW_ONLY; PRODUCT_MAIN_MERGE=HOLD.
- Actual GitHub lookup: main 63e147289e307e0b9900ca365e9c4557c5921804, stable unchanged, E 6651055ea8d6d7d26375f9d288f75546c3d0d3fa, B c7cce70c534ec90433da2bd0c60f88672de9dc2a. A PR #47 Draft targets E. Execution-pin scoped CI SUCCESS, full MVP #45737741379 cancelled, E manifest HOLD_NO_APPROVED_ROLE_FEATURES. User's conditional main merge authorization is not satisfied by data PASS alone under agreed policy. No main or E feature merge. B-QA03 can proceed review-only without waiting for cleanup, main or C training approval. No auto labels/approval ledger, no future features.
