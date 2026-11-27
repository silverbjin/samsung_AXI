# A-PROD-04-03 — 실제 단일 월드 NO_GOAL 검수 원장

판정: A_CLEARANCE_HOLD. 기능 검수 PIN 870262c8c8fc2c509a25d74d6f8ff28c0133db8e. 실제 경로 및 이동 승인 미완료.

| SHA / Run | 실제 결과 | Artifact |
|---|---|---|
| 4169af059ed2e32ebb3c4824e4adb25484255964 / 45955271845 | 후보 lifecycle CM 준비 전 조회 RED | 15178611635 |
| 6154c0e23ecbc07387803a3c6410cb727792b4af / 45955654421 | 원본/후보 7 lifecycle ACTIVE, 양쪽 footprint 580mm GREEN, publisher count RED | 원본 15178881241 / 후보 15178333860 |
| 15c299d69e6791051c9b08cedc11eeb3488b8b7e / 45956255819 | 후보 실제 graph 194/194 snapshots 19.945s에서 /cmd_vel에 CM + docking_server; 다른 sensor publisher 조건 정상. RED 원인 확정. 원본 job은 마지막 조회 시 build 진행 중 | 15178264825 |
| 870262c8c8fc2c509a25d74d6f8ff28c0133db8e / 45956739176 | docking remap 전용 launch overlay 구현, CI 실제 재검수 시작. 완료 결과 미확인 | 미확인 |

실제 원본/후보 45955654421: odom 467/484, scan 94/96, clock 4096 samples, AMCL 수신, map 수신, odom 최대 변화 9.46e-15m, 비영점 속도 명령 0건, NavigateToPose 0건. 두 launch exit 0, forced=false, Gazebo pause 및 clock quiescence 확인. Child 별 exit 0까지 주장하지 않음. Graph 실패로 실제 ComputePathToPose 0건. 
ZIP SHA256: 원본 488abf383152a7798dccf621dc6aa8b394d3b8f972761ade55dda3496eaf735b / 후보 01ec8b50045a2ec13fc03a96e93ed80f63985ca44b14831bdddcba5ac008cf1c.
TAR SHA256: 원본 c6d32dcde998a6b17f34b4189d86551cd8d68c39645340e707abc8d467d6b807 / 후보 9a2a511dac53184614452bcf799ab55b46d714246a957b7c29a6276596ed55bf. 각각 내부 17개 해시 일치.
Graph 증거 15178264825 ZIP af5c73d0e784ec574d460c9c7d765e52abb66cd4b5d4fa46ee9d949a18e3b382 / TAR 28158428d5e01d2f087ada8e7938c09231237e159ecabb5868724bc6bcf33f5f / 내부 17개 해시 일치.

수정 후 검수 항목: installed launch 원본/복사본/hash/diff, 3초 연속 CM 단일 /cmd_vel, smoother 단일 /cmd_vel_smoothed, docking→cmd_vel_nav 및 실제 subscriber, TF/AMCL/Gazebo pose 등록, 원본 vs 후보 actual map, 실제 ComputePathToPose 3구간 UUID/result와 all-yaw swept footprint, global costmap raw, actual RGB/initial entity, stationary, clean shutdown. 실패 시 원인과 TAR 보존. 단일 위치 등록은 이동 전역 정확도를 보장하지 않으므로 motion_authorized=false 유지.
