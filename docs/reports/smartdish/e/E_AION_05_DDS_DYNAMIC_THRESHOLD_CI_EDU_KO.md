# E-AION-05 — 모델 없는 실제 Jazzy DDS 동적 판정 기준 검수

- 목적: C v1 checkpoint 원본 없이도 **실제** ROS Jazzy C 추론 노드 + D Manager를 띄워 ROS 2 parameter ACK, owner profile D admission, A 미연결 시 no-goal을 검수.
- 입출력: C /smartdish_stability_inference 파라미터 stable_confidence_min/unstable_confidence_min, D 기존 /collection/request/status/nav_goal 토픽. 기존 7개 토픽/영상 토픽 계약 변경 없음.
- 정상 실험: 0.80/0.80 조회 → 0.65/0.90 원자적 변경 → 실제 C 값 확인. 부정 시험: 0.49+0.80 입력은 거부, 양쪽 기존 값 보존.
- D가 Owner 허가 프로파일로 시작해도 A Adapter의 nav_goal Subscriber가 없으므로 ADAPTER_NOT_READY_NO_GOAL과 논리 Goal 0건을 관찰해야 정상. 진짜 Nav2/Gazebo/Collision Monitor를 띄우지 않음.
- C 모델 파일이 없으므로 이미지/추론 실증 불가. 이 CI에서 STABLE/UNSTABLE 실제 예측값을 만들지 않음. C20 재학습/Test 개봉/기존 E AI OFF L3 재실행 없음.
- 최종 CI URL과 수정 SHA는 실제 Actions 결과 확인 후 교육용 보고서/PR에서 연결. CI PASS도 Owner L3 실제 AI ON을 의미하지 않음.

## 실제 L0/L1 결산

- [최종 검증 #45929414512](https://github.com/silverbjin/samsung_AXI/actions/runs/45929414512) — **L0 131 PASS / L1 3 packages + 실제 ROS 2 DDS PASS**.
- C 파라미터 0.80/0.80 → 0.65/0.90 변경 및 실제 읽기 확인, 잘못된 0.49 입력 원자적 거부, D Owner AI ON 요청에서 A 미연결 차단 + Goal 0건.
- 신규 E 런치 파일 `smartdish_e_owner_aion.launch.py`의 `ros2 launch --show-args`로 실행 인자 존재 확인. 실제 Tk GUI 표시/실제 C 모델 로드/주행은 NOT_RUN.
- 첫 L0 RED [#45928798798](https://github.com/silverbjin/samsung_AXI/actions/runs/45928798798)은 C 이미지 캐시 초기화 19 FAIL → [E-DBG-001](E_DBG_001_INFERENCE_CACHE_INITIALIZATION_EDU_KO.md), 첫 DDS L1 RED [#45928898785](https://github.com/silverbjin/samsung_AXI/actions/runs/45928898785)은 A adapter 대신 관측자 구독을 준비로 오인 → [E-DBG-002](E_DBG_002_DDS_ADAPTER_SUBSCRIBER_20261127_KO.md)로 각각 원본/원인/교정 기록.
- 최종 표기 `E_OWNER_AION_L0_L1_PASS_NO_NAV2` (실제 가중치/WSL2 현장 미검증).
