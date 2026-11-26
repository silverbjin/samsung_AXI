# B-14 교육 보고 — 파일럿 4장과 학습 데이터셋의 차이

- 코드: `register_a13_approved.py`, `scripts/smartdish_b_real_data_one_shot.sh`.
- 상태: B 실물 TAR 미확보 / 검증 후보 0 / 실제 승인 0 / C 학습 NOT_RUN.

## 규모를 늘리기 전에 증거를 검증해야 하는 이유

A 보고서에는 4개의 장면에서 저장 PNG가 있다고 기록되지만, 이미지 callback 52건씩 총 208건을 학습 데이터 208장으로 간주하면 안 됩니다. A 원본 구조상 각 trial 대표 PNG 1장이며 **이번 B에서 파일을 직접 검증하면** 최대 초기 후보 4장을 기대합니다.

클래스별 독립 배치 2개씩이라면 기존 B 최소 3개 조건을 충족하지 않습니다. 같은 초기 배치의 seed만 바꾸거나 JPEG/PNG 복사본을 늘려 독립 그룹 수를 채워서는 안 됩니다.

## 출고 경계

- 후보/승인/보류/거부/독립 그룹 수를 별도 보고.
- 승인 원본 PNG와 물리 증거/승인 ledger/후보 index를 비공개 release root에 복사, `SHA256SUMS`와 `release_manifest.json`을 생성.
- 실제 승인 뒤 `PHYSICS_OBSERVED`는 데이터 provenance 의미이며 물리 안전 인증을 의미하지 않습니다.
- 데이터 출고 root를 옮기면 B `prepare_dataset` 및 C `check_real_data_readiness`의 해시를 다시 확인합니다.
- `MOCK_ONLY` 사용이나 seed 임의 조작으로 split 부족을 우회하지 않습니다.

## A 생산 확대 제안 (자동 인수 조건 아님)

1. Pilot 4장: 실제 파일 인수·시각 검수·사람 라벨 승인 계약을 확인.
2. Minimum: 클래스별 독립 초기 식기 배치 3개 이상을 실험하고 train/val/test 그룹 누수 0 확인.
3. MVP: 클래스별 독립 50배치 목표, 실패 유형과 모호성 기록. 이는 초안 목표이며 정확도 보장 아님.
4. C baseline 평가에서 놓친 유형 중심으로 데이터 확대. A의 기존 `single/batch`와 seed 설정 지원 범위를 먼저 확인하고, 구조 자체를 바꾸려면 A 담당 계약 변경 요청.

주의: A-13은 정적 독립 트레이 테스트 세계입니다. 실제 이동 중 식기 안정성이나 로봇 장착 RGB 센서 분포까지 확인한 결과는 아닙니다.
