# B-08 — 단일 운영자 데이터 등록의 파일/CSV 원자성 보강

- 날짜: 2026-11-23 KST
- 이전 기준 HEAD: B-07 `ed90b1aa991cc5dab983ba001eaf1e5d41d99411`
- 상태: **로컬 데이터 계약 PASS / GitHub CI 후속 재검 / 실제 물리 데이터·Gazebo/WSL2 NOT_RUN**
- 연관 문제: [B-DEBUG-04](../issues/2026-11-23_B-DEBUG-04_orphan_ingest.md)

## 왜 구현합니까?

기존 `collect_tableware.collect()`는 manifest가 없더라도 이미 `.incoming.png`를 작성한 뒤 파일 읽기에서 실패했습니다. 실패 후 잔재가 남으면 다음 학생이 잘못된 파일을 관측 이미지로 사용할 위험이 있습니다. 따라서 데이터가 아직 0건인 지금 입력 및 저장 경계를 좁혀 파일/CSV 불일치 상태를 예방했습니다.

## 최소 변경과 설계 이유

| 파일 | 수정 | 선택한 이유 |
|---|---|---|
| `ai/scripts/collect_tableware.py` | CSV 헤더/행을 **이미지 생성 전** 읽기. 유일 임시 파일 `.incoming-*` 생성. 중복 해시/미색인 대상 파일 확인. CSV 저장 예외 시 새 이미지 롤백 | 원본 데이터 보존, 실패 위치를 앞당김 |
| `ai/scripts/prepare_dataset.py` | `write_csv()`에서 완성된 새 임시 CSV를 같은 폴더에 작성한 뒤 `os.replace`로 교체하고 임시 파일 정리 | 중단 시 기존 manifest의 부분 쓰기/손실 방지 |
| `tests/test_b_dataset.py` | manifest 누락, CSV 저장 실패, 미색인 PNG 덮어쓰기, CSV 직렬화 실패 방어 4개 | 결함 최초 경계를 직접 재현 |

동일 브랜치에서 기존 label_map/CSV 컬럼/분할 정책·C 모델·A 주행·D UI를 변경하지 않았습니다. 동시 다중 작성자에 대한 파일 lock이나 DB는 MVP 범위 밖이며, **한 명의 데이터 운영자**가 CLI를 순차 호출합니다.

## 기대와 실제 관찰

```bash
python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py
python3 -m compileall -q ai/scripts tests/test_b_dataset.py tests/test_b_tray_capture.py
```

- RED: 존재하지 않는 manifest 경로를 전달하면 `FileNotFoundError` 이후 `B08_BEFORE_ORPHAN_TMP True` 확인.
- GREEN: 동일 입력에서 `ai/data/images` 자체가 생기지 않으며, 의도적으로 `write_csv` 오류를 발생시켜도 원본 CSV와 기존 이미지가 보존되고 `.incoming-*`가 남지 않습니다.
- 로컬 회귀: 기존 19개 + 신규 4개 = **23 passed in 0.30s**.
- GitHub CI 원본 Run: 코드 커밋 이후 확인; 작성 시 **NOT_RUN**.
- 실제 A 센서/데이터·C 실학습: **NOT_RUN**. `MOCK_ONLY` 테스트를 물리 데이터 성능으로 대체하지 않았습니다.

## 주니어용 질문

왜 원본 파일의 존재·해시뿐만 아니라 **실패한 작업 이후 파일이 그대로 남는지**도 확인해야 합니까? 왜 이 작은 프로젝트에 DB 대신 atomic rename과 롤백을 선택했습니까?
