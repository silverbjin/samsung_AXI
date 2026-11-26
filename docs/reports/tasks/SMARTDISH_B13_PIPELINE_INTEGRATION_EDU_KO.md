# B-13 교육 보고 — 기존 B collector/prepare_dataset와 C readiness의 접점

- 기존 재사용: `ai/scripts/collect_tableware.py`, `ai/scripts/prepare_dataset.py`, `ai/train/check_real_data_readiness.py`.
- A 모델·Gazebo·ROS 및 C 모델 소스 불변. 신규 B 전용 adapter: `ai/scripts/register_a13_approved.py`.

## 계약

```text
원본 PNG(640×480) → B 기존 ImageOps.exif_transpose→RGB→ImageOps.fit 224×224 BILINEAR
물리 JSONL 원본 해시      ↗       기존 manifest 10열 / split 11열 유지
approval_ledger SHA      ↗       capture_config JSON에 provenance 추가
```

`a13_provenance`라는 **선택형 keyword 인자**만 기존 `collect()`에 추가합니다. 다른 수집 경로의 기본 동작·CLI 인자는 유지합니다. A 전용 경로에서는 원본 이미지 SHA, TAR SHA, A 실행 SHA, 승인 레코드 SHA를 중첩 `capture_config` 안에 넣고, 동일 release root 내의 물리 증거를 **상대 경로**로 기록합니다. B와 C 모두 `root` 기준으로 물리 증거를 다시 해시합니다. 절대 경로 의존성은 기본 기존 호출에서는 유지되며 변경하지 않습니다.

승인 원장이 없으면 **학습 manifest 자체를 생성하지 않습니다**. 승인된 데이터만 기존 B 등록기로 전처리·SHA/중복·원자적 CSV 처리 후 등록합니다. 4개 파일럿은 클래스별 독립 그룹 3개 미달이므로 `B_DATASET_SPLIT_BLOCKED`가 정상입니다.

## 교차 테스트

```bash
python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py \
  tests/test_b_intake_recovery.py tests/test_b_a13_real_data.py
```

C readiness를 검사하되 `CONTRACT_READY_HUMAN_REVIEW_REQUIRED`는 추가 사람 검토가 필요하다는 의미입니다. AI 모델 학습/정확도/실제 주행은 이 단계에서 검증하지 않습니다.

**주니어 질문:** `source_image_sha256`과 `image_sha256`이 서로 다른 이유는 무엇입니까? 하나는 A 원본 640×480, 다른 하나는 B 전처리 224×224이기 때문입니다.
