# ROS 2 레스토랑 자율주행 배달 로봇 — 강사 직접 개발용 독립 MVP 인계문서
## AI 에이전트 = 시니어 ROS 2 개발 책임자 / 강사 = 개발 소유자·최종 시연자

> **문서 ID:** RESTAURANT-ROBOT-SIM-INDEPENDENT-MVP-HANDOFF-20261119  
> **버전:** 2.0 / 2026-11-19 KST  
> **상태:** **개발 착수 지침(PLAN)**. 이 문서 자체는 신규 레스토랑에서 실행·완주했다는 증거가 아님  
> **독립 트랙:** 로봇·시뮬레이션 MVP, 강사가 직접 개발·검수하여 **훈련생 지도용 데모/실습 기준선**으로 활용  
> **환경:** Windows WSL2 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / RViz2 / Python / TurtleBot3 Waffle Pi + 등록 RGB-D 확장  
> **상위 참고 문서:** `RESTAURANT_ROBOT_SIM_MVP_SENIOR_JUNIOR_HANDOFF_20261118_KO.md`  
> **병렬 독립 트랙:** `RESTAURANT_VISION_AI_2PERSON_HANDOFF_20261113_KO.md` (AI 훈련생 2명; 이 문서의 인수 전제조건이 아님)

---

## 0. 이번 변경의 가장 중요한 의사결정

이 문서는 기존 「시니어 AI × 주니어 도제식 개발」 인계의 **운영 방식**을 변경한다.

1. **개발자는 강사 본인**이다. 강사가 개발 목적·범위를 정하고 실제 WSL2에서 최종 시연한다. 주니어가 시니어 프롬프트를 검토해 다시 보내야만 개발하는 **2턴 도제 승인 루프는 적용하지 않는다**.
2. **AI 에이전트는 15년 이상 ROS 2·Gazebo·Nav2 실무 경험을 가진 시니어 개발 책임자 역할**로 조사, 계획, 코드 작성, 실행, 디버깅, 최소 확인, 문서화까지 **하나의 개발 목표를 스스로 마무리**한다. '시니어'는 작업 역할 설정이지 실제 인간 경력에 대한 주장으로 사용하지 않는다.
3. **독립된 새 작업공간/저장소를 사용**하고, 기존 AXIA Instructor/Student/Public CI `main`은 기본 **읽기 전용 재사용 원본**으로 취급한다. AXIA 본류와 임의 통합·수정·병합하지 않는다.
4. **MVP의 최우선 합격 기준은 실제 동작**이다. 레스토랑에서 로봇이 **출발 → 지정 테이블 배달 → 복귀**하는 것을 우선 완성한다. 성능, 반응속도, 최적 경로율, 대규모 일반화, 정밀 위치오차, 확장성 개선은 **MVP 성공 이후 별도 단계**다.
5. **범위 확대·과도한 검증 금지**. 10~15회 반복 인수, 시간 임계값(120/150ms 등), 다중 PC 재현성, 장시간 부하 시험, 엄격한 TDD 전면 적용, 복잡한 로깅 프레임워크, 안전 인증을 현재 트랙의 완료 조건으로 끌어오지 않는다.
6. 모델 학습/고도화는 AI 훈련생 **별도 트랙**에서 수행한다. 그 트랙의 성공 여부는 이 로봇 MVP 종료를 막지 않는다. 기존 AXIA의 검증된 YOLO/Depth 예제는 화면 시연 및 통합 참고용으로 사용 가능하다.
7. 동작 우선이 **고장·충돌을 성공으로 보고해도 된다는 의미는 아니다**. 센서가 없거나 Gazebo가 빈 창인 경우, 실제 이동 없이 Path만 표시된 경우, 충돌했는데 안전 정지 성공이라고 주장하는 경우는 PASS가 아니다. 시연 중 비정상 위험 상태에서는 Goal 발행을 중단한다.

**범위 우선순위:** (①) 실제 배달·복귀 → (②) LiDAR·Depth 안전 대응 → (③) 메뉴별 정책 차이 → (④) 발표·교육용 정리. ①이 실패한 동안 ③·④의 고도화에 시간을 쓰지 않는다.

---

## 1. 데모 시나리오 고정 — `RESTAURANT-DEMO-01`

### 1.1 장면과 공간

첨부된 레스토랑 평면 배치 이미지(`image(2).png`)를 참고한다. 이미지의 번호는 **개발을 위한 잠정 논리적 구역 번호**로 간주한다. 실제 도면 치수와 각 번호의 운영상 의미는 확인되지 않았다.

- **1번:** 조리대 앞 픽업/출발 및 복귀 지점
- **3번:** MVP의 유일한 필수 배달 목적지(테이블 접근 Pose)
- **2·4·5·6번:** SDF에 가구/접근 구역을 배치하되 **각 테이블의 실제 배달 주행은 MVP 필수 아님**
- **사람형 장애물 1개:** 실제 LiDAR 또는 Depth에서 관측 가능한 단순 물리 충돌체 포함. AXIA D08 프록시 재사용 후보
- **실제 음식 적재:** 시뮬레이션 상태·텍스트 표시로만 표현. 로봇팔, 음식 물성, 픽업 메커니즘은 개발하지 않음

