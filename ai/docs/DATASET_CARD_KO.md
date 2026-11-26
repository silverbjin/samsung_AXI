# SmartDish B 데이터셋 카드 v1.0 — 식기 적재 안정성

- 작성: 2026-11-23 / 데이터 책임 B / 모델 책임 C
- 운영자가 **승인한 학습 데이터는 0건**이며 manifest/split_manifest는 헤더만 있습니다. B-10/11이 직접 검증한 실제 A-13 원본 후보는 **4장**, 사람 승인 0건, 실제 `STABLE`/`UNSTABLE` 모델 성능은 **NOT_RUN**.
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
| A가 제작한 `/smartdish/tray/image_raw` 및 검증된 물리 로그 | Gazebo 트레이 RGB | A 원본 SHA 및 사람 승인·권리 검토 후 `GAZEBO_TRAY`, `OWNED/AUTHORIZED` |
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

**B-09 더미 격리:** `--allow-fixtures`는 `CONTRACT_FIXTURE/MOCK_ONLY`만 검증하는 시험 모드입니다. `PHYSICS_OBSERVED` 행을 함께 넣거나 실제 행만 전달해도 `B_FIXTURE_MODE_REAL_DATA_FORBIDDEN`으로 실패합니다. 실제 데이터는 이 옵션을 제거하고 기본 `prepare_dataset.py` 경로로만 처리합니다.

## 5. 실물 데이터 수집 의존성 및 한계

A의 전용 트레이 카메라와 실제 Gazebo 물리 배치 4/4는 **A-13 WSL2 인수에서 검증됨**. 2026-11-25 이후 사용자 TAR 직접 업로드로 **B의 원본 SHA와 내부 88/88 및 후보 PNG 4장/시간 정렬·물리 궤적 검사가 PASS**했습니다. 다만 **사람 라벨 승인 0건·분할/성능 평가 NOT_RUN**, 사용자 WSL2의 새 B 원샷 직접 수락은 별도입니다. B-05는 ROS 2의 `/smartdish/tray/image_raw`를 1회 읽고 **라벨 없이 `ai/data/private`에 저장하는 선택형 루틴**을 추가했습니다. 이 기능의 ROS/Gazebo 실제 수신은 여전히 NOT_RUN입니다. `collect_tableware.py`는 운영자가 물리 상태를 **별도로 관측**하고 증거 파일을 제공한 경우에만 CSV를 등록합니다. 단색 fixture 6장은 실제 물리 표본으로 전환 금지.

## B-08R 데이터 등록 일관성 경계

Ubuntu/WSL2 수집기 `collect_tableware.py`는 동일 manifest에 대한 동시 입력을 `B_COLLECTOR_BUSY`로 거절합니다. 프로세스 비정상 종료 뒤 CSV에 기록되지 않은 `B-*.png`와 임시 파일이 존재하면 `B_ORPHAN_FILES_DETECTED`로 차단하며 원본은 자동 삭제하지 않습니다. 파일의 존재·해시는 진실한 물리 관측의 증명이 아닙니다. 실물 데이터는 0건이며 모델 학습 NOT_RUN 상태를 유지합니다.


## 6. B-10~B-14 — A-13 실물리 원본 인수 후보·사람 승인 정책 (2026-11-25)

