# E-R4 DBG-04 — DDS 교차 토픽 관측 순서와 실제 첫 주행

- RED: [CI 45938362714](https://github.com/silverbjin/samsung_AXI/actions/runs/45938362714), source `b606fec4b41468b3f4815a11b479c388e4f9e159`, artifact 15171582233 SHA256 `587c0453baa18e5f187d1b2090560b56fbada7ca1ff52188cb20138bcfb20fbb` 직접 재계산 일치.
- DBG-03 실증: L0 overlay tests 3 PASS, 7 ROS packages built. CM와 BT ACTIVE, /cmd_vel publisher collision_monitor 단독, subscriber ros_gz_bridge 단독. docking_server는 /cmd_vel_nav에 존재, velocity_smoother → /cmd_vel_smoothed → CM 연결 확인.
- 실제 HOME→T03: action UUID e6c2c969a1444cdc9b79e70845c98b3a status 2→4, 5.178556 m odom displacement, 667 odom / 134 scan samples, AMCL error 0.189743 m, 16.419 s. D의 10초 대기 뒤 AI 요청(10.084 s), C log는 같은 capture ID STABLE fixture, D log NEEDS_CONFIRMATION. 
- 최초 실패: observer result.json에는 AI 요청 1건, NEEDS_CONFIRMATION 1건이 있으나 stability callback 0건인 시점에 즉시 assert. 서로 다른 DDS 토픽의 관측 순서는 보장되지 않는다. C와 D의 처리 실패나 모델 결함으로 해석하면 안 된다. 직원 승인 및 후속 Goal 0건, 전체 owned process exit 0.
- 수정: NEEDS_CONFIRMATION 이후 제한 5초 내 양쪽 DDS 증거 수신을 기다린 뒤 정확히 한 건, request/capture ID, fixture model version, confidence, live RGB SHA를 검증한다. 승인 전 Goal 0건 조건 및 CM gate 유지. 시간 제한이나 중복/잘못된 메시지 검증을 완화하지 않는다.
- GREEN: 새 SHA 실제 CI 결과 대기. 첫 구간/속도 경로 PASS 증거는 위 SHA에서만 유효. 전체 3-leg 및 Owner L3는 아직 HOLD.
