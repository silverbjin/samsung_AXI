# B-DEBUG-03 — 데이터 등록 후 근거 원본이 바뀌어도 재검 PASS

- 최초 재현: 2026-11-23 / Python 3.13.5, Pillow 12.3.0, pytest 9.0.2 (로컬 개발 컨테이너)
- 상태: **RESOLVED (로컬 동일 경계)** / GitHub CI 별도 확인
- 기준 SHA: `1bfc19eabe07f2a0ea8c5c8ba3509491c9dd217d`
- 작업: [B-07](../tasks/2026-11-23_B-07_evidence_reaudit.md)

## 1. 최초 실패와 재현

`collect()`로 실제 파일 경로 및 SHA 기록 → 관측 로그 내용을 바꾼 뒤 `prepare_dataset.validate()` 재호출.

```text
BEFORE 1
AFTER_MUTATION_INCORRECT_PASS 1
```

동일 이미지의 SHA는 변경되지 않았으므로 기존 데이터 검사 함수가 실제 근거 로그 변조를 감지하지 못했습니다. 이 문제는 Gazebo 센서 실패가 아니라 **오프라인 데이터셋 증거 무결성 경계**의 누락입니다.

## 2. 진단: 사실/가설 구분

- 확인: `collect_tableware.py`는 `capture_config.physics_evidence_sha256`과 크기를 기록합니다.
- 확인: 기존 `prepare_dataset.py`는 `capture_config`가 JSON 객체인지 확인하지만 해당 SHA를 재검하지 않았습니다.
- 원인 확정: 등록 시 해시를 저장해도 **재사용 시** 검증이 빠진 것.

## 3. 최소 조치와 재검

- 변경: `prepare_dataset.validate()`의 `PHYSICS_OBSERVED` 행만 evidence path/size/sha 재검. 헤더·split·C 추론 코드는 불변.
- 동일 경계 GREEN: 변조 → `B_PHYSICS_EVIDENCE_SHA_MISMATCH`, 삭제 → `B_PHYSICS_EVIDENCE_MISSING`; 4개 추가 pytest 포함 **19 passed**.
- 오류 코드가 분리되어 운영자가 '이미지 누락'과 '관측 근거 누락'을 구별할 수 있습니다.
- 실물 관측 정확성/학습 성능: **NOT_RUN**.

## 4. 훈련생 교훈

등록 시점 검증과 학습 시점 검증은 다른 경계입니다. 데이터 파일이 바뀔 수 있는 작업에서는 출고 직전에도 근거의 해시를 다시 확인해야 합니다. 하지만 SHA 일치는 **무결성**이지 **사실성**이 아닙니다.
