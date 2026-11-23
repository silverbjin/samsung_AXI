# SmartDish B → C/E 핸드오프 (2026-11-23)

- 저장소: `silverbjin/samsung_AXI`; base `main@2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`.
- B 브랜치: `feat/smartdish-b-dataset`. 정확한 HEAD: `git rev-parse HEAD` 또는 GitHub 브랜치에서 조회. Draft PR: GitHub 본문 확인.
- B 소유: 데이터 카탈로그/스키마, 적재 안정성 라벨 정의, 수집기, 품질 검사, 스택 그룹별 재현 분할.
- C 소유: 학습/추론, `STABLE/UNSTABLE/UNKNOWN` 반환, 정확도·threshold·정규화 결정.
- 데이터 카드: [`ai/docs/DATASET_CARD_KO.md`](../../ai/docs/DATASET_CARD_KO.md)
- 사용 가이드: [`ai/docs/B_DATA_USAGE_KO.md`](../../ai/docs/B_DATA_USAGE_KO.md)
- 라벨: `STABLE=0`, `UNSTABLE=1`; `UNKNOWN`은 추론 상태이며 **학습 라벨 아님**.
- 입력: PNG RGB 224×224; PIL EXIF 보정, RGB 변환, `ImageOps.fit` BILINEAR. `capture_config` 확인; C의 학습 및 추론 정규화 동일 적용.
- 현재 실제 데이터 수: **0**, 재배포 승인된 실제 트레이 이미지: **0**, DACON ZIP 다운로드/검수: **NOT_RUN**. 합성 fixture 6개는 `MOCK_ONLY`.
- 현실적 블로커: A의 트레이 지향 실제 카메라/물리 장면 및 운영자 확인 라벨, C와 1장 실물 샘플 합동 검토.

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
