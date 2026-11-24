# B-06 — 물리 관측 증거 무결성 검증 강화

- 날짜: 2026-11-23(KST). 범위: B 이미지 등록 경계.
- 기준: B Draft PR #37 `4c63d8a88297b7418efccb6e933c25275d9807ce`.
- 결과: **로컬 PASS / GitHub 원격 CI는 후속 Run으로 확인 / 실제 물리 안전성 NOT_RUN**.

## 왜 지금 수정했습니까?

기존 `collect_tableware.py`는 `--physics-evidence`를 비어 있지 않은 문자열로만 검사했습니다. 따라서 존재하지 않는 파일 경로도 `PHYSICS_OBSERVED`로 등록되었습니다. B 데이터 계약의 핵심은 물리적으로 관측한 장면만 C에게 넘기는 것이므로, 모델 학습 이전에 이 입력 경계를 우선 보강합니다.

## 변경/의사결정

- `ai/scripts/collect_tableware.py`: 증거 파일의 **존재·0바이트 여부·수집 이미지와 다른 파일인지** 확인합니다. 기존 `capture_config.physics_evidence` 필드를 보존하며 `physics_evidence_sha256` 및 크기(바이트)를 추가합니다.
- `tests/test_b_dataset.py`: 기존 test를 실제 임시 파일 사용으로 보완하고, 증거 부재/자체 참조/빈 파일에 대한 회귀를 추가합니다.
- 기록 이유: 수집 이후 증거가 변경됐는지 SHA로 대조할 수 있지만, 해시 일치가 과학적 안정성 인증을 의미하지는 않습니다. 전문가/운영자 육안 및 물리 상태 검수는 계속 필수입니다.
- 채택하지 않은 대안: 임의 텍스트를 증거로 계속 허용하거나, 무거운 영상 분석/Physics 엔진을 B 수집기에 추가하는 방식.

## RED → GREEN 실제 재현

```bash
# 아래 두 버전에 같은 가짜 존재하지 않는 증거 경로 제공
python3 ai/scripts/collect_tableware.py --image /tmp/tray.png \
  --root /tmp/b-repro --manifest /tmp/b-repro/m.csv --label STABLE \
  --scene-id s --stack-id g --source GAZEBO_TRAY --license-status OWNED \
  --physics-evidence /tmp/b-repro/NOT_EXIST.log --camera /smartdish/tray/image_raw
python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py
```

- 수정 전 원본 B-02 코드로 동일 스크립트 시뮬레이션 재현: `BEFORE_PATCH_RC=0`, `B_CAPTURE_INGESTED` (부정확한 성공).
- 수정 후: `AFTER_PATCH_RC=1`, `ValueError: B_PHYSICS_EVIDENCE_FILE_MISSING` (의도된 Fail-closed).
- 수정된 로컬 전체 B 범위: `15 passed in 0.22s` (ROS 노드/Gazebo/실제 라벨은 NOT_RUN).
- 디버깅 보고서: [B-DEBUG-02](../issues/2026-11-23_B-DEBUG-02_unverified_evidence_reference.md).

## 교육 포인트

CSV의 `PHYSICS_OBSERVED` 필드가 있다고 해서 물리적 근거가 존재하는 것은 아닙니다. 입력 경계에서 파일 무결성을 검사하고, 실제 관측 품질은 사람의 별도 검토로 확인해야 합니다. 원본 오류가 성공처럼 보이는 경우에도 반례를 만들고 동일 조건에서 재검하는 것이 중요합니다.
