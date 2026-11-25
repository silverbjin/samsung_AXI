# SmartDish B → C / E — A-13 실데이터 인계 문서

- 기준 main: `63e147289e307e0b9900ca365e9c4557c5921804`; A-13 실행 `6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df`.
- A 원본 TAR SHA: `bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e`, **B 직접 업로드 원본 검증 88/88 PASS / 4개 원본 이미지 후보**. 단, 이번 검증은 ChatGPT Linux 컨테이너이며 사용자 WSL2 B 원샷 재인수는 별도입니다.
- 물리적으로 관측된 원본 이미지 후보는 4건이고 **라벨 승인 0건**, 실제 B 학습용 224×224 승인 이미지 0건, `split_manifest.csv` 출고 0건입니다. C 모델 학습 NOT_RUN.

## 소비 가능한 계약 (미변경)

| 필드 | 계약 |
|---|---|
| `manifest.csv` | `sample_id,scene_id,stack_id,label,image_path,source,capture_config,license_status,ground_truth,image_sha256` |
| `split_manifest.csv` | 위 + `split(train/val/test)` |
| 라벨 | `STABLE=0`, `UNSTABLE=1`, `UNKNOWN` 모델 추론 상태 |
| PNG | RGB 224×224, PIL `ImageOps.fit` BILINEAR |
| Ground truth | `PHYSICS_OBSERVED`는 **사람 승인된** 물리 관측 후보만 B 어댑터로 등록 |
| 사용권 | `OWNED` 또는 `AUTHORIZED` 명시; 자동 검증만으로 실제 권리 인증 아님 |
| 검증 | 소스 PNG SHA, physics JSONL SHA/size, approval record SHA, 배치 그룹 누수 및 C readiness |

## 실제 release 구조 (생성될 경우)

```text
<private>/release/
  ai/data/manifest.csv
  ai/data/split_manifest.csv          # 충분한 독립 그룹 + C ready 후에만
  ai/data/images/B-*.png             # 승인 및 전처리된 샘플
  source_evidence/physics/*.jsonl     # release root 상대 경로
  source_evidence/original_images/*.png
  source_evidence/approval_ledger.jsonl
  source_evidence/candidate_manifest.csv
  source_evidence/evidence_audit.json
  reports/quality_report.json
  release_manifest.json
  SHA256SUMS
```

C 담당은 read-only로 `ai/train/check_real_data_readiness.py --root ... --split-manifest ... --b-ref 40hex --report ...`를 실행합니다. 실제 훈련·모델 설정은 C가 소유합니다. 승인 0건 또는 각 클래스 독립 그룹 3개 미만이면 정상적으로 `BLOCKED`가 반환돼야 합니다.

B의 provenance는 `capture_config`의 `source_archive_sha256`, `source_image_sha256`, `source_git_sha`, `source_trial_id`, `approval_record_sha256` 등에 있으며, physics path는 release root 기준 상대 경로여서 새 WSL2 위치로 복사한 뒤 다시 SHA로 검증 가능합니다. A/S7/C/D 소스 수정하지 않음.

## 승인 후 C에게 전달할 체크리스트

- A 원본 archive와 SHA / B 원샷 인수 로그 / trial 대표 이미지 개수.
- 운영자 승인 ledger의 사람 식별자·사유·리뷰 시각 / 데이터 이용 권리 근거.
- 승인된 STABLE/UNSTABLE 수 및 독립 그룹 수(각 >=3).
- 누락·중복·경로 이탈·미승인 샘플 0.
- 원본/전처리/물리 SHA 재검 및 C readiness `CONTRACT_READY_HUMAN_REVIEW_REQUIRED`.
- C 사람 검토 및 모델 학습은 별도 승인 후 진행.

현재 이 목록은 충족 전이며 `B_LABEL_APPROVAL_PENDING`, `B_DATASET_SPLIT_BLOCKED`, `C_TRAINING_NOT_RUN` 상태입니다.


## B-10 실증 재검·운영자 검토 인계(2026-11-25)

- 실제 user TAR `(6).gz` 바이트 SHA 일치; B-10 안전 추출 / 내부 88/88 / B-11 각 trial RGB-Pose/물리 JSONL 및 10초 구간 PASS.
- 후보: ST-01/02 각각 `HELD_OBSERVED` → STABLE **추천만**, UN-01/02 `FALL_OBSERVED` → UNSTABLE **추천만**. `label_status=REVIEW_REQUIRED` 4건.
- `review.html` 및 후보 CSV/12 SVG는 **비공개 검토 패키지**로 전달 가능; JSONL 미래 관측값은 C RGB 모델 입력으로 넣지 않습니다.
- 그룹 수: 추천 라벨별 2개씩으로 기존 분할 규정 클래스별 >=3에 부족. 승인 후에도 최초 파일럿만으로 C readiness PASS는 불가.
- 현재 C 핸드오프 완료 여부: `B_EVIDENCE_IMPORT_PASS` **PASS**, `B_LABEL_APPROVAL_PENDING` **HOLD**, `B_DATASET_SPLIT_BLOCKED` **HOLD**. C 모델 학습 NOT_RUN.
- 상세 [실제 TAR 디버깅](../reports/issues/SMARTDISH_B10_DBG_04_REAL_ARCHIVE_EMPTY_DIAGNOSTIC_LOGS_KO.md) 및 [최신 인수 원장](../reports/acceptance/SMARTDISH_B_REAL_DATA_ACCEPTANCE_KO.md).


## B-15 자동 진단 아카이브 인계

