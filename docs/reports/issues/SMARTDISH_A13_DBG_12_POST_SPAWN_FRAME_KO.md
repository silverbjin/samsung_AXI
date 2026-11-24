# A-13-DBG-12 — GUI EntityFactory 이후 첫 RGB 프레임 누락 (실제 RED→수정)

- [GUI L2-G Run #45336770303](https://github.com/silverbjin/samsung_AXI/actions/runs/45336770303), 소스 `765064bce87d328a785eabece94576c5752ba7a0`: L0 **30 PASS**, L1 **PASS**, L2-H **4/4 PASS**(ST01/02 HELD, UN01/02 FALL), GUI L2-G **FAIL**.
- 첫 오류: `A13_PRE_EVENT_GAZEBO_CAMERA_NO_IMAGE`, `sim_ns=709000000`, `ros_image_callbacks=2`, 마지막 Image stamp `400000000`, 최초 식기 생성 후 신규 Image 0회. 프로브 GZ 실제 이미지 **3,672,011 bytes** + SHA; Pose `dish_01,dish_02` 확인.
- 원인 경계: 최초 빈 트레이 센서 준비는 해결됐으며, **EntityFactory가 렌더링 장면을 변경한 직후의 첫 5Hz 이미지(.6s)**가 ROS 구독자까지 전달되지 않는 재현성. 브리지 내부 패킷 누락 여부는 현재 별도 GZ post-spawn frame 계측이 없어 아직 단정 금지.
- 최소 보정: **두 번째 post-spawn 5Hz 이미지 주기(.8s)까지** 실제 수신을 허용. 이전 제한은 stage 시작 뒤 .3초로 첫 후속 이미지 1개에만 의존해 유실되면 즉시 FAIL. 이 수정은 물리 관측 timeout을 늘리는 것이 아니며 주행 모델·시나리오 mass/inertia/friction은 그대로 보존.
- 안전 가드 불변: `A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED`, `abs(pose_at_capture-capture_stamp)` 및 original vs actual Pose 검증, `REVIEW_REQUIRED` 유지. UN 시나리오에서 두 번째 이미지 시점에 실제 식기가 이미 크게 이동했다면 **FAIL/HOLD**, ST/UN 이름으로 자동 승격 금지.
- 재검: 같은 SHA L0→L1→L2-H 4개→L2-G 2개의 cold start; 실증 전까지 GUI PASS 주장 금지.
