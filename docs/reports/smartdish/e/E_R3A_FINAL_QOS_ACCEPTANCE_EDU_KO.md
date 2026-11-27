# E-R3a — GREEN 검증 완료 (실제 Gazebo PNG replay / CI double)
- 검증 SHA 2e3cd4c8658b96b5714d066dc0872f2961d5c308, [CI 45936375312](https://github.com/silverbjin/samsung_AXI/actions/runs/45936375312) success.
- [E L0/L1 45936375316](https://github.com/silverbjin/samsung_AXI/actions/runs/45936375316) success, 147 tests passed in 0.33s, ROS Jazzy L1 success.
- Artifact 15171001570 ZIP SHA256 97e2624ead5269703647de16fa4f67c951b4e498439fc732a67894d0bcac171a 직접 재계산 일치.
- capture source fe69077ff05358ace738b7a6bdf4128b43cbe3f4; 원본 PNG 1ee9c9a2b029adc5b7c581547fe1b42195b885ab2f5082835c91f7c1d6c57ab3; RGB bytes dae6f532d0b5e4717c8c174efe0bac19de9bfc9ddcbad9bb3707685e81acc451.
- RED1 UNKNOWN, RED2 cache ACK timeout, GREEN: C_TRAY_IMAGE_QOS=RELIABLE, 정확한 stamp 1/2/3초 cache ACK, 실제 predictor RGB hash match.
- missing UNKNOWN, fresh STABLE 0.75, duplicate 응답 0, already_used UNKNOWN, below_threshold UNKNOWN, stale UNKNOWN. 실제 test double DDS PASS, no Goal/cmd_vel. 모델 성능 또는 private v1 inference PASS 아님.
- 기존 A13 성공 영상 재사용, 사용자 WSL2 재실행 없음.
- 동일 artifact C log에서 시험 종료 SIGTERM 후 ExternalShutdownException과 중복 rclpy.shutdown RCLError가 발생함. 기능 PASS와 종료 결함 구분. 후속 R3b에서 clean shutdown을 명시적으로 검수한다.
- 핵심 학습: RELIABLE publisher만으로 BEST_EFFORT subscriber에 reliable delivery가 보장되지 않는다. Owner 구독 변경 후 실측 GREEN으로 해결 경계를 확인했다. 패킷 캡처 자체는 수행하지 않았다.
