# E-AION-05 — 모델 없는 실제 Jazzy DDS 동적 판정 기준 검수

- 목적: C v1 checkpoint 원본 없이도 **실제** ROS Jazzy C 추론 노드 + D Manager를 띄워 ROS 2 parameter ACK, owner profile D admission, A 미연결 시 no-goal을 검수.
- 입출력: C /smartdish_stability_inference 파라미터 stable_confidence_min/unstable_confidence_min, D 기존 /collection/request/status/nav_goal 토픽. 기존 7개 토픽/영상 토픽 계약 변경 없음.
- 정상 실험: 0.80/0.80 조회 → 0.65/0.90 원자적 변경 → 실제 C 값 확인. 부정 시험: 0.49+0.80 입력은 거부, 양쪽 기존 값 보존.
- D가 Owner 허가 프로파일로 시작해도 A Adapter의 nav_goal Subscriber가 없으므로 ADAPTER_NOT_READY_NO_GOAL과 논리 Goal 0건을 관찰해야 정상. 진짜 Nav2/Gazebo/Collision Monitor를 띄우지 않음.
- C 모델 파일이 없으므로 이미지/추론 실증 불가. 이 CI에서 STABLE/UNSTABLE 실제 예측값을 만들지 않음. C20 재학습/Test 개봉/기존 E AI OFF L3 재실행 없음.
- 최종 CI URL과 수정 SHA는 실제 Actions 결과 확인 후 교육용 보고서/PR에서 연결. CI PASS도 Owner L3 실제 AI ON을 의미하지 않음.
