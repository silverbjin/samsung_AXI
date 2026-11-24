# B-DEBUG-06 — 동시 수집·강제 중단 파일 잔재 방어

- 날짜: 2026-11-23 / 환경: Python 3.13.5, Pillow 12.3.0, pytest 9.0.2 (Linux 개발 컨테이너)
- 기준 SHA: `5d040cdae2f5414f531f4afdc86b073a21d3ecc5` (B-09)
- 상태: **RESOLVED (로컬 동일 경계)** / GitHub 신규 SHA CI 검사 별도
- 관련: [B-08R 개발 보고서](../tasks/2026-11-23_B-08R_writer_lock_orphan_recovery.md)

## 1. 현상 → 최초 실패

재현 파일: `tests/test_b_intake_recovery.py`의 오프라인 임의 색상 이미지/문자열 근거 (`TEST_ONLY`). 실제 안정성 라벨/모델 성능을 의미하지 않습니다.

```text
4 failed in 0.12s
FAILED test_staged_orphan_is_blocked_until_operator_quarantines
FAILED test_published_orphan_and_csv_temp_are_blocked_without_overwrite
FAILED test_second_writer_fails_fast_on_manifest_lock
FAILED test_keyboard_interrupt_after_image_move_is_detectable_on_next_run
```

- 기존 수집기는 동일 manifest를 두 번 읽고 쓰는 두 프로세스 간 충돌을 거부하지 않았습니다.
- 비정상 종료로 등록되지 않은 PNG 및 임시 CSV를 남긴 뒤에도 새로운 수집 시도가 이어질 수 있었습니다.

## 2. 가설과 확인

- 가설: 기존 B-08의 `os.replace`는 **CSV 한 파일** 원자성만 보장하며 read-modify-write 보호는 하지 않음 → 소스 확인으로 **채택**.
- 가설: `finally`가 비정상 종료마다 완전 복구함 → `KeyboardInterrupt` 주입 후 PNG 단독 잔존을 확인하여 **기각**.
- 최초 수정에서 포괄 고아 감지가 기존 `B_IMAGE_DEST_EXISTS_NOT_IN_MANIFEST` 에러를 대체 → 회귀 `1 failed` 확인, **에러 의미를 분리**하여 재수정.

## 3. 최소 조치·재검

- 동일 manifest 경로에 유지되는 `.b-intake.lock` 파일을 `fcntl.flock`으로 잠급니다. 잠금 실패면 `B_COLLECTOR_BUSY`; 잠금 파일 자체는 지우지 않습니다.
- 저장 중단 `B-*.png`, `.incoming-*`, `.b-csv-*` 등 **manifest에 없는 파일**을 탐지하고 `B_ORPHAN_FILES_DETECTED`로 차단합니다. 현재 대상 파일만 기존 `B_IMAGE_DEST_EXISTS_NOT_IN_MANIFEST`를 유지합니다.
- 원본 증거 보존을 위해 **자동 삭제 금지**. 관리자 검수 후 비공개 격리, 다시 등록.
- `pytest tests/test_b_dataset.py tests/test_b_tray_capture.py tests/test_b_intake_recovery.py`: **30 passed in 1.86s**. 실제 CLI 하위 프로세스 경합 검증 포함.
- GitHub PR #37 새 SHA Actions URL: 커밋 후 기록; 이 보고서 작성 시 `NOT_RUN`.

## 4. 훈련생 교훈과 한계

**배타 잠금은 동시 쓰기 순서를 보장하지만 물리적 정답 라벨의 사실성을 보장하지 않습니다.** PNG와 CSV는 둘을 묶는 트랜잭션이 아니므로 비정상 종료 뒤 고아 파일의 수동 복구가 필요합니다. DB/큐/새 ROS 런칭을 도입하지 않은 이유는 B 담당 데이터 수집의 최소 실패 경계만 보완하면 되기 때문입니다.
