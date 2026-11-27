# E-AION-04 — D Tkinter에서 STABLE/UNSTABLE 기준을 동적으로 변경

- Owner 요구: 기존 v1 모델 재학습 없이 테스트 도중 각 클래스 최소 confidence를 사용자 화면에서 변경.
- 화면 변경 범위: AI OFF(기본, 사용자 승인 UI)에서는 기존 화면을 변경하지 않음. Owner 전용 --owner-gazebo-integration 및 --ai-available true를 모두 선택할 때만 오른쪽 제어 패널에 “STABLE / UNSTABLE 판정 기준 설정” 버튼을 추가.
- 버튼 클릭: 별도 410×290 팝업이 C /smartdish_stability_inference 노드의 ROS Parameter 서비스를 조회, STABLE·UNSTABLE 현재 값을 표시. 입력 0.50~1.00, 0.05 Spinbox. 사용자 “적용” 클릭→rclpy AsyncParameterClient.set_parameters_atomically → C callback 검증→ACK 로그를 출력. 실패나 서비스 미접속일 때 기존 값 유지.
- 적용 타이밍: D 상태가 IDLE/COMPLETED/ERROR/CANCELED일 때만 허용; AI_CHECK/주행 중 변경 금지. C가 직접 ros2 param CLI로 변경하는 경로도 지원하지만 운영 절차상 IDLE에서만 사용.
- 변경은 C 모델 예측의 최소 신뢰도만 영향을 주며 실제 B 물리 GT 라벨, ImageNet 클래스 순서, 모델 weights, Nav2/CM를 수정하지 않음.
- C 프로세스 및 D UI가 서로 다른 ROS 2 프로세스로 통신하므로 동적 변경은 GUI 메모리만 바꿔서는 안 됨. ROS Parameter ACK를 확인할 때만 UI 표시값을 확정합니다.
- 기존 7개 /collection 토픽과 tray image 토픽 이름, 타입, QoS 불변.
- GUI 사용자의 실제 시각 검수는 Owner WSLg에서 별도 수행. L0/L1 CI는 파라미터 프로토콜 및 no-goal 검증까지만 성공 근거로 인정.
