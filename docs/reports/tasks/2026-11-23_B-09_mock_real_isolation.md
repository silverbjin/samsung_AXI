# B-09 — 더미·실제 물리 데이터 혼입 차단

- 날짜: 2026-11-23 KST
- 이전 HEAD: B-08 `c9c528072f76b8b2dbc1119ead770d23308ffda0`
- 판정: **로컬 데이터 계약 PASS / 원격 CI 재검 필요 / 실제 안정성 데이터·C 학습 NOT_RUN**
- 이슈: [B-DEBUG-05](../issues/2026-11-23_B-DEBUG-05_mock_real_mix.md)

## 목적 / 첫 실패

B의 `--allow-fixtures`는 형식 확인용 단색 mock에만 허용돼야 합니다. 그런데 `PHYSICS_OBSERVED` 행과 `MOCK_ONLY` 행을 함께 전달해도 검증이 통과하면서 `data_scope=MOCK_ONLY`와 7개 행으로 보고됐습니다. C에게 혼합된 split CSV를 넘길 수 있는 조건이므로 실제 데이터가 투입되기 전에 분리했습니다.

## 작업 / 왜 이렇게 수정했습니까?

- `ai/scripts/prepare_dataset.py`: `allow_fixtures=True` 경로는 **MOCK_ONLY / CONTRACT_FIXTURE 전용**으로 한정합니다. 실제 row가 들어오면 `B_FIXTURE_MODE_REAL_DATA_FORBIDDEN`으로 즉시 실패합니다. 실데이터는 반드시 기본 경로(플래그 없음)에서 통과시킵니다.
- `tests/test_b_dataset.py`: 혼합 행과 실데이터만 있는 fixture 모드를 모두 거부하는 테스트 2건 추가.
- 별도 C 모델·ROS 메시지·라벨/CSV 필드 변경 없음. 데이터 레이크/별도 MLOps, 임의 합성 물리 라벨 학습을 도입하지 않았습니다.

## 로컬 검증과 실제 관찰

```bash
python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py
python3 -m compileall -q ai/scripts tests/test_b_dataset.py tests/test_b_tray_capture.py
```

- RED: 6개 임의 단색 fixture와 '물리 관측'으로 주장한 임시 metadata 행을 섞어 `allow_fixtures=True` 실행 → `B09_BEFORE_MIXED_ACCEPTED MOCK_ONLY 7` (합성 시험 데이터에만 해당, 실제 물리 관측 없음).
- GREEN: `B_FIXTURE_MODE_REAL_DATA_FORBIDDEN` 발생, 별도 실데이터 경로는 기존처럼 검증. **25 passed in 0.30s**(기존 23 + 2).
- GitHub CI: 문서 작성 시 **NOT_RUN**, PR 본문에서 후속 확인.
- 물리 실측 0건 / 모델 정확도 미측정 / A 트레이 카메라 미제공.

## 주니어 개발자 핵심 교훈

테스트 모드에서 '검증 성공'이라는 로그가 출력되더라도 현실 데이터의 근거가 되는 것은 아닙니다. 데이터 분류 경계가 약하면 실제 샘플과 더미가 섞여 학습 결과의 의미를 잃게 됩니다. 검증 기능을 늘리는 대신 **테스트 모드의 허용 데이터를 좁히는 방식**이 MVP에 적합합니다.

## 다음 경계

A의 실제 전용 트레이 RGB와 운영자 관측/권리 기록을 수집한 후, B에서 **실제 1건 수집·정답 검수**, 그다음 독립 stack 그룹별 train/val/test 확보 시 C에게 read-only 전달. 모든 실제 수집/학습은 준비 전 **NOT_RUN**입니다.
