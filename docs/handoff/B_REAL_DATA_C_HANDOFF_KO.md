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
