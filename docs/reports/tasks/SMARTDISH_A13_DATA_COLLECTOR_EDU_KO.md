# A-13 — Gazebo/ROS 트레이 RGB+물리 관측 원샷·해시 출고기 (개발 교육 보고)

## 목적

4개 SDF 시나리오를 손으로 구성하거나 `gz`·ROS·B 수집기를 3~4개 터미널에서 실행하지 않고 `demo|single|batch` 하나의 진입점으로 통합합니다. AI OFF/Nav2를 켜지 않고 **독립 물리 시험**에만 사용합니다.

```mermaid
flowchart TD
 CLI["GUI 기본 WSL2 원샷 / 명시적 headless"] --> S["Scenario + seed + trial ID"]
 S --> G["새 GZ_PARTITION, ROS_DOMAIN_ID, Gazebo server+bridge"]
 G --> P["일시정지된 실제 Gazebo 5-step 반복"]
 P --> C["B 기존 save_unlabelled_frame() PNG"]
 P --> I["동일 시각 초기 Entity Pose"]
 I --> RUN["Gazebo 10초 physics unpause"]
 C --> RUN
 RUN --> OBS["실제 ROS /poses Pose_V→TFMessage+clock"]
 OBS --> E["SHA256SUMS, physics JSONL, initial/final, tar.gz"]
 E --> B["B 사람 라벨/권리 검토 후 별도 collect_tableware"]
```

## 실행 구조 및 안전 조건

- `scripts/smartdish_a_tray_bootstrap.sh`: 고정 SHA 확인, WSL2 ext4+전용 `~/samsung_AXI_A_TRAY`, 원격·브랜치·로컬 수정 확인 후 ff-only 갱신.
- `scripts/smartdish_a_tray_one_shot.sh`: GUI 기본, ROS 2 Jazzy/ros_gz_bridge/Pillow 점검, A package colcon build(Goal 없음).
- `scripts/smartdish_a_tray_live.py`: 실제 `gz sim -s`와 `ros_gz_bridge` 프로세스만 생성, Gaussian/가짜 주행결과 없음. 시험마다 새로운 GZ_PARTITION/ROS_DOMAIN_ID, 관측 후 자기 PID 그룹만 정리.
- `scripts/smartdish_tray_evidence.py`: 실제 이미지 SHA·별도 Pose JSONL SHA/크기, 시뮬레이션 시계(t1 이미지 ≤ t2 physics 시작), 유효한 식기 Pose, 3개 이상의 신규 영상 stamp, 관측 9초 이상. 손상되면 fail-closed.
- 원본 영상은 **B 기존 `ai/scripts/capture_tray_ros.py`의 `save_unlabelled_frame`**으로 `ai/data/private/A13_*.png`에 라벨 없이 저장하고, 시험 디렉터리로 복사합니다. 승인 전 B manifest를 수정하지 않습니다.

## 시험-관측 원리

1. World를 paused로 올리고 짧은 실제 Gazebo physics step을 수행하여, **초기 RGB+Gazebo dish pose가 먼저 있는지** 확인.
2. 초기 프레임의 sim timestamp가 0.2초 이내가 아니면 `A13_PRE_EVENT_CAMERA_TOO_LATE` 차단(이미 낙하한 뒤의 RGB가 학습 X로 들어오는 문제 방지).
3. 그 뒤 실제 Gazebo world를 unpause하고 **10 simulation seconds** 동안 자세/위치를 측정합니다. 위치 Z 하강·tray 이탈·기울기를 관찰값으로 기록합니다.
4. `HELD_OBSERVED`, `FALL_OBSERVED`, `INDETERMINATE`는 자동 **관측 후보**이며 `STABLE/UNSTABLE` 학습 라벨과 다릅니다. B 담당이 실제 물리 로그와 이미지·사용권을 검토한 뒤에만 기존 `collect_tableware.py` 등록.

## 모드

| 옵션 | 의미 | 전체 4개 물리 시나리오 L3 게이트 |
|---|---|---|
| `batch` (기본) | ST-01, ST-02, UN-01, UN-02 각각 독립 실행 | 예 |
| `demo` | ST-01, UN-01로 시연, 인수 아님 | 아니오 |
| `single --scene ...` | 단일 설정 디버깅 | 아니오 |
| `--gui` (기본) | 실제 Gazebo 시각 확인 | GUI 품질은 사용자 직접 |
| `--headless` | renderer는 유지하고 GUI만 비활성 | L2 CI 우선 |

## 인계와 미검증

- 출력: `generated/smartdish_tray/run_<UTC>_<pid>/` 아래 PNG, physics_observations.jsonl, scenario.sdf, pose 상태/메타데이터, SHA256SUMS와 `smartdish_a_tray_evidence.tar.gz`.
- B: `physics_observations.jsonl`는 이미지와 독립 파일, 사람 승인 전 labeling 금지. 승인 예시 CLI는 별도 B/C 인계 가이드.
- C: 기존 `/smartdish/tray/image_raw` 구독은 수정하지 않으며 모델 없을 때 UNKNOWN 정상.
- 실제 L2는 CI에서 Gazebo/OGRE2 실수신 결과가 나올 때만 PASS. GUI L3는 사용자의 현장 증거 전까지 **NOT_RUN**.
