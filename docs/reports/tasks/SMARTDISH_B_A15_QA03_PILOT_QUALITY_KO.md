# B-QA03 — A15 Owner 물리 파일럿 독립 QA 검수기 교육·개발 보고서

## 0. 상태와 증거 구분 (2026-11-26)

- **코드 및 합성 계약 시험**: `ai/scripts/audit_b_a15.py`, `ai/scripts/b_a15_qa_cli.py`, `tests/test_b_a15_audit.py`, `scripts/smartdish_b_a15_qa_one_shot.sh` 개발. 신규 로컬 테스트 **25/25 PASS**. 이 테스트는 **fixture**이며 물리 인수 증거가 아니다.
- **실제 A15 Owner 원본 재검**: **NOT_RUN — 필수 `a15_pilot_evidence.tar.gz` / `.sha256` 바이트가 이번 작업 컨테이너에 없음**. 연결된 개인 Library에는 과거 별도 확인 JSON이 있으나 그것을 새 원본 재계산으로 가장할 수 없다.
- **이전 A15 Owner 보고서 (2차 근거)**: [원본 Owner 인수](https://github.com/silverbjin/samsung_AXI/blob/ea68e96710b62e982308fe740afeeba6081fd551/docs/reports/acceptance/SMARTDISH_A15_OWNER_20261126_KO.md)에는 SHA `828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05`, outer15/15, inner64/64, data 4/4 GUI 4/4, server -11 네 장면, all-owned stopped, GT UNKNOWN_HOLD / human approval 0으로 기록되어 있다. 이전 검증을 부정하지 않으나 본 B 검수 직접 PASS로 재분류하지 않는다.
- **GT/학습 출고**: HOLD, approval_ledger 없음, `training_eligible=false`, B-Q01~Q07는 **이번 B 직접 원본이 확인될 때까지 전부 HOLD**.

## 1. 실제 A15 생산 스키마 연구

A15 생산 코드 `scripts/a15_pilot_batch.sh`, `scripts/a15_pilot_collect.py`, `scripts/a15_pilot_contract.py`, `scripts/a15_pilot_world.py`를 정확한 A15 실행 SHA에서 직접 확인하였다. 바깥 TAR에는 `batch_status.json`, 4×(`a15_raw.tar.gz` + sidecar), log 및 SHA256SUMS가 있고, 내부에는 `a15_design.json`, `capture.json`, `initial_validity.json`, `verdict.json`, `tray_rgb_t0.png`, `poses.tsv`, `trigger.tsv`, `ecm_contact_steps.tsv`, `ros_contacts.jsonl` 등이 있다. 정확한 두 단계 15+64 해시가 확인되어야 물리 재계산에 진입한다.

## 2. 왜 1ms Pose와 Contact 모두 검수해야 하는가

```mermaid
flowchart TD
    A[WSL2 A15 원본 TAR + sidecar] --> B{Owner SHA / outer 15 / inner 64 PASS?}
    B -->|아니오| H[모든 B-Q 게이트 HOLD, 진단 생성]
    B -->|예| C[RGB(t0) PNG / CameraInfo / 정착 / support]
    C --> D[동일 iteration 1ms 4개 Entity Pose]
    D --> E[tray inverse · 누적 이동 · 회전 · t0-12.3s]
    E --> F[500-step torque command, 4-topic ECM refresh]
    F --> G[ROS exact-stamp positive pair subset 비교]
    G --> I[리뷰용 보고서 / 사람 결정 공란]
    I --> J[B-Q01 PASS, 나머지 HOLD: 승인·출고 금지]
```

1ms 4-entity Pose의 완전한 시간 격자를 확인하고, `inverse(T_world,tray) × T_world,dish`를 직접 계산한다. 첫 200ms 정착, t0 exact, tray footprint, quaternion 정규화 및 동일 iteration을 엄격히 검증한다. 상단 식기의 최대 변위·누적 경로·최종 순변위·회전을 재계산하고 A `verdict.metrics`와 오차 ≤2e-7 단위로 대조한다. `0.015m`는 DACON 비교 후보이지 확정 제품 임계치가 아니다.

이후 `trigger.tsv`의 world-Y 0.12Nm 명령(2.200–2.699s, 500×1ms)을 검증한다. 이는 실제 **측정 wrench가 아니라 명령**이다. Gazebo ECM 4 topic의 (t0,end] 1ms refresh는 ROS callback 100% 수신의 증거가 아니다. 동일 timestamp의 positive pair 부분집합만 비교하며 silent channel을 정상 contact로 오판하지 않는다. `production_contact_health=HOLD` 유지.

## 3. 물리 PASS와 서버 teardown FAIL을 분리하는 이유

A15는 실제 데이터·GUI를 네 장면 모두 취득했어도 서버 종료 -11이 기록되었다. 이것은 유효한 기존 물리 데이터를 무효화하거나 반복 실험을 요구하는 근거가 아니며, 동시에 정상 cleanup으로 표시할 수 없다. B 결과에 `data=PASS (previous Owner) / cleanup=FAIL / production contact=HOLD / product release=HOLD`를 각각 기록한다.

## 4. RED → GREEN 검수기 개발 이력

- RED 사례: 해시 조작, 상대 TAR 경로 이탈, symlink, 압축 멤버 중복, `approval_ledger.jsonl` 삽입, t0 Pose 1ms 누락, t0 전 움직임, 초기 트레이 외부, 잘못된 quaternion, contact 1ms 누락, 접촉 pair 부재, 잘못된 외란 명령.
- GREEN: 각 독립 함수를 실제 fixture 입력으로 호출한 로컬 테스트 **25/25 PASS**. 원본 없음 또는 잘못된 SHA에서 결과·진단 TAR는 만들되 `actual_owner_raw_directly_recomputed=false` 및 전 게이트 HOLD로 Fail-Closed. 코드는 실제 A15 원본 TAR를 받아야만 실물 원장을 PASS할 수 있음.
- 고정된 `scene_id`/편심/파일명으로 자동 안정·불안정 분류하지 않는다. `review_worksheet.csv`의 human decision·reviewer·license 칸은 비워 둔다.
- 이미 제출된 Cloud artifact와 Owner가 같은 geometry/layout을 공유하면 서로 다른 독립 샘플 8개로 계산하지 않는다.

## 5. 새 WSL2 QA 사용법 (Gazebo 재실행 불필요)

`git` HEAD가 **신규 QA03 최종 SHA**인 깨끗한 독립 checkout에서 CPU만 사용한다.

```bash
# exact final SHA 및 기존 보관된 실제 A15 Owner TAR 경로를 설정
export SMARTDISH_B_QA03_SOURCE_SHA=<커밋된_실제_SHA_40자리>
OWNER="$HOME/실제_A15_OWNER_OUTPUT/a15_pilot_evidence.tar.gz"
OUT="$HOME/qa03_private_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/smartdish_b_a15_qa_one_shot.sh --owner "$OWNER" --out-dir "$OUT"
```

결과는 `qa_report.json`, 별도 사람 검토 공란 `review_worksheet.csv` (원본 PASS 경우에만), `b_a15_qa03_diagnostics.tar.gz` + `.sha256`이다. 원본 TAR나 물리 원본 이미지 자체는 진단에 자동 넣지 않는다. 현 GUI/ROS/렌더러 변경, A14/A15 시뮬레이션 재수집, 제품 main 병합을 수행하지 않는다.

## 6. 교육 포인트 및 분명한 차단 조건

- `CI PASS ≠ Owner raw PASS ≠ Human GT 승인 ≠ C 학습 가능`.
- QA03 첫 실패 경계는 **Owner 원본 TAR 및 sidecar의 실제 접근성**이다. Owner 검수 JSON/Cloud ZIP/합성 fixture/기존 A 보고서만으로 QA03의 `actual_owner_raw_directly_recomputed=true`를 기록하지 않는다.
- 독립 형상 계열은 2, 실제 배치 4만 이전 Owner에 기록되어 있다. 4 장면 또는 반복 Cloud/Owner 8 장면으로 train/valid/test split 해선 안 된다.
- 기존 B 147개 테스트는 수정하지 않으며 전용 scope CI와 공통 baseline, merge 차단 정책을 유지한다.
