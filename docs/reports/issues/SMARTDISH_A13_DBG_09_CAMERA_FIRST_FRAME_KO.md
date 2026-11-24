# A-13-DBG-09 — Gazebo 카메라 첫 프레임 플래키 현상: 전송 계층 분리와 Wall-clock 준비 장벽

- 이전 첫 오류: [L2 #45311084711](https://github.com/silverbjin/samsung_AXI/actions/runs/45311084711), 실제 SHA `d5784374a4a807ecc97e9a5d3d0c301ac4094ed1`: L0 **25 PASS**, L1 **PASS**, L2 ST-01 시작 후 `A13_PRE_EVENT_GAZEBO_CAMERA_NO_IMAGE sim_ns=305000000 GZ_IMAGE_TOPIC_ADVERTISED=True poses=['dish_01','dish_02']` → FAIL.
- 현재까지 **확정된 사실**: Gazebo topic 이름은 광고되고 PosePublisher 식기 2개는 관측됐지만, ROS2 Image 첫 유효 frame은 수집되지 않았음. 토픽 광고는 실제 GZ 이미지 발행도, GZ→ROS 전달도 증명하지 않음.
- 기존 ST-01/02 실수신 성공 사례 [#45310092985](https://github.com/silverbjin/samsung_AXI/actions/runs/45310092985)를 보존함. 카메라·물리/좌표·기존 Nav2를 재개발하지 않음.
- **원인 가설**: 5Hz 시뮬레이션 주기(최초 양의 타임스탬프 약 200ms)와 OGRE2 / ros_gz DDS 초기화의 *wall-clock 지연*을 하나의 sim-time 310ms 제한으로 묶어 초기 데이터가 지연될 때 실패. 아직 확정된 원인 아님.
- 최소 수정(계측 먼저): DDS publisher 발견 대기(최대 12 wall sec), Gazebo Transport에서 **실제 메시지 1개**를 받는 `gz topic -e -n 1` 자체 probe(관측 진단 전용), ROS image callback 횟수/0stamp/중복/최초 stamp, /clock, Pose 개체, 각 환경을 첫 오류 JSON으로 보존.
- **모션/라벨 누출 방지**: Gazebo step을 연달아 늘리는 대신 sim 약 200ms 이상에서 시뮬레이션을 paused로 유지한 채 ROS callback 수신을 벽시계로 추가 대기함. t1/t2 정렬 검증과 실제 캡처 Pose 하강 검증을 삭제하지 않음. 310ms 넘으면 계속 FAIL; 이미 낙하한 샘플을 재활용 금지.
- 학습 포인트: 실제 메시지 유무, Publisher 발견, 시뮬레이션 시계와 wall clock은 독립 관측축. 3단계 로그가 확보되기 전까지 `ROS_IMAGE_PIPELINE_READY` 또는 L2 PASS라고 출력하지 않음.
- **재검 결과**: 첫 수정 SHA `4fdd29be...`에서 기존 문자열 검증 테스트 1건이 코드 구조 변경을 과도하게 제약해 L0 RED [#45325355574](https://github.com/silverbjin/samsung_AXI/actions/runs/45325355574). 단위 함수 `pre_event_ready`의 실제 시각·식기 검증으로 교체한 SHA `05779ae191ff41c922e067ec7cc5c2356dcffeaa`에서 [GitHub Actions #45325486957](https://github.com/silverbjin/samsung_AXI/actions/runs/45325486957) **L0 26 PASS / L1 PASS / 실제 L2 4/4 PASS**. 이미지 stamp 0.2s 4건, pose/실물리 HELD2/FALL2, 원본 SHA 검증. **결론: CI 환경에서 원래 실패 조건을 재현하지 않고 실제 데이터를 생산하도록 안정화 성공**. 렌더링 지연 vs DDS 도착 지연의 단일 독립 원인은 처음 실행 증거만으로 확정 불가; 조건 분리·로그 계측 이후 초기 4실험 안정화로 확인. 앞으로 GZ probe 수신 여부와 ROS callback count 성공 진단을 CI에 기록.
