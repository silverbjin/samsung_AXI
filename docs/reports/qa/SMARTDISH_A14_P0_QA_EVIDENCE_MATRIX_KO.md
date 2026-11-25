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