- A 인수 출처: [A-13 PR #45](https://github.com/silverbjin/samsung_AXI/pull/45), `main@63e147289e307e0b9900ca365e9c4557c5921804`; 실제 WSL2 실행 SHA `6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df`.
- 원본 압축 SHA256 `bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e`는 이번 B 업로드 TAR `(6).gz`에서 **직접 일치 확인**, 내부 **88/88 PASS**, trial 4/4 PASS를 B가 재검했습니다. 0바이트 선택형 진단 로그 8건은 SHA 검증 뒤에만 허용합니다.
- A 출처 보고에서 RGB 640×480 rgb8, 이미지 0.6s/가까운 Pose 0.55s(50ms), trial 물리 관측 >10s, ST 유지·UN 낙하. 동일 수치를 이번 B 직접 TAR에서도 대조했습니다. RGB callback 52×4는 학습 이미지 208장이 아니며, 실제 저장 대표 PNG는 **4장**입니다.
- 현재 **B 실제 검증 후보 4장 (HELD 2, FALL 2), 운영자 승인 0장, 학습 manifest 신규 샘플 0장, split 출고 0**. 시간 정렬 검토 4/4 PASS, 독립 stack 후보는 각 클래스 최대 2개로 분할에 부족합니다.
- B-10 안전 TAR 해시/파일집합/링크 거부 → B-11 PNG/Trace·Image/Pose/시계열 SVG → B-12 별도 사람 승인 JSONL → B-13 기존 10열 manifest와 224×224 이미지 → B-14 상대경로 물리 증거·SHA 재검·C readiness.
- A 자동 observation(HELD/FALL)은 검토 추천일 뿐 확정 학습 라벨 아님. `REVIEW_REQUIRED`, `NOT_OPERATOR_APPROVED`, `NOT_OBSERVED` 원본 유지. `UNKNOWN` 학습 클래스로 사용하지 않음.
- 근접중복: 초기 식기 기하를 기준으로 stack_id를 보수적으로 묶으며, 실제 독립성 최종 판단은 사람 리뷰. 클래스별 독립 ≥3그룹 전에는 train/val/test 미생성.
- 권리: Gazebo 환경 산출물은 출처·모델/텍스처 권리 검토 후 `GAZEBO_TRAY`+적절한 `OWNED/AUTHORIZED`로 등록; `REAL_TRAY` 또는 DACON으로 표시하지 않음.
- 정적 독립 트레이의 물리 결과는 실제 주행 중 동적 안정성/로봇 부착 카메라 도메인 성능 또는 안전 인증이 아님.
- 수집/승인/출고 절차: [B 원샷 워크북](../../docs/guides/SMARTDISH_B_A13_EVIDENCE_WORKBOOK_KO.md), [C 인계](../../docs/handoff/B_REAL_DATA_C_HANDOFF_KO.md).


### B-10 DBG-04 실제 원본 확인 추가 기록

- 실제 사용자 첨부 Archive SHA와 내부 88개를 B에서 모두 재검하고 RGB·JSONL 후보 4건을 생성했습니다. 이전의 'TAR 미확보' 기록은 당시 상태로, **현재 판정은 직접 원본 PASS**입니다.
- TAR 전체 89개 구성원 중 SHA256SUMS 88개; 선택적 probe stdout `.log` 8개는 올바르게 비어 있고 `e3b0c442...b855` 해시로 봉인됐습니다. B 인수기에서는 정확한 패턴에 한하여 비어 있는 로그를 허용하며 필수 PNG·물리·메타데이터는 빈 파일 거부를 유지합니다.
- 사람 승인 전 원본 `REVIEW_REQUIRED`를 그대로 유지하며 승인된 학습 이미지 0, C readiness BLOCKED 상태입니다.
- [직접 인수 원장](../../docs/reports/acceptance/SMARTDISH_B_REAL_DATA_ACCEPTANCE_KO.md), [DBG-04](../../docs/reports/issues/SMARTDISH_B10_DBG_04_REAL_ARCHIVE_EMPTY_DIAGNOSTIC_LOGS_KO.md).


## B12R/B14R Owner 후속 (2026-11-25)

- 사용자 진단 TAR SHA `912bfbc759e3fde3f48e70316638bc86dd30c52461ecd19410281bd7edf1f515` 검증, B15 내부 SHA **53/53 PASS**, 종료코드 0. 이는 원본 A TAR 88개 전체가 포함된 묶음이 아닌 진단 부분집합입니다.
- B12R 안전 복원기: 진단 SHA/내부 해시, 원본 PNG 4·물리 SHA·RGB/크기, 리뷰 HTML이 참조하는 SVG 12개 확인. 승인 공란 템플릿만 작성, 운영자 승인 0, 모델 학습 0.
- B14R: 현재 A13 `placements(scene_id,seed)`는 4개 고정 레이아웃에서 seed가 x/y를 ±0.001m 흔들 뿐입니다. 같은 `source_scene_id`가 다중 legacy stack_id로 분리되면 B13 split을 `B14_A13_SEED_JITTER_SPLIT_LEAKAGE`로 차단, 같은 템플릿 라벨 충돌도 차단합니다. 이는 A13 지정 SHA에 한정하며 기존 다른 소스 계약은 유지합니다.
- 실제 클래스별 독립 템플릿 최대 2/2, C 학습 여전히 HOLD. [Owner 인수](../../docs/reports/acceptance/SMARTDISH_B15_OWNER_DIAGNOSTIC_ACCEPTANCE_20261125_KO.md), [운영자 워크북](../../docs/guides/SMARTDISH_B12R_REVIEW_OPERATOR_WORKBOOK_KO.md).

## B-DATA-QA-01 — DACON baseline v1.0 compatibility audit (2026-11-25)

- 사용자 첨부 [DACON 기준선](../../docs/quality/SMARTDISH_B_DACON_DATA_QUALITY_BASELINE_20261125_KO.md)의 **B-Q01~B-Q07**을 제품 승인 이전의 QA 제안 기준으로 보존합니다. DACON audit ZIP 2,100 scenes/4,200 PNG 통계, Dev↔Test 100 scene exact front/top duplicates는 첨부 문서의 기록이며 **현재 B 작업에서 DACON audit ZIP을 다시 직접 재검한 것은 아님**.
- A13 원본 SHA `bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e`의 내부 88개를 직접 재계산하면 **B-Q01 PASS**. B15 진단 subset만 있으면 원본 전체 88개 SHA 재검으로 주장하지 않으며 Q01 HOLD입니다.
- B-Q02 RGB(t0) 640×480 카메라 SDF·50ms 동기화 구조 확인에도 시각적 가림 승인 부재 **HOLD**. B-Q03 실제 식기 JSONL은 WORLD pose 위주이므로 tray-relative pose / measured velocity/contact / 독립 GT 규칙 부족 **HOLD**. B-Q04 사람 승인 0 및 독립 규칙 없음 **HOLD**.
- B-Q05 4 fixed A13 scenes/가림·환경×클래스 커버리지 부족 **HOLD**. B-Q06 승인된 분할 없음, file SHA/pixel SHA exact 0 overlaps within 4 pilot images, aHash 유사 후보 2쌍은 사람 검토 대기 **HOLD**. B-Q07 실제 human-approved manifest/C release 미확보 **HOLD**.
- DACON 384×384 front/top, 10s 및 0.015m cumulative movement는 **비교 후보**, 기존 제품 640×480 원본/단일 카메라와 구분. 0.015m와 월드 누적 이동으로 사람 라벨을 자동 승인하지 않음.
- 최종: **B-DATA-QA-01 감사 실행 PASS / 데이터셋 출고 HOLD**, 운영자 승인 0, C 모델 학습 NOT_RUN. [교육 보고](../../docs/reports/tasks/SMARTDISH_B_DATA_QA01_DACON_EDU_KO.md) / [실제 게이트 원장](../../docs/reports/acceptance/SMARTDISH_B_DATA_QA01_ACCEPTANCE_20261125_KO.md) / [WSL2 원샷](../../docs/guides/SMARTDISH_B_DATA_QA01_WSL2_RUNBOOK_KO.md).

## B-QA03 A15 Owner 파일럿 검수 계약 (2026-11-26 최초 개발 시점; 아래 실제 검수 갱신 참조)

- A15 과거 Owner 검수보고 SHA `828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05`, 4/4 실물 data+GUI PASS, teardown server `-11` ×4 FAIL 및 전체 contact production health HOLD. 출처 [A15 Owner 보고](../../docs/reports/acceptance/SMARTDISH_B_A15_QA03_ACCEPTANCE_KO.md). 이 B-QA03 작업 공간에는 **Owner 원본 TAR 바이트 자체가 없어 독립적인 outer15/inner64 및 1ms 물리 궤적 재계산은 NOT_RUN**. 기존 A 보고서·연결된 독립 리뷰 JSON을 임의로 이번 B 직접 PASS로 승격하지 않습니다.
- 신규 `ai/scripts/audit_b_a15.py`는 OWNER 정확한 외부 SHA, 모든 내부 SHA, 4×(10301×4 entity) 동기화 1ms Pose/초기 지지, tray inverse/속도 유도 경계, 상단 식기 변위/거리/회전, 500×1ms 명령, Contact ECM/ROS 동일 시각의 positive subset을 재검할 수 있는 CPU 전용 offline consumer입니다. 원본 없으면 B-Q01까지 HOLD.
- 사람 검토 worksheet의 승인 칸은 공란입니다. 현재 A15 사람 승인 0, `rule_candidate=UNKNOWN`, `ground_truth=NOT_OPERATOR_APPROVED`, B-Q01~07 직접 검사 전체 HOLD. **학습용 real manifest/split/C 모델 학습 NOT_RUN**.
- 두 geometry family/네 layout, top 640×480 RGB 단일 카메라, static world-Y 0.12Nm 명령은 DACON front+top 또는 주행 트레이 가속도와 동등하지 않습니다. 제품 0.015m 임계치 확정 금지, Cloud+Owner 동일 layout은 8개 독립 표본으로 계산 불가. [교육 보고](../../docs/reports/tasks/SMARTDISH_B_A15_QA03_PILOT_QUALITY_KO.md) / [A16 확대 요구](../../docs/plans/SMARTDISH_A16_EXPANSION_QA03_REQUIREMENTS_KO.md) / [C 인계](../../docs/handoff/SMARTDISH_B_A15_QA03_TO_A_C_KO.md).

### B-QA03 실제 원본 직접 검수 갱신 (2026-11-26)

- Owner 원본 수령 및 공식 CPU Python CLI 검수 완료(exit0 REVIEW_ONLY). 원본 고정 SHA/outer15/inner64, RGB 4장, 1ms Pose/ECM, exact t0 support, 500-step torque, ROS same-stamp subset, geometry/family/layout 및 파일·픽셀 SHA 재검. B-Q01 PASS/Q02~Q07 HOLD. FOV design/validity 분리 연결 오류 수정; 원본 미제공 기록은 과거 상태.
- 2 family/4 layout; exact duplicate 0; aHash 유사 후보 6쌍(0–2), 운영자 검토 필요. ROS positive subset 55932/140744는 전체 전달률이 아님. Cleanup -11 ×4 FAIL, full production contact HOLD, GT UNKNOWN_HOLD, 승인 0, split/manifest/C 실학습 0. 실제 data/GUI PASS와 제품 승인을 혼동하지 않음.
- 원본/worksheet/진단은 private, Git에 포함하지 않음. [실제 원장](../../docs/reports/acceptance/SMARTDISH_B_A15_QA03_ACCEPTANCE_KO.md) / [DBG-02](../../docs/reports/issues/SMARTDISH_B_A15_QA03_DBG_02_FOV_SCHEMA_KO.md).


## B-QA04 — A16 실제 Owner raw 독립 검수 (2026-11-26)

A16 Owner DATA/GUI 8/8 PASS and user visual review completed, server -11×8 and minimal camera-only -11, all stopped. Exact production bacc1af and B verifier b36694d; actual independent CPU CLI exit0 REVIEW_ONLY for A15+A16. 12 distinct layout/pixel hashes, 4 geometry families, 66/66 pairwise aHash <=8 review candidates (22 aHash distance0, not exact pixel duplicates). Q01 PASS Q02–07 HOLD, actual approved0, contact production HOLD, C real training0. See [actual QA04 report](../../docs/reports/acceptance/SMARTDISH_B_A16_QA04_OWNER_RELEASE_KO.md). No public raw/worksheet or new learning manifest. WSL2 B runner NOT_RUN. Same layout Cloud/Owner one group. Future t0 RGB only; no post-t0 leakage. 


### B-QA04 Owner 검수 제품 인수 완료 (2026-11-26)

제출 진단 외부 SHA 6bb16e93a22079c588a63afc9f04e8725154b25313ea133d277d5ba547eea83f 및 내부 3/3 PASS; exit 0, verifier b36694d 기록, 실제 독립 검수 JSON byte-for-byte 일치. B_QA04_OWNER_VERIFIER_ACCEPTED_REVIEW_ONLY. Q01 PASS Q02–07 HOLD, 12 layout/4 family, 승인 0, Contact HOLD 및 cleanup FAIL 유지. [Owner 인수 원장](../../docs/reports/acceptance/SMARTDISH_B_A16_QA04_OWNER_20261126_KO.md). 실제 WSL2 checkout 별도 로그는 진단에 없음; 기존 raw 검수 증거 재사용. 새 학습 승인 또는 제품 병합 아님.
