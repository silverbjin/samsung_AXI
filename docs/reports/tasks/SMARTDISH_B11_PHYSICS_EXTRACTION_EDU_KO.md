# B-11 교육 보고 — RGB 입력 시점과 10초 뒤 물리 결과를 나누는 이유

- 코드: `ai/scripts/extract_a13_candidates.py`; 입력은 B-10이 모든 체크를 통과한 비공개 `/raw` 디렉터리.
- 초기 개발 시 A 보고서만 존재했으나 2026-11-25 사용자 원본 TAR를 추가 업로드받아 **B에서 직접 88/88 및 이미지·물리 타이밍 4/4 재검증**했습니다. 신규 WSL2 현장 재실행과는 구별합니다.

## 왜 시간 축이 중요한가?

```mermaid
sequenceDiagram
participant G as Gazebo
participant C as RGB 저장
participant T as Pose 기록
participant B as 사람 라벨 담당
G->>C: 캡처 t1=0.60s (입력 X)
T-->>C: 최근접 Pose 0.55s (차이 50ms)
G->>T: 이후 10+초 식기 물리 궤적 (결과 Y 근거)
T->>B: HELD_OBSERVED 또는 FALL_OBSERVED
B->>B: 이미지가 낙하 이전인지 검토 / 수동 승인
```

RGB 한 프레임은 접촉력/무게중심을 직접 관측하지 못합니다. 프레임 이후의 물리 결과로 **라벨을 제안**하지만 미래 정보를 C 이미지 입력 feature에 추가하면 정답 유출입니다.

## 코드와 결과

- `trace_audit`: JSONL 각 `sim_ns/entity/pose` 읽기, Entity 시간 역행·누락·NaN/Inf·비정규 Quaternion·관측 구간 외 데이터 거부.
- `group_key`: 초기 식기들의 위치·크기·자세를 0.01 단위로 정규화해 seed나 trial_id만 다른 사실상 동일 배치의 누수를 피함. 이것은 자동 독립성 **보장**이 아니라 근접 중복 사람 리뷰용 보수적 그룹입니다.
- `audit_trial`: 캡처/관측 시간, capture-vs-initial 낙하 여부, 초기/최종/trace 데이터의 구별, 계산한 낙하량/XY 이동량 (`derived`) 저장.
- `make_svg`: 실제 JSONL만 받아 z(m)·tilt(deg)·XY 경로 그래프 작성, RGB/physics 관측 시작·끝 표시.
- `review.html`: 원본 PNG와 세 그래프, 식기별 계산값, 출처/검토 대기 상태를 한 화면에서 표시.

## 제한과 테스트

신규 계약 fixture에서 4개 후보 및 그래프 12개를 생성할 수 있는지 검증합니다. PNG/JSONL 데이터는 **교육용 합성물**로 실제 결과라고 발표하지 않습니다. 원본 TAR를 받기 전 `B_REAL_CANDIDATES_VERIFIED`를 선언하지 않습니다.

A `verify_timing`이 허용하는 최대 이미지-Pose 250ms와 실제 인수 보고의 50ms를 구분합니다. A에서 9초를 허용해도 B 학습 검토는 10초 미만 시 `TEMPORAL_REVIEW_REQUIRED`로 차단합니다.


## 2026-11-25 실제 원본 B-11 검증 결과

- 실제 업로드 원본 TAR의 B-10 SHA 88/88 통과 후, 오프라인 B-11 추출 PASS.
- 원본 PNG **4장 RGB 640×480**, 물리 궤적별 Pose **407/609/407/407**, SVG **12개(각 장면 z·tilt·XY)**, `review.html`, `candidate_manifest.csv` 생성.
- 관측 시간 ST-01 10.286s / ST-02 10.229s / UN-01 10.227s / UN-02 10.232s. Image 0.600s, Pose 0.550s, Δ50ms; 시간 감사 `PASS` 4/4.
- 물리 관측 HELD/HELD/FALL/FALL은 **추천 라벨만** 생성; `REVIEW_REQUIRED` 4건 / 운영자 승인 0. 학습 분할 미생성.
- 이 파일럿의 독립 그룹은 클래스별 2개 후보에 불과해 최소 3그룹을 만족하지 않습니다. `B_DATASET_SPLIT_BLOCKED` 유지.
