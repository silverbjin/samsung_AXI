# A-12/A-13-DBG-06 — Gazebo 일반 Pose_V의 ROS TF 프레임 식별 상실

- 실제 L2 Run [#45308446649](https://github.com/silverbjin/samsung_AXI/actions/runs/45308446649), 소스 `d7033a0727e07a3ef975d3771a0813716ead7aed`: L0 24 PASS, L1 Jazzy PASS. L2 실제 ST-01에서 `A13_GAZEBO_DYNAMIC_POSE_BRIDGE_NO_DISH` 첫 오류, 최종 PASS 없음.
- 직전 [#45307436741](https://github.com/silverbjin/samsung_AXI/actions/runs/45307436741)에서는 이미지 수신 불가였으나 이후 스텝 한정 보완으로 이미지 **수신 경계는 통과**, 식기 Pose 프레임 식별 단계에서 중단.
- L2 운영 로그: Gazebo `Sensors` renderer OGRE2 초기화 및 ROS 브리지 `/smartdish/tray/image_raw`·`/world/smartdish_tray/dynamic_pose/info` 정상 생성 메시지. 단, `Pose_V` → `TFMessage` 변환 뒤 **정확한 식기 이름이 있는 pose가 callback에서 관측되지 않음**. bridge 프로세스 살아있음을 물리 Pose 검증으로 대체하지 않음.
- 확인한 공식/업스트림 근거: [ros_gz #172](https://github.com/gazebosim/ros_gz/issues/172), 핵심 개발자 답변(2024-02-27): `/world/default/pose/info`는 TF bridged ground truth용으로 의도된 것이 아니며, **공식 `gz::sim::systems::PosePublisher`에서 `<use_pose_vector_msg>true</use_pose_vector_msg>`, `<publish_nested_model_pose>true</publish_nested_model_pose>` 설정을 사용**. [Gazebo Harmonic PosePublisher API](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1PosePublisher.html)에도 개별 `<topic>` 지원.
- 최소 수정: 기존 S7/ROS 코드 미수정. 신규 **독립 물리 SDF**의 각 `dish_01..03` 동적 model에 공식 PosePublisher 추가. 각 `/smartdish/tray/gz_pose/dish_XX`의 named `Pose_V`를 `/smartdish/tray/pose/dish_XX`에 `TFMessage`로 변환; 신뢰할 식기 이름 없으면 여전히 FAIL. 식기 질량/충돌/관성/중력 변경 0건.
- 검수: L0 SDF/bridge/계약 → L1 ROS → L2 실제 camera frame / 4 dynamic pose + before-after 지지 확인. 관측 데이터 없이 `HELD_OBSERVED`/ `FALL_OBSERVED`를 가짜로 만들지 않음.
- 원인 구분: 정확한 변환 메시지 개별 필드의 원본은 이전 CI에 저장되지 않았기 때문에, 위 브리지 프레임 식별 문제는 **업스트림 근거를 가진 원인 후보**이고 L2 GREEN 시 검증 완료. 실패의 직접 확인 사실은 `named dish pose 0`입니다.
