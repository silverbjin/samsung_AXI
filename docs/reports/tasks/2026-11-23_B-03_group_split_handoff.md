# B-03 — 품질 검사·물리 배치 분할·C 인계

- 기준: S7 `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894` / B-01, B-02 이어서 수행
- 작업 커밋: 본 문서와 동일한 Git 커밋; Draft PR은 리뷰용, main 미병합.
- **PASS: 로컬 데이터 계약 테스트 10개 / 실제 데이터·Gazebo·C 학습 NOT_RUN**.

## 기능과 이유

- `ai/scripts/prepare_dataset.py`: 필수 컬럼·PNG/ RGB/224·SHA·출처/권리·라벨·scene/stack 무결성 검사, 동일 stack_id 그룹의 train/val/test 분할.
- `tests/test_b_dataset.py`: `STACKED` 거부, 중복·변조·누락·scene/stack 레이블 모순·검증 그룹 부족을 실제 예외로 점검.
- `docs/handoff/B_HANDOFF.md`: C가 필요한 파일, 명령, label_map, 남은 외부 의존성.
- `docs/handoff/B_DATA_PIPELINE_EDU_KO.md`: 요구사항→설계→검증→인계 교육 보고.

## 명령 및 관찰

```bash
python3 -m pytest -q tests/test_b_dataset.py
python3 ai/scripts/prepare_dataset.py --make-fixtures /tmp/smartdish_b_fixtures
python3 ai/scripts/prepare_dataset.py --manifest /tmp/smartdish_b_fixtures/manifest.csv --root /tmp/smartdish_b_fixtures --out /tmp/smartdish_b_fixtures/split.csv --report /tmp/smartdish_b_fixtures/quality.json --allow-fixtures
python3 -m compileall -q ai/scripts tests
```

- 로컬 관찰: **10 passed in 0.22s**, fixture 6건, 클래스별 3개 그룹/ train·val·test 각각 한 그룹, 중복 0. 모두 `MOCK_ONLY`.
- 안전 차단 재검: 위 준비 명령에서 `--allow-fixtures` 제외 시 `B_GROUND_TRUTH_NOT_OBSERVED row=2`로 실패 확인. 이 실패는 정상이며 train 데이터로 오용할 수 없음.
- 이슈: `test_group_conflict_rejected` 오류 우선순위 충돌 → [B-DEBUG-01](../issues/2026-11-23_B-DEBUG-01_validation_error_priority.md) 최소 수정 후 10 PASS.
- 테스트 환경: 이 작업 컨테이너 Python 3 / Pillow 12.3.0 / pytest 9.0.2. **ROS/Gazebo/WSL2/Actions NOT_RUN**.

## 훈련생 질문·다음 경계

연속 프레임을 서로 다른 split에 넣으면 왜 test 정확도가 높게 왜곡됩니까? A의 트레이 카메라 및 물리 관찰 데이터 준비 후 1건 수집하고 C와 원본+label_map 합의합니다.