외벽, 카운터, 테이블·의자, 출입구는 기본 SDF 박스와 공식 제공 모델 위주로 만든다. 시각적 재현도보다 **통로 확보, Collision, 센서 관측**이 우선이다. 로봇의 목표 좌표는 테이블 중심이 아닌 주행 가능한 **접근 Pose(x, y, yaw)** 로 설정한다.

### 1.2 실제 시연 한 번의 흐름

1. 강사의 단일 명령으로 Gazebo 레스토랑 World, Waffle Pi, RViz2가 열린다. **빈 Gazebo 창은 실패**.
2. 이미 한 번 생성·저장해 둔 SLAM 지도(`restaurant_map.yaml` 등)를 로딩하고 AMCL 위치 추정을 시작한다. 지도 **생성 과정은 별도 짧은 시연 또는 녹화**로 입증할 수 있다.
3. 콘솔에서 `NORMAL` 메뉴, 목적지 `table_3`을 선택한다.
4. Python 배달 관리자가 Nav2에 **실제 이동 Goal**을 보낸다. 로봇이 1번에서 3번 접근 위치까지 이동한다.
5. 이동 경로에 **물리 장애물 1개**를 출현시킨다. LiDAR/Depth로 인지해 Nav2 Costmap/Collision Monitor에서 감속·정지 또는 안전 우회가 작동하는 것을 보여준다. 제거 후 주행을 재개한다. 자동 복구 구현이 복잡하면 운영자 승인에 따른 재개도 허용한다.
6. 3번에서 `DELIVERED` 상태를 표시하고, 강사의 수령 확인 후 **1번으로 실제 복귀**한다.
7. 동일 메뉴 조건에서 `SOUP`을 선택했을 때 **더 낮은 주행 속도 정책 또는 안전 경로 가중치가 적용됨**을 설정과 실동작으로 짧게 보여준다. 메뉴별 매번 완주·별도 성능 비교는 불필요하다.
8. 강사가 `Ctrl+C`로 종료하고 관련 프로세스가 정리된다.

**영상만 성공한 것처럼 연출하는 데모 금지:** `ComputePathToPose`의 경로 표시만으로 실제 `NavigateToPose` 이동 성공을 주장하지 않는다. 필요 최소 증거는 Action Result + `/odom` 변화 + Gazebo 또는 RViz에서 확인된 실제 이동이다.

### 1.3 정식 MVP 완료 기준(숫자 성능 목표 없음)

| ID | 실제로 확인할 것 | 최소 완료 판단 |
|---|---|---|
| M1 | 레스토랑 World + 로봇 화면 | Gazebo에서 모델이 보이고 기초 Collision이 존재함 |
| M2 | 실제 LiDAR 지도 | `/scan` 관측을 바탕으로 지도 파일 1개 생성·저장·재로딩 |
| M3 | 위치 추정 | AMCL/TF와 실제 로봇 위치가 주행을 시작할 정도로 일치함 |
| M4 | **실제 배달·복귀** | 1→3→1 한 차례 이동 완주; Nav2 결과·위치 변화 확인 |
| M5 | 메뉴 상태 | `NORMAL`과 `SOUP`의 차이가 제어 정책에 적용되는 모습 확인 |
| M6 | LiDAR·Depth 활용 | 센서 데이터를 실제 ROS에서 받으며 장애물 대응 경로에 연결됨 |
| M7 | 물리 장애물 대응 | 물리 객체가 경로에 들어오면 감속·정지 또는 회피하고 제거 후 재개함 |
| M8 | 운용성 | 실행 방법·종료법·핵심 로그가 강사에게 설명 가능함 |

**M1~M8을 완료하면 개발을 멈추고 강사용 기준선(tag)을 고정한다.** 정확도 0.25m, 120ms 응답, 10Hz/30FPS, 3/3·15/15 반복 같은 수치 목표를 추가하지 않는다. 주행이 성립하는 기본적 안전 여유는 필요하나 상용 성능 인증은 목표가 아니다.

---

## 2. 재사용 우선순위와 실무 주의사항

### 2.1 공식 우선

