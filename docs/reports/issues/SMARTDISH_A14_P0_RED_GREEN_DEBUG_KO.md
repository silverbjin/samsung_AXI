# A14 — RED→GREEN 물리 증거 디버깅·QA 이력

## 0. 재사용해야 하는 PASS

- A13 원본 WSL2 GUI ST-01/02 HELD / UN-01/02 FALL = 4/4 PASS.
- RGB 640×480×4, 기존 A13 RAW 88/88 SHA.
- B-Q01 원본 provenance PASS. B-Q03 상대/속도/Contact, B-Q04 human GT 등 HOLD.
- 카메라 SDF 정적 Pose는 B가 원본 authenticated TAR에서 검증했으므로 A에서 다시 제작하지 않음.

## 1. RED: 무엇이 누락됐습니까?

B QA `7048f7f01b6c9d03cae2c082a93af01dfc9a5531`:
`WORLD` Pose만 있고 트레이 상대 Pose 없음, Twist/Velocity 미측정, Contact/support 원본 없음, GT 사람 승인 0개. 배경 Class ST/UN은 실물 물리 상태를 관측했지만 승인 라벨은 아닙니다.

A13의 TF→Pose 기록은 일부 callback 시점 clock을 사용하므로 정확한 Gazebo 메시지 header 시간이 아닐 수 있습니다. A14에서 추가 `ROS_TF_HEADER_STAMP` 자료를 별도 기록하도록 합니다.

## 2. GREEN 변경의 최소성

- 원본 A13은 `--a14-static` 미지정 시 기존 코드 경로 그대로.
- opt-in 모드에서만 생성 SDF Contact System과 실제 sensor/bridge를 구성.
- 고정 tray SDF와 동적 식기 timestamp를 변환해 v2 생성.
- 직접 실측 Twist가 없으므로 DERIVED provenance 명시.
- contact heartbeat가 없으면 '미접촉' PASS가 아니라 HOLD.
- 사람이 승인하지 않은 후보를 자동 GT로 변경하지 않음.

## 3. 테스트 실패 시 분류와 조치

| 최초 오류 | 확인할 원본 | 다음 조치 |
|---|---|---|
| `A14_CONTACT_SYSTEM_PLUGIN_UNAVAILABLE` | Gazebo 실제 설치 plugin .so | Jazzy/Harmonic 설치 검수, 소스 변경 보류 |
| `A14_TF_HEADER_POSES_MISSING` | TF TransformStamped header stamp | header/timestamp bridge 오류 조사, callback clock 위장 금지 |
| `A14_POSE_GAP` | physics_observations_v2.jsonl | PosePublisher 주기/ROS callback 지연 분석 |
| `A14_CONTACT_NOT_VERIFIED` | contact_sensor_status.json, bridge logs | 콜리전 명칭·센서 활성화·DDS bridge 교차점 확인 |
| `A14_ORIGINAL_PHYSICS_SHA_MISMATCH` | 원본 SHA/시나리오 trial | 변조 금지·Fail-Closed |
| `A14_HUMAN_GT_BOUNDARY_VIOLATION` | metadata/approval_ledger | A 코드에서 승인 생성 금지 |

## 4. 교육용 RED-GREEN-REFACTOR 워크플로우

`RESEARCH → CONTRACT → RED (invalid fixture) → GREEN (pure math + measured data) → REFACTOR (minimal opt-in) → REVIEW (no auto-label) → COMMIT → L0/L1/L2 CI → OWNER WSL2`.

Cloud CI에서 L1/L2가 실패하면 해당 RUN의 status를 FAIL로 기록하고 근거 없이 성공으로 바꾸지 않습니다. 기존 A13 Owner PASS를 무효화하거나 재시험하지 않습니다.

## 5. 2026-11-25 실제 CI RED→GREEN 증거 (실험 SHA 구분)

| 실제 Run | 최초 근거 | 결과 및 조치 |
|---|---|---|
| #45572182408 | L0 25/25 PASS, L1 플러그인 경로 탐지 실패 | **HOLD**, ROS vendor 경로 조사 |
| #45572849986 | L0 PASS, L1 플러그인 패키지/파일 경로 불일치 | **HOLD**, ROS Jazzy vendor 플러그인 검색 |
| #45574049102 | L1 PASS, 실제 L2 Contact callbacks 0 | **HOLD**, Gazebo/ROS 그래프 증거 수집 |
| #45574964841 | 실제 SDF Contact Sensor가 /world/... 기본 토픽 발행, ROS Bridge는 /smartdish/tray/contact/... 구독 | **HOLD**, SDF의 <contact><topic>으로 수정 |
| #45575746576 | 실제 Contact 수신 성공, ST-02 식기 4,964~5,009건/트레이 5,032건, UN-01 식기 6,638~6,672건/바닥 6,690건 | **HOLD**, 과다 메시지 누적으로 버퍼 초과, 중복 상태만 축약 |
| #45577260183 | 실제 접촉 쌍 상태 축약 후 정상 샘플: ST 식기 200~201건/트레이 202건, UN 식기 194~196건/바닥 195건 | **Contact 계측 복구**, 그러나 ST 바닥/UN 트레이 콜백 없음 → CONTACT_DATA_INCOMPLETE, GT UNKNOWN/HOLD |

**핵심 원칙**: Gazebo 센서가 실제로 만든 토픽명과 bridge topic이 다르면 ROS publisher 항목이 존재해도 실제 ROS Contact callback은 0건입니다. 이 오류는 Gazebo Contact System 미설치가 아닙니다.

**버퍼 보존 계약**: 상태가 변하는 모든 실제 collision pair 시작/종료는 유지하고, 변화 없는 고주파 heartbeat만 50ms마다 1회 남깁니다. 원본 ROS callback 총수·전처리로 축약한 건수·capacity overflow를 따로 기록합니다. 이는 Contact 메시지를 조작한 것이 아니며, 기존 모든 콜백의 전체 raw bag을 보존한 것도 아닙니다. RAW ContactBag 저장은 추후 별도 관리가 필요합니다.

**P0 완결 범위**: 실제 상대 좌표/DERIVED velocity/Contact pair의 캡처와 provenance는 확보됐습니다. 그러나 아무 접촉이 없는 것으로 예상되는 특정 센서 토픽에서 callback이 없다는 사실만으로 그 센서를 “NO_CONTACT_OBSERVED”로 승격할 수 없습니다. 실제 증거 파일에는 `CONTACT_DATA_INCOMPLETE` / `rule_candidate=UNKNOWN` / `human_approved=false` / `quality_verdict=HOLD`를 그대로 유지합니다. **B의 GT 승인 0건, B-Q03/04 HOLD, Owner WSL2 아직 미검증, P1 NOT_STARTED**.

## 6. Cloud L2 검증의 분리

- **L2 real evidence capture gate**: 필요 장면(안정 ST-02=TRAY_DISH; 낙하 UN-01=FLOOR_DISH)의 실제 collision1/2 ID와 source timestamp 및 SHA와 트레이 상대 Pose/Velocity가 있으면 통과 가능.
- **GT candidate quality gate**: 다른 접촉 센서 채널이 메시지를 발행하지 않으면 해당 공백을 보존하고 UNKNOWN/HOLD. 이 둘은 한 지표로 합치지 않습니다.
- 수학/시뮬레이션/실제로 관측되지 않은 접촉을 채워 넣어 합격으로 위장하면 안 됩니다.
