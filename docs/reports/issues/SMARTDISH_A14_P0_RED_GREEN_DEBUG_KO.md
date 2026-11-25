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