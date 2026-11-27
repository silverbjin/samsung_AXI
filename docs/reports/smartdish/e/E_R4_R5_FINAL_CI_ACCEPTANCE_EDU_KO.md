# E-R4/R5 — CI 실제 3-leg 통합 검증 및 Owner 인계 판정 (2026-11-27)

## 최종 CI 판정
**E_R4_REAL_NAV2_STATION_CI_TEST_DOUBLE_PASS / READY_FOR_OWNER_STATION_L3**.
- 실행 코드 PIN `77a1ae256cf4a008c8cefc16a32c43bfc40c7d08`.
- [R4 CI 45939257386](https://github.com/silverbjin/samsung_AXI/actions/runs/45939257386), job 140309536789 SUCCESS, marker E_R4_EVIDENCE_VERIFIED_STATION_SCOPE_ONLY.
- Artifact [15172117729](https://github.com/silverbjin/samsung_AXI/actions/runs/45939257386/artifacts/15172117729), ZIP 103003 bytes, SHA256 `bcedecc2b009465c3e17abd761c77dd404c7dce30726ef23957859020da8b277` (직접 재계산 일치). result.json, DDS event 원본, action status UUID, actual predictor input, live frames, launch overlay receipt, 원본 프로세스 로그 확인.
- E L0/L1 [45939257362](https://github.com/silverbjin/samsung_AXI/actions/runs/45939257362) 및 [45939264718](https://github.com/silverbjin/samsung_AXI/actions/runs/45939264718) SUCCESS: L0 150 tests, L1 C/D/A build, actual installed module bytes, required model fail closed, DDS atomic parameter ACK. 
- 바로 이전 기능 SHA b23adebcfdd840e1b7da8bdcb4af4ac7339c98d0의 R3a [45938853703](https://github.com/silverbjin/samsung_AXI/actions/runs/45938853703), R3b [45938853624](https://github.com/silverbjin/samsung_AXI/actions/runs/45938853624), R3c [45938853617](https://github.com/silverbjin/samsung_AXI/actions/runs/45938853617) 전부 SUCCESS. 최종 코드 변경은 R4 probe 초기화 순서와 보고서에 한정. R3 생산 경로 재실행하지 않음.
- 동일 최종 SHA C 계약 45939264719, C17 AI OFF 45939264722, D AI ON 계약 45939264750, D smoke 45939264734, E A+D 45939264771 SUCCESS. 기존 Restaurant survey 45939264766은 보고 시점 L0 PASS / L1+L2 별도 실행 중. 기존 사용자 AI OFF L3를 재실행하지 않으며 main merge는 최종 Owner 및 필요한 PR checks 완료 전 금지.

## 실제 3-leg 증거
| leg | Nav2 terminal | odom 최대변위(m) | odom/scan | AMCL 목표 오차(m) | wall sec |
|---|---|---:|---:|---:|---:|
| HOME→T03 | SUCCEEDED | 5.124869 | 654/131 | 0.235120 | 22.852481 |
| T03→DISH_RETURN | SUCCEEDED | 6.383165 | 915/182 | 0.206484 | 32.553363 |
| DISH_RETURN→HOME | SUCCEEDED | 1.898264 | 568/113 | 0.238945 | 20.442017 |

Goal UUID (세 개 모두 status 2→4): 7c83f608ff4c468c8018f13d35c21fe1, 6fdd56893c37466b88959b97ef96adba, 06a399d3842743a28f5790aa77c598c5.
- 첫 결과→AI check 10.173526s, 두 번째 결과→세 번째 goal 5.186945s. D COMPLETED, 첫 Goal→COMPLETED 92.272878s.
- CI explicit TTY before A READY. 초기 threshold readback 0.65/0.90. request E-CI-STATION-NAV-01, capture E-CI-STATION-NAV-01-AI-f6fd4efa2c. 실제 RGB 640x480, stamp 22600000000, C input SHA256 `723b444744f73de88e6037df96246bca0474c44e7d116c422ff07aa3340091b1` 일치. fixture model resnet18-10df3d54b52e STABLE .75 (실제 모델 판정 아님). NEEDS_CONFIRMATION→1.003274s 후 CI explicit approve→0.005363s 후 TO_RETURN; D 로그 causal order verified. 승인 이전 후속 Goal 0.
- CM/BT ACTIVE, /cmd_vel sole publisher collision_monitor; bridge sole subscriber; docking_server → cmd_vel_nav → smoother → cmd_vel_smoothed → CM. start/end graph 검증. /clock publisher 1개, RGB-only independent station bridge. 종료 D/C/A/bridge/station/nav2 모두 rc0.
- source_sha, map SHA, R4 fixture provenance 확인. private_model_loaded=false, robot_mounted_tray_verified=false, ui_click_verified=false, test4_opened=false. **실제 모델·GUI·WSL2 통합 L3는 NOT_RUN.**

## RED→GREEN 교육용 원장
| 단계 | 최초 실패와 수정 | 근거 |
|---|---|---|
| R3a DBG-01 | UNKNOWN, 실제 cache ACK 도입 | E_R3A_DBG_01_DDS_CACHE_ACK_EDU_KO.md |
| R3a DBG-02 | ACK timeout, Owner RELIABLE image 구독 | E_R3A_DBG_02_OWNER_RELIABLE_QOS_EDU_KO.md |
| R3b | context 중복 shutdown 수정 | E_R3B_LIVE_TRAY_AND_SHUTDOWN_EDU_KO.md |
| R4 DBG-01 | lifecycle 발견과 ACTIVE 분리 | E_R4_DBG_01_LIFECYCLE_READINESS_EDU_KO.md |
| R4d DBG-01 | container git safe.directory 범위 고정 | E_R4D_DBG_01_CI_GIT_OWNERSHIP_EDU_KO.md |
| R4 DBG-02/03 | 직접 docking publisher 검출 및 E-only remap | E_R4_DBG_02_VELOCITY_GRAPH_EDU_KO.md, E_R4_DBG_03_DOCKING_CM_REMAP_EDU_KO.md |
| R4 DBG-04 | DDS 교차 토픽 수신 순서 수정 | E_R4_DBG_04_CROSS_TOPIC_ORDER_EDU_KO.md |
| R4 DBG-05 | parameter ACK timeout, startup readback 후 camera launch | E_R4_DBG_05_PARAMETER_ACK_STARTUP_EDU_KO.md |
| R5 | 실제 C input 및 D staff causal marker, UI/TTY manual gate, immutable runner | E_R5A_INFERENCE_AND_STAFF_PROVENANCE_EDU_KO.md, E_R5B_OWNER_STATION_RUNNER_EDU_KO.md |

학습 포인트: lifecycle 서비스가 보이는 것과 ACTIVE는 다르다. DDS 교차 토픽 관찰 순서와 node 내부 causal order는 다르다. 파라미터 적용과 ACK 전달은 다르다. 안전 graph gate를 완화하지 않고 launch 경로를 실제 수정한다. 정상 종료까지 검증하고 통과한 코드 PIN을 그대로 인계한다.

## 인계 경계
현재 main a64f54145762c88fd83ce237f4d494f4f0bb33f5 조상, E Draft PR #64만 사용. 기존 A/B/C 브랜치, S7 AI OFF L3, C20, Test4 및 default product deny 보존. 이 SHA의 R4는 두 Gazebo partition의 실제 Nav2+독립 tray station/CI-only 모델 double이다. 로봇 장착 물리 트레이 및 실제 C 모델 성능 승인 아님. 최종 Owner는 기존 private model과 수동 TTY/GUI 승인으로 같은 공통 witness를 실행한다. 자세한 실행 절차는 [최종 인계](../../../handoff/SMARTDISH_E_OWNER_STATION_FINAL_HANDOFF_20261127_KO.md). 