| 공식 자산 | 무엇을 그대로 사용할까 | 직접 만들지 말 것 |
|---|---|---|
| [ROBOTIS TurtleBot3 `jazzy`](https://github.com/ROBOTIS-GIT/turtlebot3_simulations/tree/jazzy) | Waffle Pi SDF·LiDAR·RGB·모터·Gazebo Bridge, `turtlebot3_house` 가구 자산 | 로봇 바퀴 물리/센서 드라이버 |
| [Gazebo Harmonic](https://gazebosim.org/docs/harmonic/) | SDF World, 모델 포함, 센서, 물리 Collision | 3D 엔진·고급 메시 제작 |
| [SLAM Toolbox](https://github.com/SteveMacenski/slam_toolbox) | 지도 생성 및 저장 | SLAM 알고리즘 |
| [Nav2](https://docs.nav2.org/) | AMCL/Map Server/Planner/Controller/Costmap/Collision Monitor | Nav2 경로계획·회피·모터 제어 코어 |
| [Nav2 Simple Commander](https://docs.nav2.org/jazzy/configuration_and_development/simple_commander_api/simple_commander_api/) | Python Goal/Result, waypoint 실행 | 커스텀 Action 서버 |
| [ros_gz](https://github.com/gazebosim/ros_gz) | ROS ↔ Gazebo 메시지 브리지 | 별도 네트워크 브리지 |

**Waffle Pi 핵심 사실:** 공식 Jazzy `turtlebot3_waffle_pi/model.sdf`는 기본 `gpu_lidar`와 일반 RGB `type="camera"`를 제공한다. 기본 카메라를 RGB-D로 단정하지 않는다. RGB-D는 **AXIA D05에서 확인된 `rgbd_camera` 장착형 구현을 선택적으로 재사용**한다.

### 2.2 AXIA 우선 확인 파일(복제보다 선택적 이식)

| 경로 및 출처 | 재사용 목적 | 주의 |
|---|---|---|
| [AXIA D04 Vision](https://github.com/silverbjin/axia-robot-safety-instructor/tree/main/ros2_ws/src/axia_d04_vision_demo) | YOLO/카메라/디버그 화면 구성 | 모델 고도화는 AI 별도 트랙 |
| [AXIA D05 Depth](https://github.com/silverbjin/axia-robot-safety-instructor/tree/main/ros2_ws/src/axia_d05_depth_demo) | 같은 RGB-D 센서의 거리 관측/무효 입력 처리 | 관측 자체가 보호 정지 기능은 아님 |
| [D05 RGB-D Mounted Scene](https://github.com/silverbjin/axia-robot-safety-student/blob/feature/d05-mounted-rgbd-actor-live-20261113/block_B/day05/gazebo_live/prepare_scene.py) | Waffle 카메라에 등록 RGB-D 장착 | 기존 교육 장면의 시연 코드, 새 월드에서 확인 필요 |
| [AXIA D06 Collision Monitor config](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/main/d06/params/collision_monitor_d06.yaml) | 감속·정지 기본 설정 참고 | 원본은 `/axia/d06/test/*` 격리 시험, 그대로 실주행에 복사 금지 |
| [AXIA D07 Planner](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/main/d07/params/nav2_d07_planner.yaml) | LiDAR/Costmap/Path 연결 패턴 | D07-H01은 무주행 Path 확인임 |
| [AXIA D08 Physical Human Proxy](https://github.com/silverbjin/axia-robot-safety-ci-public/blob/main/d08/harness/d08_live_world.py) | 시각 메시+Collision+Contact가 한 모델에 있는 사람 프록시 | 새 월드에서 센서가 물리체를 감지하는지 재확인 |
| [AXIA P0/P1 Bringup](https://github.com/silverbjin/axia-robot-safety-instructor/tree/main/ros2_ws/src/axia_safety_bringup) | 초기 Gazebo/Nav2/Lifecycle 연결 | 원본은 Waffle 계열. Waffle Pi 제어 브리지와 충돌 여부 확인 |

기존 D05는 실제 Gazebo RGB-D/YOLO 거리 관측을 확인한 기록이 있지만, **새 음식점에서 주행하는 로봇의 안전 제어까지 검증한 것은 아니다**. D07 경로 변화 기록도 `goal_sent=false`인 읽기 전용 데모이므로 실제 배달 성공 증거로 사용하지 않는다.

- **소스 정책:** 기존 AXIA 저장소의 `main` 수정·병합·기존 테스트 재실행을 기본 작업으로 삼지 않는다. 새 독립 저장소에 필요한 설정·파일만 반영하고 출처 URL·commit SHA·라이선스만 간단히 남긴다.
- **제어 주의:** Waffle Pi 공식 Bridge의 `/cmd_vel` 타입 및 기존 AXIA 제어 체인의 `Twist`/`TwistStamped` 호환을 확인한다. 최종 구동 토픽에 서로 다른 두 퍼블리셔를 붙이지 않는다.
- **센서 주의:** RGB/Depth는 같은 등록 센서의 장면·timestamp/optical frame을 사용한다. Depth가 존재한다는 이유만으로 Collision Monitor가 이용한다고 주장하지 않는다.
- **전환 최소화:** AXIA 전체 Supervisor/Guard/Fault Injector를 이번 MVP에서 반드시 이식하지 않는다. 공식 Nav2 + Collision Monitor만으로 시연이 되면 **그 상태에서 개발 종료**한다.

> **출처 확인 메모:** 이전 인계문서에서 확인된 AXIA main 기준값은 Instructor `f46874470a814be8f6976b6adbcaa1e43a1fe681`, Student `6a3047b5aa219687f5fc918e467cea5115d3d482`, Public CI `62e366b51c64da25ad0216328fe1e019b78e0bef`(2026-11-18 조회)이다. 이는 과거의 참고 기준값으로, 실제 착수 시 변경 여부만 확인하고 사용 파일의 SHA를 기록한다. 이번 문서가 최신 HEAD 확인·실주행을 완료했다는 의미는 아니다.

---

## 3. 신규 개발해야 하는 것만 명시

**필수 구현 패키지 3개 내외로 제한**한다. 별도 패키지가 꼭 필요하지 않은 설정은 `restaurant_bringup`에 통합한다.

```text
restaurant_robot_mvp/                    # 새 독립 workspace·Git 저장소(이름은 제안)
├── README.md                            # 단일 실행/종료/문제 해결
├── docs/
│   ├── HANDOFF.md                       # 본 인계문서
│   ├── REUSE_NOTES.md                    # 재사용 URL·SHA·수정 사유 1쪽
│   ├── WORLD_LAYOUT.md                   # 배치 가정·접근 Pose
│   └── DEVELOPMENT_LOG.md               # 오류/수정/결과·강의 소재
├── src/
│   ├── restaurant_world/
│   │   ├── worlds/restaurant.sdf         # 벽·카운터·테이블·통로
│   │   └── config/tables.yaml           # 최소: pickup, table_3
│   ├── restaurant_bringup/
│   │   ├── launch/                       # Gazebo / mapping / navigation
│   │   └── config/                       # Nav2·sensor bridge·CM YAML
│   └── restaurant_delivery/
│       ├── restaurant_delivery/
│       │   ├── delivery_manager.py      # 배달/복귀 FSM+Nav2 Goal
│       │   └── menu_policy.py           # NORMAL / SOUP 설정
│       └── config/menu.yaml
├── scripts/restaurant_demo.sh           # 하나의 실행기 (추후 작성)
└── evidence/                             # 이미지/짧은 로그; 대용량 원본 별도 보관
```

**처음부터 만들지 않을 것:** 새로운 서비스용 웹 앱, 마이크로서비스, 별도 ROS 메시지 표준, 파라미터 자동 튜닝 프레임워크, AI 모델, Planner/Controller/Collision Monitor 코어, 전체 AXIA Fault Injector, Docker 이미지, 경로 그래프 DB, RTF 성능 수집기, 확장된 다중 시나리오 평가 도구.

**Python A* 처리 방침:** 기존 구현 조건에서 경로 계획 알고리즘을 발표해야 하므로, Nav2가 실제 주행 가능한 경로를 만들고 Python은 **소규모 경유점 선택**을 담당한다. 레스토랑에 선택 가능한 통로가 있으면 `route_planner.py`에 4~6노드의 단순 A*를 추가한다. 없는 통로를 억지로 만들거나 자체 Nav2 Planner를 작성하지 않는다. A* 개발은 실제 배달 완주 이후에만 진행한다.

---

## 4. 개발 순서 — 기능 성공을 우선하는 6개 작업

> 4주/20작업일은 **운영 참고치**이고, 매 단계의 성능 목표나 납기 인증이 아니다. 실제 성공 순서에 따라 앞당기거나 단순화한다. 모든 단계에서 AI 에이전트가 스스로 조사→구현→실행 가능한 범위 내 테스트→최소 수정→보고를 수행한다.

| 작업 | 구현 내용 | 성공하면 다음으로 이동 | 하지 않을 것 |
|---|---|---|---|
| **S0. 재사용 점검** | 공식 Waffle Pi/AXIA 파일 확인, 새 독립 저장소/환경 구성 | 실제 실행 가능한 Bringup 경로 1개 선정 | 전체 AXIA 브랜치·PR 전수 조사 |
| **S1. 레스토랑 World** | 첨부 이미지 기준 기본 SDF, 통로·픽업·테이블3, Collision | Gazebo GUI에서 실제 공간/로봇 보이고 주행 가능 | 고급 3D 디자인·모든 테이블 정밀 모델링 |
| **S2. 센서·지도·위치** | Waffle Pi + AXIA RGB-D, `/scan`, SLAM 지도 1회, AMCL | 지도 파일 저장·재로딩 및 위치 추정 확인 | 지도 최적화 실험·RGBD 알고리즘 개발 |
| **S3. 실제 배달·복귀 (최우선)** | Nav2 Goal, `table_3` 배달, 수령 확인, pickup 복귀 | 한 번 실제 이동 성공 + Action/odom 근거 | 복잡한 FSM·다목적지·정밀 도킹 |
| **S4. 메뉴·장애물 안전** | NORMAL/SOUP 정책 차이, 1개 물리 프록시, LiDAR/Depth→Costmap·CM | 실제 주행 중 회피 또는 정지→재개, 메뉴 정책 반영 | 새 제어 알고리즘·엄격한 120ms 게이트 |
| **S5. 시연 고정·교육자료** | 원샷, 간결한 가이드, 짧은 오류·수정 사례 | 강사 WSL2에서 `DEMO-01` 한 번 완주 | 성능 보고서·장시간 회귀·패키지 제품화 |

### 4.1 권장 진행 일정(고정하지 않음)

- **1주차:** S0~S1. 로봇이 실제 Gazebo 레스토랑에 떠 있는 모습을 먼저 확보.
- **2주차:** S2~S3 진입. 지도 생성보다 **한 번의 실제 배달 주행**에 집중.
- **3주차:** S3 완료 및 S4. 기존 AXIA 안전 코드 설정을 최대 재사용.
- **4주차:** S4~S5. 통합 시연 안정화, 영상, 교육용 회고만 수행.

**일정 지연 시 축소 순서:** 고급 가구/텍스처 → 모든 테이블 접근 좌표 → 메뉴별 경로 변경(속도 정책만 유지) → 완전 자동 장애물 재개(수동 확인 재개 허용) → AI 모델 연동. **실제 1→3→1 주행 자체는 축소 대상이 아님.**

---

## 5. AI 시니어 에이전트의 실행 계약

### 5.1 역할과 자율 수행 범위

- 강사와 **시니어 개발자 대 시니어 프로젝트 오너** 관계로 협력한다. 사용자를 '주니어'로 간주하거나 학습·재전달을 강제하지 않는다.
- 현재 목표와 필요한 최소 자료를 짧게 설명한 후 **실제 개발을 진행**한다. 계획을 다시 사용자에게 보내 승인받는 루프, 매 코드 변경마다 프롬프트 재전달하는 루프는 금지.
- 각 단계에서 공식 패키지·AXIA 코드를 먼저 확인하고, **그대로 사용할 수 있는 것은 사용**한다. 필요한 코드만 만든다.
- 문제가 발생하면 `실패 로그 → 최초 실패 지점 → 공식 문서/기존 AXIA 해결 이력 → 가설 하나 → 최소 수정 → 같은 경계 재확인`을 따른다.
- 결과를 보고할 때 **실제 실행 여부, 화면에서 확인된 동작, 변경 코드, 다음 행동**을 간결하게 기술한다. 완료 단계마다 1쪽 분량의 `DEVELOPMENT_LOG`를 누적하여 강의 소재로 활용한다.
- 실행 도구가 없거나 WSL2 현장에 직접 접근할 수 없으면 **그 부분을 완료했다고 주장하지 않고**, 강사가 한 번 실행할 명령·관찰 결과·실패시 로그 위치를 제시한다. 실제 결과가 전달되면 이어서 원인을 수정한다.
- 특별한 범위 변경이 없는 한 S0~S5를 자율적으로 진행한다. 통합이 확인되면 개발을 **중단**하고 기준선을 고정한다.

### 5.2 도구·CI·검증을 최소화하는 원칙

| 상황 | 해볼 검사 | 충분한 종료 조건 |
|---|---|---|
| 새 Python 코드 | `python -m compileall` + 해당 기능의 작은 테스트 | 문법/핵심 상태 전이 확인 |
| 새 Gazebo World | SDF 파싱 + 실제 gz sim 한 번 | 모델이 보이고 Collision/통로 확인 |
| ROS 패키지 변경 | `colcon build --packages-select ...` | 빌드 및 정상 노드 실행 확인 |
| Nav2 목표 주행 | **실제 Gazebo 한 번** | Goal/odom/화면이 맞는 실제 도착·복귀 |
| 센서 안전 통합 | **장애물 한 번** | 실제 센서→CM/Costmap→주행 반응 확인 |
| 최종 인수 | **강사 WSL2 통합 1회** | DEMO-01 완주, Ctrl+C 정상 종료 |

**CI 정책:** 가벼운 Python/설정 회귀를 공개 CI에 둘 수 있으나 CI 구축이 MVP 개발의 본업이 되면 중단한다. 실물에 가까운 Gazebo CI를 여러 워크플로로 반복 구축하지 않는다. **강사 WSL2에서 직접 동작을 보는 것이 최종 기준**이다. CI와 실제 PC 환경 차이가 발생하면 불필요한 반복 검증보다 **같은 실행 스크립트 사용**을 우선한다.

**금지 검증 기준:** 독립 리뷰어 강제, 다중 PC, 10회 이상 cold-run, 엄격한 안전 정지 시간 측정, 정확도·FPS·CPU/GPU·메모리 정량 최적화, 매 단계 수십 테스트, 전 시나리오 자동 증거 서명·압축·체크섬 강제. 필요하다면 사용자가 별도 '성능 고도화 단계'를 승인한 후에만 수행한다.

### 5.3 실패 처리 한도

1. 같은 현상을 반복 재실행하기 전에 **기존 로그에서 첫 오류를 찾는다**.
2. 공식 문서·AXIA 해결 코드로 해결 가능하면 해당 파일/설정만 수정한다.
3. 복잡한 기능을 새로 설계해야만 가능한 상황이면 **더 간단한 공식 구성을 선택**한다.
4. 지나치게 오래 걸리는 주변 기능은 `DEFERRED`로 표시하고 배달 성공 경로로 복귀한다.
5. 시연 핵심이 실패하면 **성공한 척 진행하지 않고 BLOCKED**로 보고한다. 추가 구현 범위를 넓히기 전에 현재 기능을 복구한다.

---

## 6. AI 시니어가 교육용으로 남길 최소 지식 자산

강사는 개발 과정 자체를 훈련생 지도에 활용한다. AI 에이전트는 **별도 수업용 시스템을 만들지 않고** 아래를 기존 코드와 함께 남긴다.

| 산출물 | 내용 | 분량 가이드 |
|---|---|---|
| `README.md` | 클론→설치 의존성→원샷→메뉴 선택→Ctrl+C→오류 확인 | 따라 할 수 있는 1개 흐름 |
| `docs/ARCHITECTURE.md` | Gazebo/Bridge/Scan/Depth/SLAM/AMCL/Nav2/CM/배달관리자 관계 | Mermaid 다이어그램 1개 |
| `docs/WORLD_LAYOUT.md` | 제공 이미지의 좌표 가정·픽업 및 테이블3 접근 Pose | 표 1개 |
| `docs/REUSE_NOTES.md` | 가져온 AXIA/공식 소스와 이유/주의 | 표 1개 |
| `docs/DEVELOPMENT_LOG.md` | 실제 오류 1~3건의 원인·수정·확인, 코드 링크 | 짧은 회고 |
| `docs/DEMO_GUIDE.md` | 강사용 시연 대사·기대 화면·명령·복구 | 5~10분 시연 기준 |

개발 과정에서 매번 별도 발표자료·동영상·교재·테스트 보고서를 대량 제작하지 않는다. 최종 코드가 정상 동작할 때 시연 화면을 간단히 녹화하고 설명자료를 완성한다.

**훈련생 시연 핵심 질문(교수법 참고):**

- 왜 Gazebo에 보이는 사람 이미지가 곧 LiDAR에서 감지되는 장애물은 아닌가?
- 왜 Nav2가 경로를 계산했다고 해서 로봇이 실제 이동했다고 할 수 없는가?
- 왜 Waffle Pi 기본 RGB 카메라와 AXIA가 확장한 RGB-D를 구별해야 하는가?
- 메뉴에 따른 정책은 어느 Python 코드에서 변경되고, 최종 속도는 어느 계층에서 적용되는가?

---

## 7. 독립 트랙과 AI 훈련생 2인 팀의 경계

로봇 MVP는 **AI 학습 모델이 아직 없어도 단독으로 시연이 성공해야 한다.** 사람의 충돌체는 Gazebo SDF/AXIA 프록시로, 메뉴 선택은 CLI로 구현한다.

AI 팀에는 필요할 때 다음만 제공한다.

- 고정 `restaurant.sdf`와 출발지/테이블 접근 위치
- Gazebo 카메라 RGB/Depth/CameraInfo 및 TF 토픽명(현장 조회값)
- 사람형 물리 프록시 배치/장면 ID, 재현 방법
- ROS 2 통합 시 사용할 읽기 전용 Detection 인터페이스

**금지:** 로봇 팀에서 사람·카트 YOLO 학습을 시작하거나, AI 팀 개발 완료를 강사 시연 승인 조건에 넣거나, AI Detection 노드에 `/cmd_vel` 발행 권한을 주는 행위. AI 팀의 별도 성능/학습 증빙은 별도 인계문서에서 관리한다.

---

## 8. 현장 디버깅 순서 — 첫 실패 지점만 점검

| 문제 | 즉시 확인할 사실 | 최소 조치 방향 |
|---|---|---|
| Gazebo 창만 있고 매장이 비어 있음 | server 로그, SDF 경로, model URI, GUI 렌더링 오류 | 모델 include 또는 렌더링 원인만 수정 |
| Waffle는 보이는데 움직이지 않음 | `/cmd_vel` 타입/발행자, Bridge, Nav2 Action Result, `/odom` | Twist/Stamped 호환 또는 lifecycle·Goal 수정 |
| 지도 생성 불가 | `/scan`, `/tf`, `/clock`, SLAM lifecycle | ROS 토픽/TF/시간 불일치 교정 |
| Goal이 거부됨 | AMCL 초기 Pose, map frame, Costmap, Goal tolerance | 그 범위의 설정만 변경 |
| Depth는 나오는데 안전에 영향 없음 | RGB-D→PointCloud2→CM/Costmap 실제 관측 소스 | 공식 Depth 브리지/프로세서 한 단계 보완 |
| 사람은 보이는데 로봇이 감지 안 함 | 물리 Collision, LaserScan/Depth, visual-only Actor 여부 | AXIA D08 물리 프록시 재사용 |
| 종료 후 프로세스가 남음 | 해당 launch 소유 PID, respawn, 종료 로그 | 이 데모가 소유한 PID만 순서대로 종료 |

문제가 생겼다고 임의의 `sleep 30`, 과도한 전역 `pkill -9`, 무작위 파라미터 튜닝부터 하지 않는다. 그래도 해소하지 못하면 당시의 로그와 변경 파일 1개만 확보하고 가장 좁은 질문부터 분석한다.

---

## 9. 신규 트랙을 여는 첫 마스터 프롬프트(그대로 재사용 가능)

아래 프롬프트는 **강사가 에이전트에게 직접 요청하는 실행 명령**이다. 주니어의 프롬프트 재전달이나 사전 승인 과정을 요구하지 않는다.

```text
당신은 ROS 2 Jazzy, Gazebo Harmonic, Nav2, SLAM Toolbox, Waffle Pi,
WSL2/WSLg 및 로봇 안전 제어에 숙련된 시니어 ROS 2 개발 책임자다.

프로젝트 오너는 강사 본인이다. 이 업무는 훈련생 2인 AI 모델 개발과
분리된 '로봇·시뮬레이션 단독 MVP 트랙'이다. 개발 결과는 강사의
훈련생 지도용 실제 시연·코드 해설 자산으로 사용한다.

이 인계문서의 RESTAURANT-DEMO-01을 최종 목표로 한다.
반드시 이 문서와 첨부된 기존 로봇/AI 인계를 먼저 읽고,
확인한 사실과 가정을 구분한다.

최우선 성공 기준은 성능이 아니라 동작 여부다.
레스토랑 Gazebo World에서 Waffle Pi + 등록 RGB-D·LiDAR가 작동하고,
SLAM으로 만든 지도를 로드해 실제 로봇이
픽업(1)→테이블(3)→픽업(1)로 이동하며,
NORMAL/SOUP 메뉴 정책 차이와 물리 장애물 감속/정지·재개를 시연한다.

공식 Nav2/SLAM/ROBOTIS와 AXIA D04~D08/P0-P1 코드를 먼저 조사해
재사용하고, 부족한 World/Launch/배달 상태 관리·메뉴 설정만 구현하라.
기존 AXIA Instructor/Student/Public CI main을 수정하지 않는다.
별도의 독립 workspace 및 Git 저장소로 개발한다.

진행은 S0 재사용 점검 → S1 레스토랑 World → S2 센서·지도·위치 →
S3 실제 배달/복귀 → S4 메뉴·장애물 안전 → S5 시연 고정 순으로 한다.
각 단계에서 기존 증거를 보존하고, 최초 실패 지점을 분석하여
최소 수정한 후 그 기능이 실제로 동작하는지만 확인하라.

과도한 확장·검수 조건은 엄격히 금지한다.
- 새 Planner/Controller/SLAM/안전 Supervisor/AI 모델 개발 금지
- 수치 성능 KPI(FPS/RTF/정밀 오차/정지시간), 다중 PC/장시간 스트레스 금지
- 3회/10회/15회 반복 검수와 전체 AXIA G00~G13 인증 이식 금지
- 불필요한 강제 TDD·거대 CI·다중 보고서·웹 대시보드 금지
- 주니어 도제식 프롬프트 재전달·단계별 사용자 승인 루프 금지

다만 실제 실행이 없으면 PASS를 주장하지 말라.
공식 Nav2 Path 계산과 실제 로봇 이동을 구별하고, 센서 화면과
실제 보호 기능의 연동을 구별한다. 로봇이 정지해야 할 상황에서
안전 제어를 우회하는 /cmd_vel 직접 발행은 금지한다.

먼저 현재 저장소/환경을 확인하고 S0~S1을 실제로 수행하라.
그 후 S2~S5도 같은 원칙으로 이어 진행하되, 강사 WSL2 GUI 같은
도구로 접근할 수 없는 경계는 한 번에 실행 가능한 명령과
예상 화면·실패 로그 위치를 제공하라.

각 단계 종료 때 다음 5가지만 보고하라.
1. 무엇이 실제로 동작하는가?
2. 어떤 공식/AXIA 자산을 재사용했는가?
3. 새로 작성·수정한 파일은 무엇인가?
4. 실패가 있었다면 첫 원인과 최소 수정은 무엇인가?
5. 아직 미검증한 것은 무엇이며, 다음 행동은 무엇인가?

M1~M8이 충족되면 개발을 종료하고 강사 시연용 기준선을 고정하라.
성능 고도화는 새로운 작업으로 별도 승인받기 전까지 착수하지 말라.
```

---

## 10. S0~S5 단계별 짧은 실행 프롬프트(문제가 생겼을 때 단계별 재개용)

**S0:** `AXIA와 ROBOTIS Jazzy의 실제 재사용 파일을 조회하고 독립 저장소를 준비하라. 정확한 Waffle Pi RGB-only/AXIA RGB-D 구조, Bridge 타입, Nav2 경로를 확인하되 기존 AXIA main은 수정하지 말라. REUSE_NOTES 한 쪽과 실제 첫 실행 명령만 제공하라.`

**S1:** `첨부 레스토랑 도면을 바탕으로 SDF World를 최소 박스/기존 가구 모델로 만들고 1번 pickup과 3번 table 접근 Pose를 정의하라. Gazebo에 World·로봇·Collision이 실제로 나타나면 종료하라. 그래픽 고도화 금지.`

**S2:** `Waffle Pi에 기존 AXIA D05 등록 RGB-D를 재사용해 Scan/RGB/Depth 토픽을 연결하고, SLAM 지도를 1개 저장한 후 AMCL로 다시 로드하라. 복잡한 센서 신뢰도 프레임워크를 개발하지 말고 유효한 한 번의 센서 수신과 지도/위치 확인만 수행하라.`

**S3:** `Nav2 BasicNavigator를 사용하여 pickup(1)에서 table_3으로 실제 주행하고 수령 확인 후 원위치로 복귀시키라. 경로 그림이 아닌 Action Result, /odom 변화, 실제 시뮬레이터 움직임으로 한 번의 성공을 확인하라. 지금은 메뉴·AI·세부 성능 개선을 하지 말라.`

**S4:** `NORMAL/SOUP 속도 정책을 적용하고 AXIA D08 물리 프록시 한 개로 실제 장애물 진입→감속·정지 또는 회피→제거 후 재개를 시연하라. LiDAR와 RGB-D가 Costmap/Collision Monitor에 어떻게 입력되는지 확인한다. 추가 안전 알고리즘·120ms 검수 금지.`

**S5:** `검증된 코드만 묶어 강사 원샷과 짧은 실행·종료·문제 해결 가이드를 작성하라. WSL2에서 RESTAURANT-DEMO-01 한 번 완주하면 기준선을 고정하고 성능 최적화·다중 시나리오 개발을 시작하지 말라.`

---

## 11. 시작 전·최종 완료 시 체크리스트

### 시작 전 (S0)

- [ ] 기존 로봇 인계 및 첨부 레스토랑 배치도 열람
- [ ] 별도 Workspace/저장소 결정(기존 AXIA main 읽기 전용)
- [ ] 실제 설치된 Jazzy/Harmonic/WSLg·Nav2 확인
- [ ] 사용할 Waffle Pi SDF/Bridge 및 AXIA D05 RGB-D 후보 선택
- [ ] `pickup`·`table_3` 접근 위치 가정 기록

### 시연 종료 (S5)

- [ ] Gazebo 레스토랑 안에 로봇·가구가 정상 렌더링됨
- [ ] `/scan`, RGB, Depth가 실제 수신됨
- [ ] SLAM 지도 파일을 생성·재로드함
- [ ] AMCL을 사용해 실제 이동 Goal을 수행함
- [ ] 1→3→1 주행·복귀 한 차례 완료함
- [ ] NORMAL/SOUP 정책 차이를 실제 적용함
- [ ] 물리 장애물 인지·감속/정지/회피·재개를 관찰함
- [ ] 단일 명령으로 실행하고 Ctrl+C로 종료 가능함
- [ ] 강사용 README/시연 가이드와 첫 실패·수정 사례가 남음

### 최종 판정 문구

- **`RESTAURANT_ROBOT_MVP=DEMO_PASS`** — 강사 WSL2에서 위 **실제 시나리오 완주** 및 기본 센서/안전/메뉴 확인을 모두 수행한 경우에만 사용.
- **`RESTAURANT_ROBOT_MVP=PARTIAL`** — 예: 월드·지도·Goal은 작동하지만 복귀 또는 장애물 대응이 미완료인 경우.
- **`RESTAURANT_ROBOT_MVP=BLOCKED`** — 필수 구동·브리지·센서·Goal 중 최초 실패가 남아 시연할 수 없는 경우.
- **`RESTAURANT_ROBOT_MVP=NOT_RUN`** — 작성·빌드·소스검토만 하고 실제 Gazebo에서 실행하지 않은 경우.

**이 문서 작성 시점의 판정은 `NOT_RUN`**이다. 이전 AXIA Run/보고서에서 검증한 범위를 새 레스토랑의 시연 성공으로 승격하지 않는다.

---

## 12. 성능 고도화는 별도 후속 프로젝트

이번 MVP 완료 **이후에만** 다음을 검토한다: 도착 위치 정밀도 측정·개선, 경로 비용 최적화, 반복 성공률, 충돌/정지 지연, 센서 융합의 정량 성능, 실시간 FPS/RTF, 여러 테이블 및 다중 로봇, 실물 하드웨어 안전 인증. 다음 단계 착수 여부는 강사가 필요성과 학습 목표를 별도로 판단한다.

> **최종 한 줄 원칙:** **"먼저 동작하는 레스토랑 자율주행 배달 로봇 한 대를 완성한다. 제대로 움직이면 MVP는 종료한다. 얼마나 빠르고 정확하며 확장 가능한지는 그다음 문제다."**
