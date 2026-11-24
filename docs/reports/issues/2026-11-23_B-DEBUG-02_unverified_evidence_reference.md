# B-DEBUG-02 — 존재하지 않는 물리 증거 참조도 데이터셋에 등록됨

- 일자: 2026-11-23 / 환경: Python 3 + Pillow, 로컬 스모크.
- 영향 경계: B 수집기의 `PHYSICS_OBSERVED` 메타데이터 등록.
- 최초 기준 SHA: `4c63d8a88297b7418efccb6e933c25275d9807ce`.
- 판정: **RESOLVED (로컬 입력 경계)** / ROS 카메라 및 실제 물리 라벨 **NOT_RUN**.
- 연관 보고: [B-06](../tasks/2026-11-23_B-06_physics_evidence_integrity.md).

## 1. 증상/최초 실패

로컬 임시 트레이 PNG를 만들고 `--physics-evidence /tmp/NOT_EXIST.log`를 지정했습니다. 이 파일은 실제로 존재하지 않았지만 최초 구현에서는 `BEFORE_PATCH_RC=0`, `B_CAPTURE_INGESTED ...`가 출력되며 CSV의 `ground_truth`가 `PHYSICS_OBSERVED`가 됐습니다.

## 2. 원인 분리

- 사실: `collect_tableware.py`의 유효성 검사 조건은 `evidence.strip()`만 확인했습니다.
- 배제: ROS2 QoS, Gazebo 월드, 이미지 디코더의 문제가 아닙니다. 단일 파일 유효성 경계에서 재현됩니다.
- 확정된 근본 원인: 증거가 가리키는 실제 파일을 `is_file()`/내용 검사로 검증하지 않았기 때문입니다.

## 3. 최소 수정

- `Path(evidence).resolve().is_file()` 필수.
- 이미지와 동일 파일이거나 빈 파일이면 거부.
- 독립 증거 파일의 SHA-256과 byte count를 `capture_config`에 기록. 기존 CSV 컬럼/타입 유지(C 호환).
- 남은 한계: 파일이 존재한다고 내용이 참임을 자동 판정할 수는 없습니다. 사람의 물리 검수는 별도입니다.

## 4. 동일 경계 재검

- 수정 후 동일 미존재 경로: `AFTER_PATCH_RC=1`, `ValueError: B_PHYSICS_EVIDENCE_FILE_MISSING`.
- 임시 존재 파일 사용: 정상 수집 및 SHA 기록.
- 최소 테스트: `test_physics_reference_must_be_real_nonempty_independent`.
- 전체 로컬 B 테스트: `15 passed in 0.22s`.
- 원격 Actions 결과: 후속 Run 기록에서 확인. 수정 커밋은 본 이슈 보고서와 동일 Git commit.

## 5. 훈련생 질문

기존 코드가 `PASS`를 출력했는데 왜 결함입니까? `파일 형식 검증`, `파일이 실제 존재함`, `물리적으로 올바른 라벨`의 세 수준을 구분해 설명하십시오.
