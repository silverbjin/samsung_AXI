# B-PROD-01 — 읽기 전용 물리 증거 QA 교육 보고서
## WHAT / WHY
A13 standalone world의 성공은 restaurant robot-mounted 제품 성공이 아니다. A/C/E의 독립 원본을 B가 대조해야 한다. 해시만 복사하면 실제 픽셀 동일성을 증명하지 못한다. 신규 교환 형식은 E 승인 전 fixture/candidate 전용이고 공통 ROS v2 계약은 변경하지 않는다.
## RED → GREEN
| Cycle | 정확한 SHA | CI run / 판정 | Artifact / GitHub digest |
|---|---|---|---|
| RED1 | 4f27c5e340e9203c48a67cf325a53febf66d593c | 45946858989 FAIL, job 140333429049, ModuleNotFoundError (검증기 없음) | 15175211265 / sha256:8e3011901b7ae8217acc8bf796a4011c55ebb6cdb26b61ca3d99e8aba8bf3d40 |
| GREEN1 | 39987c343cf02aa414b3e1d1b4f4bc94431e4271 | 45946918431 SUCCESS, job 140333615575, Ran 22 tests OK | 15174054847 / sha256:0a83b023428682f60fabed9c380dd42ed2e61e8633379a600581f93aa57b261b |
| RED2 | 0cf4e959c606fea431588fecf2daff8cb5747809 | 45946973818 FAIL, job 140333792661, 32 tests 31 failures, B_ARCHIVE_UNAPPROVED_MEMBER | 15175002853 / sha256:0a0c7259b3ec2b304a5bc0fd6e256b220f863696d42be183e778330491acd475 |
| GREEN2 | f39de0e23ad5231a62db9b479cd1efca10b30b5c | 45946986173 SUCCESS, job 140333829762, Ran 32 tests OK | 15174169784 / sha256:f9d5df7674761a343f798dcfe38e1fb17026f36884f4bed26c477852f1240aba |
RED2 최초 원인: 신규 원본 ROS Image bytes는 이전 허용 멤버 집합에 없다. 최소 수정: 정확히 ros_frame.bin 추가, stride 길이 검사 및 bgr8 RGB 변환, canonical bytes 재계산. archive path/size/hash 및 other gates 그대로. 첫 오류 확인 뒤 원본 로그의 해당 SHA/테스트 수 확인. Artifact digest는 GitHub 반환 메타데이터이며 ZIP 다운로드 재해싱을 주장하지 않는다.
## HOW
- TAR/sidecar SHA, exact allowlist, regular files only, duplicate/unsafe path, size bounds, JSON duplicate/nonfinite, manifest size/hash. No extract/write to source.
- receipt canonical bytes 및 request/stack/transfer/capture 일치; LOAD/UNLOAD entity count, ID conservation.
- Original ROS row bytes → strip stride / BGR→RGB → frame.rgb SHA → lossless RGB PNG decoded bytes → C canonical input bytes, exact stamp/frame/capture.
- sim load < frame <= infer < unload; separate monotonic causal/freshness. Tray inverse quaternion on observed world XYZ; relative drift and nonzero world movement; navigation 3 distinct UUIDs, ordered odom/scan samples, displacement.
- C raw status/confidence, effective thresholds, one invocation receipt; invalid source and duplicate IDs fail closed. Fixture only PASS; actual candidate valid structural checks still HOLD.
## REVIEW / limitations
No actual producer archive schema or actual A/E file bytes supplied. Current candidate manifest is deliberately narrow; E needs adapter or agreed archive export. Relative drift 0.05m, fixed bounds and transfer displacement 0.25m are illustrative fixture checks, not approved real geometry gates. Actual product must additionally bind initial table/return location, raw entity and camera mount/graph witnesses, receipt hash links, real /clock epoch, full pose/velocity/contact and nav stop dwell, AMCL, staff approval/wait 10/5s (steady), exact C invocation instrumentation and provenance. Current normalized JSON cannot authenticate physical reality; no claim of those L1/L2/L3 gates. Raw product data, model weights and Test4 not read or uploaded. Existing dataset contract CI 45946986185 SUCCESS; Restaurant 45946986121 cancelled, not PASS.
Workflow is push-filtered for exact B branch and PR-filtered for integration base; PR runs confirmed by connector; separate push-run enumeration is not available through this connector. Final PR checks and machine-readable receipt artifact in PR body. No merge.
