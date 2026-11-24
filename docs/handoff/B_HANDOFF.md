# SmartDish B → C/E 핸드오프 (2026-11-23)

- 저장소: `silverbjin/samsung_AXI`; base `main@2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`.
- B 브랜치: `feat/smartdish-b-dataset`. [Draft PR #37](https://github.com/silverbjin/samsung_AXI/pull/37) → `main` (병합 금지). **검증된 코드 SHA** `32722c3a7e5361d20659e7116894c35b89b629d2`; 최종 HEAD는 문서 보강 커밋 때문에 다를 수 있으므로 GitHub PR head 및 `git rev-parse HEAD` 확인.
- B 소유: 데이터 카탈로그/스키마, 적재 안정성 라벨 정의, 수집기, 품질 검사, 스택 그룹별 재현 분할.
- C 소유: 학습/추론, `STABLE/UNSTABLE/UNKNOWN` 반환, 정확도·threshold·정규화 결정.
- 데이터 카드: [`ai/docs/DATASET_CARD_KO.md`](../../ai/docs/DATASET_CARD_KO.md)
- 사용 가이드: [`ai/docs/B_DATA_USAGE_KO.md`](../../ai/docs/B_DATA_USAGE_KO.md)
- 라벨: `STABLE=0`, `UNSTABLE=1`; `UNKNOWN`은 추론 상태이며 **학습 라벨 아님**.
- 입력: PNG RGB 224×224; PIL EXIF 보정, RGB 변환, `ImageOps.fit` BILINEAR. `capture_config` 확인; C의 학습 및 추론 정규화 동일 적용.
- 현재 실제 데이터 수: **0**, 재배포 승인된 실제 트레이 이미지: **0**, DACON ZIP 다운로드/검수: **NOT_RUN**. 합성 fixture 6개는 `MOCK_ONLY`.
- 검증: 로컬 `10 passed in 0.22s`, [GitHub Push CI #45120166614](https://github.com/silverbjin/samsung_AXI/actions/runs/45120166614) `10 passed in 0.17s`, [PR CI #45120198336](https://github.com/silverbjin/samsung_AXI/actions/runs/45120198336) PASS.
- B-05 신규 무라벨 캡처: `ai/scripts/capture_tray_ros.py`, [사용가이드](../../ai/docs/B_TRAY_CAPTURE_GUIDE_KO.md), topic `/smartdish/tray/image_raw`, private PNG+JSON. 실제 ROS 런은 NOT_RUN.
- B-06 증거 유효성 강화: 미존재/빈 파일/캡처 이미지 자체는 증거로 거부, `capture_config.physics_evidence_sha256` 기록. [RED→GREEN 보고](../reports/issues/2026-11-23_B-DEBUG-02_unverified_evidence_reference.md).
- B-05/06 로컬 계약 검사: `python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py tests/test_b_tray_capture.py` → **15 passed in 0.22s**. 본 숫자는 실제 트레이 데이터·ROS2/모델 성능이 아님.
- 현실적 블로커: A의 트레이 지향 실제 카메라/물리 장면 및 운영자 확인 라벨, C와 1장 실물 샘플 합동 검토.

- B-07: 실제 라벨 데이터가 추가되면 `prepare_dataset`의 **근거 파일 현시점 SHA/크기 재검** 통과가 C 인계 전 조건입니다. 보고서 `evidence_hash_verified`로 파일 검증 건수만 확인합니다. [B-DEBUG-03](../reports/issues/2026-11-23_B-DEBUG-03_evidence_drift.md). 이번 단계 실제 데이터 0건, 실물 검증 NOT_RUN.

- B-08: 원자적 CSV 저장·PNG 롤백과 미색인 파일 덮어쓰기 방어. 단일 운영자/순차 입력 전제, CI는 23개 Python 계약 테스트. [개발 보고서](../reports/tasks/2026-11-23_B-08_atomic_intake.md), [이슈](../reports/issues/2026-11-23_B-DEBUG-04_orphan_ingest.md). 실제 트레이 0건 유지.

- B-09: C가 실학습에 사용할 때는 `--allow-fixtures`를 **절대 사용하지 않습니다**. 이 옵션은 단색 mock fixture 전용이며 실데이터 혼합 시 `B_FIXTURE_MODE_REAL_DATA_FORBIDDEN`으로 거부합니다. [보고서](../reports/tasks/2026-11-23_B-09_mock_real_isolation.md).

## C 담당 재현 명령

```bash
python3 -m pytest -q tests/test_b_dataset.py
python3 ai/scripts/prepare_dataset.py --make-fixtures /tmp/smartdish_b_fixtures
python3 ai/scripts/prepare_dataset.py --manifest /tmp/smartdish_b_fixtures/manifest.csv \
  --root /tmp/smartdish_b_fixtures --out /tmp/smartdish_b_fixtures/split.csv \
  --report /tmp/smartdish_b_fixtures/quality.json --allow-fixtures
```

C는 위 명령을 **인터페이스 포맷 검증**으로만 사용하고 모델을 학습하지 않습니다. 실제 데이터가 B의 manifest에 채워진 뒤 `--allow-fixtures` 없이 `prepare_dataset.py` 실행 및 split 중복 0 확인을 한 다음 모델 학습을 시작합니다. C가 B 파일을 자기 브랜치에 중복 커밋하지 않습니다.

## 통합 계약/가드

D의 `/collection/stability`는 C 출력이며 B는 ROS 토픽을 발행하지 않습니다. `UNKNOWN`/미응답/불안정인 경우 D는 직원 확인을 요구하고, AI OFF 시연은 본 데이터와 무관하게 진행합니다. **B Draft PR은 main 병합하지 않습니다.**

## B-08R — 중단 잔재·동시 수집 대응 (2026-11-23)

- B-08의 원자적 CSV 교체는 유지하고 `collect_tableware.py`에 동일 manifest `fcntl.flock` 배타 잠금(`B_COLLECTOR_BUSY`) 추가. Ubuntu/WSL2 한정이며 잠금 파일은 삭제하지 않습니다.
- 원본 manifest에 없는 `B-*.png`, `.incoming-*`, `.b-csv-*`는 `B_ORPHAN_FILES_DETECTED`로 차단하고 자동 삭제하지 않습니다. 운영자가 SHA/원본 확인 후 `ai/data/private/quarantine`으로 수동 격리합니다. 동일 목적지 파일의 기존 `B_IMAGE_DEST_EXISTS_NOT_IN_MANIFEST` 오류도 유지합니다.
- [후속 작업 보고서](../reports/tasks/2026-11-23_B-08R_writer_lock_orphan_recovery.md) / [디버깅 B-DEBUG-06](../reports/issues/2026-11-23_B-DEBUG-06_concurrent_orphan_recovery.md). 로컬 **30/30 PASS**, GitHub 최신 Run은 PR #37의 Actions 확인. 실제 안정성 이미지 **0건**.
- 오프라인 전체 계약 검사: `python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py tests/test_b_intake_recovery.py`
