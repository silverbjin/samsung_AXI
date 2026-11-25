# SmartDish A-11/A-12/A-13 개발 계획 및 기준선 조사 — 2026-11-24

## 검증한 Git 기준선
- main HEAD: `cc66b66a16ffc8020498d973ebe31a5c4ca439e0`, [PR #44](https://github.com/silverbjin/samsung_AXI/pull/44) merged=true, merge_commit_sha 일치.
- 현장 통합 실행 SHA `efedaf38aca421bcdd3056584483b9a85f00ba8b` → main 차이: `docs/reports/integration/SMARTDISH_MVP_FINAL_ACCEPTANCE_KO.md` 하나만 추가. **런타임 변경 없음**.
- 기존 A/B/C/D 코드는 이미 main에 포함됨. 신규 `feat/smartdish-a-tray-camera`는 main에서 분기하며 원래 A PR을 재병합하지 않음.
- **보호**: `restaurant.sdf`, `prepare_waffle_rgbd.py`, A NavigationAdapter, E WSL2 실행기/Navigation/Map/Collision Monitor/D Manager·UI를 이번 후속 기능으로 수정하지 않음.

## 재사용 소스와 미구현 경계

| 영역 | main 실제 자료 | 결론 |
|---|---|---|
| ROS Gazebo 실행기 | `src/restaurant_bringup/launch/world.launch.py` + bridge yaml | gz server/gui, Sensors OGRE2, ros_gz_bridge 재사용 방법 확인. 원래 world/bridge는 변경하지 않음 |
| 센서 구성 | `scripts/prepare_waffle_rgbd.py` | 정면 RGB-D SDF overlay 생성 패턴만 재사용. 전용 tray 카메라/bridge는 신규 opt-in |
| 식기 | `scripts/s7_scene.py` 및 `s6_scene.py` | 기존 고정(static) S7 stacked fixture는 물리 Ground Truth 금지. 신규 dynamic dish model 필요 |
| A | `src/smartdish_robot`, `docs/handoff/A_HANDOFF.md` | 3-leg 실제 WSL2 GUI PASS 보존. 신규 tray test는 Nav2 미가동 |
| B | `ai/scripts/capture_tray_ros.py` | /smartdish/tray/image_raw SensorData QoS 1프레임→라벨 없는 비공개 PNG, 메타데이터 저장 재사용 |
| B | `collect_tableware.py` `prepare_dataset.py` | B만 인간 라벨/물리 SHA/권리/manifest/224×224 변환/stack group split 소유 |
| C | `src/smartdish_ai/smartdish_ai/stability_inference_node.py` | rgb8/bgr8 /fresh 2s, SensorData QoS, model 부재 UNKNOWN. 신규 AI/가짜 모델 추가 금지 |
| E | `scripts/smartdish_e_wsl2_one_shot.sh` | AI OFF owner GUI 인수 성공 코드 그대로 보존; 별도 tray 전용 WSL2 원샷 |
| 실제 승인이 확인된 학습 이미지 | main B Dataset Card | 0건. 자동 물리 관측 후보는 B 사람 검토 전까지 `UNLABELLED_REVIEW_REQUIRED` |

## 설계와 수정 파일

```mermaid
flowchart TD
 CLI["A tray runner (demo/single/batch)"] --> GEN["A-12 deterministic standalone scene generator"]
 GEN --> GZ["Gazebo Harmonic physics + camera (real GPU/CPU rendering)"]
 GZ --> BR["A-11 ros_gz_bridge: Image + dynamic pose"]
 BR --> R["A-13 ROS read-only collector"]
 R --> P["raw PNG + stamp + pose/tilt/displacement JSONL"]
 P --> VAL["Hash/clock/before-after checks & per-trial evidence"]
 VAL --> B["B existing capture/label/prepare tools (human review)"]
 BR --> C["C existing image subscriber / 2s TTL"]
 ```

A-11: 독립 world에서 단일 640×480 RGB at 5Hz, 고유 `smartdish_tray_optical`/Gazebo image topic. 빌드가 아닌 Gazebo 실제 frame 수신으로 완료. 로봇 모델 overlay는 물리 베이스를 변경하지 않는 선택적 camera-only 생성기로 독립 제공하되, **로봇 위 적재 구조/시야 실제 동등성은 L3 검수 이전 NOT_RUN**.

A-12: 독립 trial 별 world 생성, 2 안정 후보 + 2 이탈/전도 후보. 기존 고정 fixture가 아닌 dynamic cylinder dish, mass/inertia/friction, gravity, initial pose/seed 보존. Gazebo dynamic_pose (또는 지원되는 pose topic)에서 실제 frame/position/tilt 및 위치 변화 기록. 예상 시나리오 이름은 라벨이 아님.

A-13: `demo`(2개), `single`(1개), `batch`(4개) GUI 기본, headless opt-in. 시험별 Gazebo server/bridge/pose observer 격리·고유 run ID; 준비→최초 RGB 프레임 및 초기 Pose→관측 구간→결과 기록→증거 원본 SHA → 작은 tar.gz. 기존 B의 별도 경로 `ai/data/private/` 및 수집기를 **수정하거나 자동 라벨 등록하지 않음**. B에게 복사·승인 절차만 안내. 각 시험 물리 결과의 STABLE/UNSTABLE은 B 승인 전까지 후보 상태.

## 검증 전략과 완료 경계

- L0: JSON/SDF syntax, GUI default, bridge msg/QoS, 기존 AI OFF 보호 파일 변경 0, pose 수치, 중복 trial/잘못된 타임스탬프·해시·근거 차단.
- L1: ROS Jazzy bridge/type 계약 + Python import. B/C 코드 변경 금지.
- L2: 실제 Gazebo server/camera/bridge/pose 서비스, **실제 RGB와 4 시나리오 물리 관측 성공일 때만 PASS**. GPU/렌더러 지원 불가 시 BLOCKED, mock/예상값으로 대체 금지.
- L3: 사용자 WSL2 실제 GUI 인수, 4 scenarios 및 소형 증거 파일 검수 전까지 NOT_RUN.
- 신규 SHA/PR은 A 후속 브랜치에만. A-11/12/13 단계별 분리 커밋 및 교육용 보고/실제 디버깅 기록.

공식 참고: Gazebo Harmonic [Sensors](https://gazebosim.org/docs/harmonic/sensors/), [ROS 2 Integration](https://gazebosim.org/docs/harmonic/ros2_integration/). 실제 런타임 topic을 위 문서에서 자동 확정한 것으로 오해하지 않도록 Gazebo L2에서 재확인.
