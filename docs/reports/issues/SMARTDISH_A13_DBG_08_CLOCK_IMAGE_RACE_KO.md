# A-13-DBG-08 — ST-02 RGB 시뮬레이션 타임스탬프와 /clock 경쟁 조건

- 원본 실제 L2: [Actions #45310092985](https://github.com/silverbjin/samsung_AXI/actions/runs/45310092985), SHA `6aef300a6bc4464e2d3f2c55f74d5c799c0f6fca`.
- **실제 완료된 부분**: ST-01 RGB/PNG/10s 물리 `HELD_OBSERVED`; ST-02 역시 RGB/PNG/10s `HELD_OBSERVED`. ST-02 `SMARTDISH_A_TRAY_PHYSICS_OBSERVED` 직후 `A13_IMAGE_AFTER_PHYSICS_OBSERVATION` 차단. UN-01/02는 이전 실패 후 미실행. 전체 L2 FAIL.
- 근본 원인: 초기 카메라 준비 loop 내부는 `clock >= captured image.stamp`를 검사하지만 **loop 바깥 break**는 `image present`+ `dish poses`만 검사해 클록이 아직 image stamp보다 뒤에 있어도 탈출했습니다. ROS Camera/TF/Clock은 별도 subscriber여서 수신 순서가 완전히 동일하다는 보장이 없습니다.
- 수정: 외부 break 조건에도 `state['sim_ns'] >= image timestamp`를 명시하여 t1 이미지 `<=` t2 관측 시작을 구조적으로 보장. 누락/역전 시 기존 `verify_timing()` FAIL-CLOSED는 그대로 유지하며 임계값을 느슨하게 변경하거나 결과를 PASS로 승격하지 않습니다.
- 회귀 범위: A-13 L0 정적 준비 조건, ROS Jazzy L1, 네 시나리오 실제 Gazebo L2. 기존 E AI OFF/Nav2/CM은 수정·재인수 없음.
- 교육 포인트: 독립 비동기 토픽의 **논리 조건을 내측/외측 종료 분기에 모두 일치**시키고, 나중의 강한 증거 검증이 실제로 오류를 잡아낸 것이므로 검증기를 삭제하지 않습니다.
