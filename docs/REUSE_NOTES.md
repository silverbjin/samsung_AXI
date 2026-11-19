# S0 재사용 조사·기준선 (2026-11-19)

## 읽기 전용 원본

| 원본 | 조회한 기준 | 사용 범위 |
|---|---|---|
| [ROBOTIS TurtleBot3 simulations](https://github.com/ROBOTIS-GIT/turtlebot3_simulations/tree/jazzy) | `jazzy` commit `45633014a14e8f438495b532a723e4ad45cbbd31` / `turtlebot3_waffle_pi/model.sdf` blob `b898477ad9c9d702ecf22853913266fe1d295b6f`; 공식 Bridge YAML blob `7806de7a80ef177c786305010914ff96579500fa` | 로봇 SDF·센서·DiffDrive·공식 메쉬, Apache-2.0. 원본을 수정하지 않고 로컬 overlay 생성 |
| [Nav2 Jazzy](https://github.com/ros-navigation/navigation2/tree/jazzy/nav2_bringup) | `jazzy` commit `c7046550547d382a5186d106b0895eda02485d7c` / `tb3_simulation_launch.py` blob `db1964f955e3fa98d69cace024b2ad37b03380d4`, `nav2_params.yaml` blob `ac52c787f587288c448079fdcaa2f4c686f25fbd` | Navigation/SLAM official launch·기본 params를 로컬에서 사용·최소 overlay |
| [AXIA D08 Physical Proxy](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/main/d08/harness/d08_live_world.py) | blob `b9cefbf70b571769cb19748bc2ff6093ebf73672` | 사람 모습과 Collision 물리 일체화 원칙 및 RGB-D 등록 센서 구조만 참고. D08 소스 코드 복사하지 않음 |
| [AXIA D05 Depth](https://github.com/silverbjin/axia-robot-safety-instructor/tree/main/ros2_ws/src/axia_d05_depth_demo) | `package.xml` blob `a976d2e48f2579c75a946d0ea2c47d07d6836e77` | 교육용 거리 관측 로직 참고. 신규 MVP 핵심 구동 의존성에 넣지 않음 |
| [AXIA D06 Collision Monitor](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/main/d06/params/collision_monitor_d06.yaml) | blob `7fec41b5e7fc9edded0d297cca391955f35f6567` | 격리 테스트 토픽(`/axia/d06/test/*`)이므로 재사용하지 않음. 공식 Nav2 Collision Monitor 사용 |

조회 당시 `main` SHA: AXIA Instructor `604fe59c75de4975a10cd727d4a1d43914aba9f8`, Student `1c0ae40a4c8a7aeccc6d5b481abaef8689dcd933`, Public CI `2b9547b330cd54a95049a2e56fecfacca999f2fd`. 모두 **읽기 전용**이며, 이 프로젝트에 코드 변경/PR/병합하지 않았습니다.

### 핵심 기술 차이

- ROBOTIS Waffle Pi 기본 카메라는 `camera`, Depth 카메라가 아닙니다. S2에서 새 로컬 SDF 사본에 `rgbd_camera`를 장착합니다.
- ROBOTIS 원본 Waffle Pi Bridge는 `/cmd_vel`을 `geometry_msgs/msg/TwistStamped`로 브리지합니다. Nav2 Jazzy는 기본적으로 `Twist`를 사용하므로 본 프로젝트에서는 **한 개 ROS→Gazebo `/cmd_vel` Bridge만** `Twist`로 설정합니다.
- ROS 시스템/실행기에 설치된 Nav2의 실제 버전과 소스 SHA가 다를 수 있습니다. 빌드 성공과 실제 구독 타입 및 Costmap/CM 동작을 확인해야 합니다.

도면 이미지 원본은 제공되지 않았으며 SDF 공간 배치는 임시 가정입니다.
