# A-PROD-04 DBG-02 — 실제 publisher graph 경계

- RED: SHA 6154c0e23ecbc07387803a3c6410cb727792b4af, Run 45955654421, original artifact 15178881241 (ZIP SHA256 488abf383152a7798dccf621dc6aa8b394d3b8f972761ade55dda3496eaf735b, TAR c6d32dcde998a6b17f34b4189d86551cd8d68c39645340e707abc8d467d6b807), candidate artifact 15178333860 (ZIP SHA256 01ec8b50045a2ec13fc03a96e93ed80f63985ca44b14831bdddcba5ac008cf1c).
- 두 실제 실행 모두 7 lifecycle ACTIVE, local/global live footprint 0.58m, first_error GRAPH_PUBLISHER_COUNT. 원본 launch log에는 ROS->GZ /cmd_vel bridge 및 docking_server activation이 존재한다. 정확한 중복 publisher 또는 discovery lag 여부는 이전 코드가 assertion 이후에 graph를 저장하는 결함 때문에 미확정이다.
- 수정: 실패 시 graph/publisher/subscriber 목록을 항상 보존하고 20초 내 3초 연속 정상 graph를 요구한다. /cmd_vel 단일 CM publisher, /cmd_vel_smoothed 단일 smoother, /clock 및 tray RGB 단일 publisher 조건은 그대로 유지한다. 명령 발행 없음.
- 검수: 새 CI 실행 결과로 실제 원인을 확정한다. GREEN 미확정. 이동 승인 없음.