B 원샷 실행 성공·실패 시 `ai/data/private/b_a13_diagnostics/*_diagnostics.tar.gz`와 `.sha256`를 생성합니다. 아카이브는 원본 전체 TAR를 내포하지 않으며 검증 로그, B 검토 HTML, PNG 4장, SVG 12개, 물리 JSONL, `diagnostic_status.json`을 포함할 수 있습니다. 내부 `SHA256SUMS` 및 TAR 외부 SHA를 검사한 후 **비공개 전달**하십시오. 이는 디버깅·리뷰용이지 사람 승인 학습 데이터셋 또는 C readiness PASS가 아닙니다.


## B-12R/B-14R 수신 및 C 분할 차단 경계

- B15 Owner 진단 TAR는 54개 정규 파일, 내부 SHA 53/53, 종료코드 0, PNG 4 + SVG 12. 원본 A13 TAR 88개 전체가 아님.
- `ai/scripts/receive_b15_diagnostics.py`로 비공개 폴더에 SHA 검증 후 복원, `B12_REVIEW_DECISIONS_TEMPLATE.csv`는 승인 칸 공란입니다. [운영자 가이드](../guides/SMARTDISH_B12R_REVIEW_OPERATOR_WORKBOOK_KO.md).
- A13 기존 네 scene의 seed 변화는 좌표 ±1mm이므로 독립 배치로 세지 않음. B13은 지정 A13 SHA에서 동일 `source_scene_id`가 다른 `stack_id`로 분리되거나 승인 라벨 충돌하면 C split 전 Fail-Closed 합니다. 추후 A 신규 `physical_layout_id` 계약 필요. [A 요청](../plans/SMARTDISH_B14_REAL_LAYOUT_EXPANSION_REQUEST_KO.md).
- 현 상태: B-15 Owner PASS / B-12R 후보 4 PASS / 운영자 승인 0 / C 데이터셋 split BLOCKED / 모델 학습 NOT_RUN. S2 Robot CI 실패는 별도 E 소유로 인계.


## B12R-DBG-02 — SHA 경로 독립 원샷 출고 및 C 인계 경계

- 이전 워크북의 `sha256sum -c "$ARCHIVE.sha256"`는 호출자 CWD 기준으로 내부 basename을 검사해서 루트에서 파일을 찾지 못했습니다. 사용자 셸의 최상위 `|| exit 1` 때문에 터미널 종료까지 발생했습니다.
- 최종 출고 진입점은 `bash scripts/smartdish_b12r_one_shot.sh --sha <정확한_Git_SHA> --mode review`입니다. 진단 TAR를 SHA가 일치하는 기존 `ai/data/private/b_a13_diagnostics/`에서 자동 검색합니다. Python `read_sidecar()`를 재사용해 CWD 의존 수동 `sha256sum -c`를 제거했습니다.
- 실행 결과는 private `ai/data/private/b12r_diagnostics/*_diagnostics.tar.gz`와 `.sha256`로 무조건 자동 패키징하며, 실패 시에도 CLI 자체 종료코드를 유지하고 사용자 대화형 셸은 종료하지 않습니다. 다른 SHA·파일 손상·승인 위조는 Fail-Closed.
- 검증된 WSL2 B15 원본 진단 TAR SHA `912bfbc759e3fde3f48e70316638bc86dd30c52461ecd19410281bd7edf1f515`; 현재 B12R 신규 버전 로컬 오프라인 검증은 후보 4 / 독립 2+2 BLOCKED / 승인 0. GitHub CI 동일 SHA 및 Owner 실물 결과 별도.
- 코드·QA 상세: [DBG-02](../reports/issues/SMARTDISH_B12R_DBG_02_SHA_RELATIVE_PATH_CWD_KO.md) / [사용자용 원샷 워크북](../guides/SMARTDISH_B12R_REVIEW_OPERATOR_WORKBOOK_KO.md) / [게이트 원장](../reports/acceptance/SMARTDISH_B12R_CLI_PREFLIGHT_ACCEPTANCE_KO.md).

## B-DATA-QA-01 — 사용자 DACON v1.0 기준 인계 (2026-11-25)

- 적용 문서: [DACON 품질 기준선 v1.0](../quality/SMARTDISH_B_DACON_DATA_QUALITY_BASELINE_20261125_KO.md); 384×384 front/top·0.015m은 비교 후보로만 유지. DACON audit ZIP 원본은 이번 작업에서 독립적으로 재검증하지 않았습니다.
- B QA 실행기: `scripts/smartdish_b_dacon_qa01_one_shot.sh --sha <exact code SHA> [--workspace ...] [--source-archive ...]`. 기존 B12R raw+review 재사용; 원본 A13 전체 TAR 공급 시 B-Q01 SHA 88/88 직접 검증. 전체 TAR 없으면 Q01 HOLD.
- 실제 결과: B-Q01 **PASS**, B-Q02~B-Q07 **HOLD**. 원본 640×480 RGB4, t0 0.60s/pose0.55s, SDF camera pose, WORLD frame trajectory; tray-relative/velocity/contact 미완성, 사람 승인0, 4 fixed scenes/독립 커버리지 부족, approved split 없음. 모델 학습 NOT_RUN.
- 소스 및 임계치: `0.015m` 누적 기준은 미승인 후보이며 WORLD-frame displacement는 tray 상대 변위와 다릅니다. 뒤따르는 물리 trace는 C RGB inference feature가 아니라 GT 검토 증거입니다.
- A 담당: tray 상대 Pose·contact·velocity 동기화와 새로운 geometry/환경 클래스 교차 장면 수집 계획. B 담당: 오프라인 SHA·형상/중복/사람 승인·그룹 누수 검증, C 담당: 승인된 manifest만 읽기 전용 재검 후 학습. [Gate 원장](../reports/acceptance/SMARTDISH_B_DATA_QA01_ACCEPTANCE_20261125_KO.md).
