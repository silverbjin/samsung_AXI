# A14-P0 — 물리 증거 QA 매트릭스 / PASS-HOLD 원장

| Gate | PASS에 필요한 실제 근거 | 미달시 |
|---|---|---|
| A14_SOURCE_SHA | HEAD exact SHA, scenario SDF 원본 SHA, 증거 SHA | HOLD |
| A14_TRAY_RELATIVE_POSE | SDF 고정 tray 확인 + 실제 header-stamped named Pose + 역변환 quaternion | UNKNOWN/HOLD |
| A14_VELOCITY_PROVENANCE | ns dt 양수, 두 연속 Pose, DERIVED m/s·rad/s 명기 | HOLD |
| A14_CONTACT_EVIDENCE | ROS↔Gazebo Contact Sensor 실제 callback + collision entity + topic/sensor 출처 | CONTACT_DATA_INCOMPLETE/HOLD |
| A14_TIME_ALIGNMENT | 실제 640×480 RGB t0 이전, Pose skew <=250ms, 최대 gap <=350ms, 관측 9s 이상 | INVALID/HOLD |
| A14_PHYSICS_TRACE_INTEGRITY | v2 + original RAW SHA + Contact RAW SHA + 포즈 누락 없음 | HOLD |
| A14_GT_CANDIDATE_REVIEW_REQUIRED | human_approved=false, ground_truth=NOT_OPERATOR_APPROVED, no approval_ledger.jsonl | PASS만 review 단계 |
| AI OFF protected | 기존 HOME→T03→DISH_RETURN→HOME 제어 파일 불변 | HOLD |
| ROBOT_MOTION | 실제 동적 tray pose/twist/accelerations 없음 | **설계만, NOT_RUN** |
| B-Q01 provenance | A13 기존 88/88, B QA SHA 유지 | A13 PASS 보존 |
| B-Q03/04 | 실제 상대·velocity·contact + 사람 라벨 검토 | 이 A14 작업만으로 B 전체 PASS 아님 |

## 상태 해석

- L0는 수학과 contract 위조 방지 검증.
- L1은 Jazzy/Harmonic 메시지와 실제 Contact System 플러그인 확인.
- L2는 실제 Gazebo ST-02/UN-01 단위 실험 1회씩.
- Owner L3는 실제 사용자 WSL2 기본 GUI, 독립 증거 수령 후 PASS 판정.

**중요:** CI PASS ≠ Owner WSL2 PASS. A는 승인 레저·학습 split·C 모델 학습을 하지 않습니다. 기준 0.015m는 DACON 비교 후보이며 B의 승인 전 임계치가 아닙니다.

## 향후 후속 오류 원장

서버 종료 SIGSEGV(-11)가 실제 관측 후 cleanup에만 나온다면 최초 계측 장애와 구별합니다. 센서 수집 중 충돌하거나 Pose/clock 역행이면 즉시 HOLD. 새로운 충돌·누락은 source_sha, 처음 실패한 시간, 원본 파일 SHA와 함께 별도 DBG 보고서로 남겨야 합니다.

## 2026-11-25 추가: Cloud 데이터 취득 계약과 GT 인수를 엄격히 분리

실제 Contact System과 bridge 경로는 Gazebo/ROS 토픽을 교차검증한 결과 정상 복구됐습니다. 하지만 Contact Sensor는 콜리전 이벤트가 없는 채널에서 메시지가 없을 수 있습니다.

| 독립 판정 | ST-02 | UN-01 | 근거 |
|---|---|---|---|
| 실제 RGB·Pose·시간·상대좌표·유도속도 | PASS | PASS | Gazebo L2 원본 및 SHA |
| Contact 원본 및 충돌 ID | TRAY_DISH 검수 | FLOOR_DISH 검수 | contact_events.jsonl 실제 수신 필요 |
| 미관측 Contact Sensor | tray_test_floor | tray_platform | callback 0건 = **부재/미접촉 미확정** |
| Contact 전체 품질 | DATA_INCOMPLETE | DATA_INCOMPLETE | per-topic callback 상태 |
| GT 후보 | UNKNOWN | UNKNOWN | 사람 승인 없음 |
| B 데이터셋 승인 | HOLD | HOLD | approval_ledger A가 생성 금지 |

CI에서 데이터 **취득 성공과 명시적 HOLD 처리**를 검증했다는 사실을 `P0 GT 승인 성공`으로 표시하지 마십시오. 다음 단계는 미관측 센서의 정상 동작을 독립적으로 증명할 수 있는 전용 교정/heartbeat 실험을 설계하는 것입니다. 그 이전에는 B-Q03/04 및 P1 확대를 시작하지 않습니다.
