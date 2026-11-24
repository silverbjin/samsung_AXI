# B-DEBUG-04 — manifest 누락 시 이미지 임시 파일 잔재 발생

- 날짜: 2026-11-23 / Python 3.13.5 + Pillow 12.3.0 + pytest 9.0.2
- 상태: **RESOLVED (로컬 동일 경계) / 원격 CI 후속 확인**
- 기준: B-07 `ed90b1aa991cc5dab983ba001eaf1e5d41d99411`
- 관련 개발: [B-08](../tasks/2026-11-23_B-08_atomic_intake.md)

## 1. 증상/최초 실패

기존 `collect()`에 정상 이미지·실존 증거 파일과 미존재 CSV manifest를 입력했습니다.

```text
FileNotFoundError: missing_manifest.csv
B08_BEFORE_ORPHAN_TMP True
```

파일 읽기 실패가 발생하기 전 `ai/data/images/.incoming.png`를 만들었기 때문에 실패 후 잔재가 남았습니다. 데이터가 등록됐다는 뜻은 아니지만 학생이 잘못 재사용할 여지가 있습니다.

## 2. 원인과 최소 수정

- 확인된 원인: 기존 이미지 임시파일 저장 → `load_manifest` 순서였고 예외에 대한 임시파일 정리가 없었습니다.
- 수정: `load_manifest`를 이미지 출력 앞에 이동. 임시파일을 유일한 이름으로 저장하고 `finally`에서 정리. 중복/미색인 원본 덮어쓰기 방어 및 CSV 실패 시 새 파일 롤백.
- CSV helper는 같은 디렉터리에서 완성한 임시 파일만 `os.replace`하여 원본 truncation 위험을 제거했습니다.
- 배제: Redis lock/DB/다중 프로세스 동시 입력 큐 도입 — 단일 운영자 MVP에 불필요합니다.

## 3. 동일 경계 재검

- manifest 누락 → 이미지 디렉터리 생성되지 않음.
- 강제 CSV 오류 → 기존 CSV 동일, 신규 PNG/임시파일 없음.
- 미색인 기존 PNG → `B_IMAGE_DEST_EXISTS_NOT_IN_MANIFEST`로 거부, 원본 bytes 동일.
- 불량 CSV row → 예외 후 원래 CSV 동일, 임시 CSV 없음.
- `python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py` → **23 passed in 0.30s** (로컬 개발 환경).
- GitHub CI/실제 카메라: **NOT_RUN** (이 보고서 작성 시점).

## 4. 교훈과 한계

오류를 포착하는 것과 실패했을 때 데이터 상태를 **복구**하는 것은 다릅니다. 원자적 쓰기는 기존 CSV 보존에 도움이 되지만 여러 운영자가 동시에 같은 CSV에 쓰는 분산 동기화는 해결하지 않습니다. MVP 범위에서는 단일 프로세스/한 운영자가 순차 수집하는 조건을 명확히 유지합니다.
