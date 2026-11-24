# SmartDish B-08R — B-08 후속 동시 등록 잠금·중단 잔재 감지

- 날짜: 2026-11-23 KST
- 범위: **B 담당 오프라인 수집기** `ai/scripts/collect_tableware.py`, `ai/data/.gitignore`, 경량 pytest, 교육 문서
- 출발 기준: B-09 `5d040cdae2f5414f531f4afdc86b073a21d3ecc5` / [Draft PR #37](https://github.com/silverbjin/samsung_AXI/pull/37)
- 판정: **로컬 Python 계약 30 PASS** / 이 보고서 작성 당시 새 HEAD GitHub CI `NOT_RUN` / ROS·Gazebo 트레이 실제 입력 `NOT_RUN`
- 문제 보고서: [B-DEBUG-06](../issues/2026-11-23_B-DEBUG-06_concurrent_orphan_recovery.md)

## 1. 왜 다시 점검했습니까?

이미 병렬 개발된 B-08은 **파일 이름 충돌과 CSV 부분 쓰기**를 개선했지만, 2개의 수집 CLI가 동시에 기존 manifest를 읽고 한 행씩 쓰는 경우 **나중 쓰는 행이 앞선 행을 덮을 수 있는 경계**와, 비정상 종료로 남은 `.incoming-*` / `B-*.png` / `.b-csv-*`를 **다음 실행에서 알려주는 경계**는 구현되어 있지 않았습니다. 이는 물리 라벨의 정확성과는 구별되는 데이터 **등록 완전성** 문제입니다.

## 2. 수정 및 왜 이 방법인가

| 파일 | 최소 수정 | 설계 이유 |
|---|---|---|
| `ai/scripts/collect_tableware.py` | `fcntl.flock(..., LOCK_EX|LOCK_NB)`로 동일 manifest **수집기 간 배타 잠금**, 충돌 시 `B_COLLECTOR_BUSY` | Ubuntu/WSL2 MVP 단일 파일 동기화; DB·큐·임의 sleep 불필요 |
| 동일 파일 | 원본 CSV에 없는 `B-*.png`, 중단된 `.incoming-*`, `.b-csv-*` **탐지 후 등록 차단** | 강제 종료의 원본 증거를 자동 삭제하지 않음. 기존 `B_IMAGE_DEST_EXISTS_NOT_IN_MANIFEST` 의미 보존 |
| `ai/data/.gitignore` | `.b-intake.lock` 무시 | 실행 잠금 파일의 무단 Git 추적 방지. inode 경합을 막도록 잠금 파일은 삭제하지 않음 |
| `tests/test_b_intake_recovery.py` | 실패 주입 5개(대기 잔재, 미색인 PNG·CSV, 락 충돌, KeyboardInterrupt, **실제 두 번째 프로세스**) | 단일 함수 모킹만으로는 CLI 프로세스 경계를 입증하지 못함 |
| `.github/workflows/smartdish-b-dataset-ci.yml` | 기존 pytest 목록에 신규 테스트 모듈 추가 | 기존 ROS/Gazebo를 반복하지 않고 B 데이터 경계만 재검 |

**중요 한계:** PNG 저장과 manifest 교체는 두 파일에 걸친 단일 원자 트랜잭션이 **아닙니다**. 프로세스 강제 종료 시 PNG만 남을 수 있습니다. 재실행에서 이를 `B_ORPHAN_FILES_DETECTED` 또는 동일 대상의 `B_IMAGE_DEST_EXISTS_NOT_IN_MANIFEST`로 검출하고 **사람이 비공개 격리 공간에 이동해 원본을 보존**한 후 재등록하도록 합니다. 자동 삭제·무단 복원은 하지 않습니다. `flock`은 이 수집기를 사용하는 Ubuntu/WSL2 프로세스 사이에만 유효하며 다른 도구가 CSV를 임의 수정하면 막지 못합니다.

## 3. RED → GREEN, 기대와 관찰

```bash
python3 -m compileall -q ai/scripts tests/test_b_dataset.py tests/test_b_tray_capture.py tests/test_b_intake_recovery.py
python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py tests/test_b_intake_recovery.py
```

- 수정 전: 신규 실패 주입 **4 failed**. 임시 이미지/미색인 PNG를 둔 상태에서 등록을 허용, 잠금 중에도 등록, 강제 중단 직후 다른 시도에서 고아 파일 탐지 실패.
- 수정 후 첫 회귀: **28 passed, 1 failed** — 기존 `B_IMAGE_DEST_EXISTS_NOT_IN_MANIFEST` 테스트가 새 포괄 오류로 바뀐 것을 발견. 기존 에러 의미 보존을 위해 대상 PNG만 기존 오류에 남기고 나머지 잔재를 신규 경고로 분리했습니다.
- 수정 후 확정: **30 passed in 1.86s** (기존 25 + 신규 5). 별도 subprocess에서 `B_COLLECTOR_BUSY` 및 락 해제 후 정상 등록 확인.
- 계약 fixture: `B_DATASET_CONTRACT_PASS`, 6건 모두 `MOCK_ONLY`; 기본 모드에서는 `B_GROUND_TRUTH_NOT_OBSERVED row=2` 거부 확인.
- GitHub 신규 SHA CI: 개발 직후 `NOT_RUN`; [PR #37](https://github.com/silverbjin/samsung_AXI/pull/37) 체크 및 Actions 실행에서 최종 결과 확인하여 PR 기록에 반영합니다.

## 4. 실제 운영·중단 시 복구

`B_ORPHAN_FILES_DETECTED`가 나오면 **등록 중지 → manifest에 실제로 없는 파일 판별 → `ai/data/private/quarantine/`로 수동 이동 → 원본 SHA/이유 기록 → 재실행** 순서를 따릅니다. 이름만 보고 자동 `rm`하는 복구 스크립트는 제공하지 않습니다. `B_COLLECTOR_BUSY`는 다른 실행이 같은 manifest를 사용 중임을 뜻하므로 종료 여부를 확인한 뒤 재시도합니다. `.b-intake.lock` 파일은 프로세스가 사라지면 커널 잠금이 해제되므로 제거하지 않습니다.

## 5. 인수 범위와 교육 포인트

- PASS 가능한 범위: 오프라인 파일/CSV 계약, 실제 별도 CLI 프로세스 락 및 실패 검출, MOCK_ONLY 차단.
- NOT_RUN: A 전용 트레이 카메라, Gazebo 10초 물리 관측, 실제 승인 라벨, C 모델 학습 및 WSL2 실센서 인수.
- 훈련생 질문: (1) atomic CSV와 두 파일 트랜잭션은 왜 다릅니까? (2) 충돌 시 대기보다 명시적 실패가 안전한 상황은? (3) 고아 파일을 바로 삭제하지 않는 이유는?
- 다음 경계: A 이미지 및 사람이 검수한 물리 증거를 1건 확보하기 전에는 실데이터 성능 PASS를 주장하지 않음.
