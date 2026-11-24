# B-07 — 물리 관측 증거 재검증과 C 인계 무결성

- 날짜: 2026-11-23 KST
- 기준: B Draft PR #37, 작업 전 HEAD `1bfc19eabe07f2a0ea8c5c8ba3509491c9dd217d`
- 상태: **로컬 데이터 계약 PASS / GitHub CI 재검 필요 / 실제 물리 영상 및 모델 학습 NOT_RUN**
- 연관 이슈: [B-DEBUG-03](../issues/2026-11-23_B-DEBUG-03_evidence_drift.md)

## 목적 — 왜 지금 고쳤습니까?

B-06은 등록 **시점**의 근거 파일 존재/해시만 확인했습니다. 그러나 등록 후 로그가 바뀌거나 사라져도 `prepare_dataset.validate()`는 이미지 SHA만 점검하여 학습 인계까지 진행할 수 있었습니다. 출고 시점에도 물리 증거 원본이 동일한지 확인하도록 데이터 준비 경계 한 곳만 강화했습니다.

## 변경 내용

| 파일 | 기능/결정 |
|---|---|
| `ai/scripts/prepare_dataset.py` | 실제 라벨 행에 한해 evidence 메타데이터·파일 존재·크기·SHA-256·이미지와 분리 여부 재검증. 보고서에 `evidence_hash_verified` 기록 |
| `tests/test_b_dataset.py` | 원본 근거/동일 크기 변조/삭제/메타데이터 누락 경계 4건 추가 |
| `ai/docs/DATASET_CARD_KO.md`, `ai/docs/B_DATA_USAGE_KO.md` | C에 인계 전 증거 무결성 재검 기준과 오류 코드 추가 |

기존 CSV 필드 및 `STABLE=0`, `UNSTABLE=1` 계약은 수정하지 않았습니다. `MOCK_ONLY` 여섯 단색 샘플은 증거 검증 대상이 아니며 기본 경로에서 계속 차단됩니다. 자동 물리 안정성 판정, 비전 학습, 카메라/주행 코드는 변경하지 않았습니다.

## RED → GREEN 실행 및 기대와 관찰

```bash
python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py
python3 -m compileall -q ai/scripts tests/test_b_dataset.py tests/test_b_tray_capture.py
# 기존 단색 임의 fixture는 --allow-fixtures 없이 검증 시 실패해야 정상
```

- 기존 버전 재현: 이미지 등록 이후 물리 관측 로그를 수정했음에도 `validate()`가 **1건 PASS**(의도하지 않은 동작).
- 수정 후: 증거 SHA가 바뀌면 `B_PHYSICS_EVIDENCE_SHA_MISMATCH`, 삭제하면 `B_PHYSICS_EVIDENCE_MISSING`, 필수 메타데이터 누락이면 `B_PHYSICS_EVIDENCE_METADATA_INVALID`로 실패.
- 로컬 관찰: **19 passed in 0.26s**. 기존 15 + 4 단위 테스트. `MOCK_ONLY` fixture 6건에서 `evidence_hash_verified=0`, 기본 모드는 `B_GROUND_TRUTH_NOT_OBSERVED row=2` 거부 유지.
- GitHub Actions: 보고서 작성 시 **NOT_RUN**; 후속 원격 Run 링크를 별도 후속 커밋 또는 PR에 기재.
- 실제 A Gazebo 트레이 RGB / 실제 안정성 ground truth / C 실학습: **NOT_RUN**.

## 교육·한계

경로 문자열 검사는 파일이 있다는 사실만 확인합니다. 해시는 데이터가 변경되지 않았음을 확인하지만 **물리 판단이 사실인지**는 증명하지 못합니다. 직접적인 관측/검토가 없는 데이터는 파일 검증 PASS라 해도 학습 데이터로 승인하면 안 됩니다. 영상 같은 대용량 원본은 GitHub에 넣지 않고 로컬 또는 허가된 별도 저장소에 보존합니다.

- 다음 경계: B-08 — 파일 수집 오류 시 원본 이미지·CSV 불일치 발생을 차단하는 최소 원자적 입력 검증.
