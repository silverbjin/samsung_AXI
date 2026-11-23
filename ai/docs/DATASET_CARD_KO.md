# SmartDish B 데이터셋 카드 v1.0 — 식기 적재 안정성

- 작성: 2026-11-23 / 데이터 책임 B / 모델 책임 C
- 실제 데이터: **0건**. manifest/split_manifest는 헤더만 있음. 실제 `STABLE`/`UNSTABLE` 성능은 **NOT_RUN**.
- 베이스: samsung_AXI main `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`.
- S7의 TABLE_3 전방 영상과 static fixture는 **트레이 안정성 ground truth가 아님**.

## 1. 목표와 제외 범위

트레이에 올려놓은 식기가 이동 전에 물리적으로 안정한지 검토하기 위한 **지도학습 2클래스** 데이터입니다. `STACKED/NOT_STACKED`는 S7의 존재 여부 라벨이라 변환하지 않습니다. `UNKNOWN`은 C 추론의 저신뢰/영상 없음/오류 상태이며 학습 클래스가 아닙니다. 이미지 판독만으로 실물 안전을 인증하지 않습니다.

## 2. 라벨 승인 규칙 (사람/시뮬레이션 확인 필요)

| 라벨 | 필수 관찰 | 예시/반례 |
|---|---|---|
| `STABLE` (0) | 실제 트레이 위 식기 배치, 지지와 접촉 유지, 명확한 쏠림·전도·낙하 없음. 같은 배치의 물리 시뮬레이션 정착 이후 관찰 기록 | 다수 식기가 겹쳤다는 사실만으로는 STABLE 불가 |
| `UNSTABLE` (1) | 식기 낙하·전도, 받침면 이탈, 트레이 가장자리 밖 이탈, 물리 시뮬레이션 중 명백한 붕괴 중 하나를 관찰·기록 | 단순 빈 테이블, 빈 트레이는 UNSTABLE 아님 |
| 제외 (`UNKNOWN`-학습 안함) | 트레이 없음/식기 없음, 시야 막힘, 흐림, 움직임 불명, 안정·불안정 근거 미확인, 충돌 판정 불분명 | 추론 단계에서는 `UNKNOWN` |

라벨링 시각: 트레이 위 배치를 고정한 후 같은 장면에서 **10초 시뮬레이션 영상 또는 구체적 관측 시간·전후 Pose**를 기록하도록 권장합니다. 10초는 DACON 시뮬레이션과 비교를 위한 수집 기준이지 물리안전 인증 기준이 아닙니다. 지지면/편심/기울기/이동량에 대한 실측치가 있으면 `capture_config`의 증거 경로에 포함하지만 숫자 임계값은 A/C 실제 장면을 확인한 뒤 별도 합의합니다. 단일 RGB에서는 무게중심/접촉력을 직접 알 수 없음을 적습니다.

## 3. 데이터 출처와 권리

| 출처 | 범주 | 사용 결정 |
|---|---|---|
| A가 제작할 `/smartdish/tray/image_raw` 및 물리 로그 | Gazebo 트레이 RGB | 장면과 기록이 완성된 후 `GAZEBO_TRAY`, `OWNED` |
| 실제 트레이 촬영 + 동의 | 카메라 RGB | 사용 허가를 문서화한 뒤 `REAL_TRAY`, `AUTHORIZED` |
| DACON 236686 | 구조물 2뷰 + train simulation.mp4 | **도메인 다름. 원본 다운로드·사용·재배포 권리 미확정. 공개 저장소 반입 금지.** |
| 로컬 코드가 생성한 단색 fixture | `CONTRACT_FIXTURE` | 오직 데이터 파이프라인 체크, `MOCK_ONLY` |

DACON 설명은 `open.zip` 아래 `train/{id}/{front.png,top.png,simulation.mp4}`, `dev/{id}/{front.png,top.png}`, `test/{id}/{front.png,top.png}`, `train.csv`, `dev.csv`, `sample_submission.csv` 형태로 **공식 페이지에 안내**됩니다. 실제 ZIP을 내려받거나 내부 검증하지 않았으므로 파일 실재 여부는 `NOT_RUN`입니다. 대회 동의 약관에는 대회 데이터의 비참가자 배포·복제 제한이 있으므로 외부 공개를 금지하는 보수적 원칙을 적용합니다.

