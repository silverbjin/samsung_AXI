# SmartDish A-14 — B-DATA-QA-01 반영 물리 데이터 근거 보강 및 독립 장면 확장 요청

## 소유권·우선순위

- A 기존 `smartdish_tray_world.py`/`smartdish_a_tray_live.py`/`smartdish_tray_camera.py`의 성공한 A13 4장면, AI OFF HOME→T03→DISH_RETURN→HOME, RGB GUI 경로 보존.
- A-13 original batch: 4장면, 640×480 RGB, 10s world-frame Pose/observed HELD/FALL. A GUI Owner 인수 이전 기록 존중. 새 변경 없는 A13 전체 재실행 금지.
- **P0 필수: GT를 만들 수 있는 계측 계약을 먼저 구현**. 그다음 P1 여러 독립 geometry 장면 수집. 계측 없이 기존 장면 수만 늘리면 GT·독립성 HOLD가 그대로입니다.
- 이 요구서는 A **독립 브랜치**에서 개발할 작업 명세이며 B 코드나 A 소스 수정 커밋이 아닙니다.

## A14-P0 — 계측·좌표계·시간·비정답 원본

1. **좌표계**: 각 시각 t에 시뮬레이션 타임 기준 `T_world_tray(t)`와 `T_world_dish_i(t)`를 각각 저장하고 `T_tray_dish_i(t)=inv(T_world_tray(t)) @ T_world_dish_i(t)`를 계산·검산. 트레이가 정적인 독립 세계면 `STATIC_TRAY`/정적 pose 출처 명시. 로봇 주행에서는 Gazebo 내 트레이 실제 동적 pose가 있어야 하며 `STATIC_TRAY` 위조 금지. frame_id/parent_id, quaternion 정규화, 단위(m/rad/s), timestamp_ns/step_id, transform source와 결측 이유 기록.
2. **Velocity**: 위치·자세의 시각 t 실측 속도(선형/각속도, 좌표계·단위·출처) 또는 스냅샷에서 계산한 `DERIVED` 속도를 구분. 포즈 변화율이 측정 twist인 것처럼 표기하지 말 것. 시뮬레이션 이력 샘플링 명시, max_gap/누락/불규칙·역행/clock reset 검증.
3. **Contact/support**: 트레이-식기, 식기-식기, 식기-바닥 접촉 쌍·시간·collision IDs·Gazebo sensor/topic source를 원본으로 저장. Gazebo Harmonic Contact Sensor/ros_gz bridge가 실제 사용 가능한지 **L1 기능 탐색** 후 최소 구현. `no_event`와 `sensor_unavailable`을 구분하고, 센서가 비활성인데 Contact0이라고 처리 금지. support-loss 및 tray egress 증거는 후처리 측정치로 별도 저장.
4. **RGB(t0)**: 실제 Image 헤더 timestamp(원본 640×480 RGB), camera frame/topic/encoding, SDF static configured camera pose 및 관련 파일 SHA; 동적 실제 카메라 TF는 별도 실측/미실측 상태 필드. t0는 외란/낙하 **이전 캡처** 검증; 이미 초기 붕괴된 장면은 `UNKNOWN/INVALID`로 보류. t0와 물리 nearest pose의 시간 차/상한을 계약으로 검증.
5. **관측 구간**: 정상/낙하 10 sim sec 관측 vs wall time을 구분. 규칙이 요구하는 샘플링 Hz, 최대 허용 gap, 관측 범위·종료 시점·잘림 여부를 선언; old raw JSONL에서 0.290s gap도 관측되므로 신규 계약 기준을 증거 기반으로 설계.
6. **프로파일**: `STATIC_GRAVITY`와 `ROBOT_MOTION`을 분리. 후자는 실제 robot / tray accelerations·angular rates·speed profile을 기록하고 미래 운행 데이터가 RGB 모델 입력으로 누출되지 않도록 하며 기존 AI OFF 주행안전 코드를 수정하지 않는다.
7. **승인 경계**: `observation`/`rule_candidate`/`suggested_label`은 자동 계산 가능하나 `human_approved=false`, `ground_truth=NOT_OPERATOR_APPROVED`, `label_status=REVIEW_REQUIRED`. 0.015m는 DACON 비교 제안값이지 제품 확정 임계치 아님. 누적 tray 상대 이동, 순이동, 전도 각, 접촉 상실, 트레이 이탈 등의 독립 근거를 QA에서 재계산할 수 있도록 함. 결측·경계·충돌 사례는 UNKNOWN, 사람 승인 불가.
8. **출고**: `physics_observations_v2.jsonl`, `tray_pose_timeline.jsonl`, `contact_events.jsonl`, `camera_pose_metadata.json`, `capture_metadata.json`, `scenario.scenario.json`, `geometry_layout.json`, `trial_summary.json`, `SHA256SUMS`, source SHA/trial ID/scene ID/seed/physics profile + provenance. 기존 A13 파일명을 재사용하되 무손실 backward compatibility adapter 제시. 새 evidence bundle에 모든 관련 원본/타임 시계열 포함, B 수신 부분집합에도 QA 필수 메타데이터 누락하지 않도록 artifact manifest 작성.

