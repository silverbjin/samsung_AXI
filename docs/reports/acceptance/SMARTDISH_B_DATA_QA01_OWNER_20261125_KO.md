# SmartDish B-DATA-QA-01 — 사용자 WSL2 진단 검수 및 수정 후 판정

- 실행일: 2026-11-25 (첨부 생성 UTC 07:32:27)
- Owner 실행 SHA: `ff1e2e2c32f8d3f53df3352b1bc0601a003d0b81`
- 진단 TAR: `b_dacon_qa01_diagnostics.tar.gz`, 외부 SHA `483c859767566d1d46bd7da07014dd1dfcda7f0804b9b833c33136cc81bc0dbe` 일치
- 내부 SHA256SUMS **12/12 PASS**, TAR 정규 멤버 13개, 비정규 멤버 0
- `diagnostic_status.json`: `AUDIT_COMPLETED`, `exit_code=0`, `quality_verdict=HOLD`, `automatic_approval=false`, `training_executed=false`
- `qa_report.json`: baseline v1.0 / 기존 원본 A13 SHA 88개 확인 / 후보 4건 / 운영자 승인 0건·검토결정 0건.

| Gate | 사용자 원본 실행 | B DBG-01 수정 후 ChatGPT Linux 직접 재검 | 수용 근거/잔여 조건 |
|---|---|---|---|
| B-Q01 | PASS | PASS | 실제 원본 SHA 및 내부 88/88 |
| B-Q02 | HOLD | HOLD | 원본 A13 SDF 정적 카메라 설정 포즈 4/4 확인; 가림·시야/관측성 사람 승인 필요 |
| B-Q03 | HOLD | HOLD | 실제 JSONL은 World Pose 중심, tray-relative pose/velocity/contact 부족 |
| B-Q04 | HOLD | HOLD | human APPROVED 0, 독립 GT 규칙 없음 |
| B-Q05 | HOLD | HOLD | 4개 고정 장면, 형상/클래스/환경 교차 미검증 |
| B-Q06 | HOLD | HOLD | 승인 split 없음, near duplicate 검토 대기 |
| B-Q07 | HOLD | HOLD | B 승인 manifest 및 C release 없음 |

## 원본에 기록된 실제 통계

- RGB 4건 640×480, `capture_s=0.6`, 가장 가까운 관측 Pose 0.55s (50ms 차이)
- world-frame `max_cumulative_world_translation_m` ST-01=0.000130 / ST-02=0.000110 / UN-01=0.743370 / UN-02=1.246708. **정답·tray-relative 값 아님**.
- 개별 Pose sample 203~204개씩. 장면에 따라 최대 관측 간격 0.290s(일부 dish), 0.231s, 0.236s 등; 정량 규칙을 만들기 전에 샘플링 계약 확인 필요.
- `camera_metadata.csv` 사용자 원본 파일에서는 4건 모두 `camera_pose_source=MISSING`. 실제 A13 전체 원본 TAR에 원래 존재하며 B QA 코드의 부분집합 탐색 결함이었음. 수정 후 `VERIFIED_A13_TAR_SENSOR_PREFLIGHT_SDF`로 재검, 4/4 Pose/Topic/Frame/Width/Height 일치. 정적 포즈일 뿐 동적 TF 실측은 아님.
- original B QA file/pixel exact image duplicates 0; 8×8 aHash 유사 후보 2쌍. 삭제·중복 라벨 자동 확정 금지.

## PASS/HOLD 계약

- Owner **기존 SHA 실행·산출물 무결성 PASS** (B-DATA-QA-01 감사 작동 정상).
- 수정 B 코드 테스트 및 새 SHA의 GitHub B CI 별도 확인. 수정 코드의 **Owner WSL2 실제 실행은 NOT_RUN**이며 과거 Owner 성공으로 대체하지 않음.
- A14는 새 물리 증거 계약 선행, seed 반복으로 독립 scene 개수 늘렸다는 주장 금지. B13 라벨 승인/학습 출고 자동 수행 금지.
- 전체 S7/A13 물리 재실행 반복 금지; 기존 증거 재사용.

## 수정 후 추가 확인

- 실물리 원본 TAR를 직접 읽은 정적 SDF 4개 카메라 설정 포즈·640×480·ROS topic/optical frame 일치 확인.
- `B_Q02_CAMERA_POSE_MISSING` 사라짐; `B_Q02_OCCLUSION_VISUAL_QA_NOT_SIGNED`만 잔여.
- 60장면 권고 미달은 **nonbinding advisory**로 분리, B-Q05 HOLD는 교차 형상/환경 미증명 때문.
- 기존 `STABLE=2, UNSTABLE=2`은 자동 추천일 뿐 사람이 승인한 라벨이 아님. Approval ledger 여전히 NOT_PRESENT.