출처: https://dacon.io/competitions/official/236686/data / https://dacon.io/competitions/official/236686/overview/agreement / https://dacon.io/competitions/official/236686/overview/rules

## 4. C 인계 스키마

- `manifest.csv`: `sample_id,scene_id,stack_id,label,image_path,source,capture_config,license_status,ground_truth,image_sha256`
- `split_manifest.csv`: 위 10열 + `split` (`train`/`val`/`test`). 분할 단위는 **stack_id**, `scene_id` 하나에 여러 stack이 걸치면 불허. 같은 스택의 연속 프레임을 서로 다른 split에 놓지 않습니다.
- `label_map`: `{"STABLE":0,"UNSTABLE":1}`. 숫자 순서는 C와 사전 합의 없이 변경하지 않습니다.
- 저장 형식: **PNG, RGB, 224×224**, Python Pillow `ImageOps.exif_transpose` → `convert('RGB')` → `ImageOps.fit(..., 224×224, BILINEAR)`. 정규화(mean/std)는 C 학습·추론에 같은 방식으로 별도 고정하며 B가 임의로 지정하지 않습니다.
- `capture_config`: JSON 객체 문자열, 최소 `camera`, `physics_evidence`, `preprocess` 저장. B-06부터 `physics_evidence`는 존재하고 비어 있지 않은 독립 파일이어야 하며 `physics_evidence_sha256`·`physics_evidence_size_bytes`도 포함합니다. 이는 파일 무결성 추적이지 물리적 참/거짓 자동 판정이 아닙니다. 물리 근거 파일은 Git 비추적.
- `ground_truth`: `PHYSICS_OBSERVED`만 학습 가능; `MOCK_ONLY`는 `--allow-fixtures`에서만 검사.
- 분할의 독립성: 그룹 `stack_id`, label별 최소 3개 독립 그룹; Seed `smartdish-b-v1`, 그룹별 SHA256 정렬, 20% test + 20% val 반올림, 나머지 train. 클래스별 균형은 리포트 확인. 임계값은 데이터 확보 후 재검토.
- 중복 판정: 포맷 변환된 PNG의 SHA256, 완전히 동일한 이미지가 별도 행이면 실패. 근접 중복은 **미구현/수동 검토**.
- 데이터/라이선스 검증: `license_status`는 `OWNED` 또는 `AUTHORIZED`; 증거 없는 외부 소스 불허.

**B-07 데이터 재감사:** `PHYSICS_OBSERVED` 행은 B-06 수집기에서 기록한 `physics_evidence_sha256`과 `physics_evidence_size_bytes`를 `prepare_dataset.validate()` 실행 때마다 원본 파일과 비교합니다. 품질 JSON의 `evidence_hash_verified`는 성공한 파일 검사 건수일 뿐 물리 안전성이 확인된 건수가 아닙니다. 원본 유실·변조는 `B_PHYSICS_EVIDENCE_MISSING/SHA_MISMATCH/SIZE_MISMATCH`로 차단합니다.

## 5. 실물 데이터 수집 의존성 및 한계

A의 별도 트레이 지향 카메라(토픽 `/smartdish/tray/image_raw`)와 실제 물리 적재 장면이 없으므로 **실제 이미지 수집·분할/성능 평가 NOT_RUN**. B-05는 ROS 2의 `/smartdish/tray/image_raw`를 1회 읽고 **라벨 없이 `ai/data/private`에 저장하는 선택형 루틴**을 추가했습니다. 이 기능의 ROS/Gazebo 실제 수신은 여전히 NOT_RUN입니다. `collect_tableware.py`는 운영자가 물리 상태를 **별도로 관측**하고 증거 파일을 제공한 경우에만 CSV를 등록합니다. 단색 fixture 6장은 실제 물리 표본으로 전환 금지.