## A14-P1 — 독립 물리 배치 및 시야 다양성 (P0 계약 통과 후)

- `physical_layout_id`, `geometry_family_id`, `environment_profile_id`의 provenance 정의. 동일 geometry family는 seed/jitter/렌더/카메라 변경이 있어도 split group 동일. `physical_layout_id`는 내용 기반 canonical hash. label과 무관하게 geometry/scene seed를 설계하며, 한 형태에서 STABLE/UNSTABLE 모두 가능한 경계 사례를 포함.
- 높이·접촉·지지면·편심·식기 개수·지름·두께·재질/마찰·초기 기울기·가림 등 조합을 명시적으로 변경. seed ±1mm jitter는 독립 레이아웃으로 절대 카운트하지 않음.
- 최소 smoke: 기존 장면 이외에 클래스별 새로운 **진짜 독립 geometry family 후보 1개 이상**, 동일 family에서 여러 seed를 적용했을 때 split group 하나로 유지. 이후 B 승인된 파일럿 규모(60장면·6 geometry family)는 **제안 목표**로 협의, 자동 gate로 고정하지 않음.
- 제품 카메라 640×480 단일 RGB 계속 유지. 연구용 2번째 시점은 별도 opt-in 센서·데이터로 허용하되 제품 입력 인터페이스에 강제하거나 C AI ON에 자동 전달하지 않음. `occlusion_status`는 자동 후보로 산출 후 사람 검토.
- 질량·마찰·외란처럼 이미지에서 직접 관측 불가한 물리 변수는 고정·프로파일 데이터로 명시하고 hidden confounder/shortcut leakage 위험을 B/C에 전달.

## QA 게이트/교육 보고

- L0: 스키마·SHA·시간 ns, frame/unit, quaternion, pose inverse/compose, stable/fall/UNKNOWN 합성 fixture, static vs motion 교차, contact sensor 없는 failure injection; 실제 실행 성공을 꾸미지 않음.
- L1: ROS2 Jazzy + Gazebo Harmonic bridge message availability, contact sensor server/topic, physics sampler smoke; hardcode된 미확인 topic·메시지형 금지.
- L2: 물리 source 변경 시 하나의 작은 `single` 장면에서 수집, sensor pose/time/contact/velocity 검수. 추가 신규 family 최소 1 ST/UN 이후 필요 시 4장면만 확장; 기존 성공한 A13 전체 4/4 재실행 억제.
- Owner L3: 실행 코드 immutable 40hex PIN, WSL2 GUI 기본, 필요 시 headless physics, 시각 검수는 사용자가 직접 수행하며 자동 게이트에서 제외. 비공개 진단 TAR.GZ+sidecar SHA·상세 CSV/JSON PASS/HOLD. `CI PASS != Owner L3 PASS`.
- 개발 단위마다 RED→GREEN→REVIEW→COMMIT, 신규 tests + GitHub CI, 교육 보고서·원본 증거 스키마/인터페이스 변경서, 기존 A/S7 AI OFF 회귀 무변경 보고서, Draft PR, main 미병합(사용자 승인 전).

## 금지

- A-13 원본 4/4 자동 라벨 승인, C 데이터 학습, B 데이터 release/GT threshold 확정, A/S7 Nav2/Collision Monitor 수정, 기존 물리 시험 무조건 반복, GitHub 공개 저장소에 민감 원본 업로드.
