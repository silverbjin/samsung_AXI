# B 담당 데이터 파이프라인 실습 안내 (초심자용)

## 0. 왜 필요한가

S7의 접시가 있는 상태와 적재가 물리적으로 안정한 상태는 다릅니다. 카메라 RGB가 형식상 유효하더라도 낙하/지지면 확인이 없으면 정답 라벨이라고 할 수 없습니다. B는 모형 개발 C에게 데이터를 **파일**로 전달하며 ROS 임무 토픽에 관여하지 않습니다.

## 1. 개발 환경

Ubuntu 24.04 또는 일반 Python 3.10+, Pillow, pytest. ROS/Gazebo는 오프라인 스모크에 불필요합니다.

```bash
# 저장소 루트에서
python3 -m pip install --user Pillow pytest
python3 -m pytest -q tests/test_b_dataset.py tests/test_b_tray_capture.py
python3 ai/scripts/prepare_dataset.py --make-fixtures /tmp/smartdish_b_fixtures
python3 ai/scripts/prepare_dataset.py --manifest /tmp/smartdish_b_fixtures/manifest.csv \
  --root /tmp/smartdish_b_fixtures --out /tmp/smartdish_b_fixtures/split.csv \
  --report /tmp/smartdish_b_fixtures/quality.json --allow-fixtures
```

예상 로그: `B_MOCK_ONLY_FIXTURES_CREATED`, `B_DATASET_CONTRACT_PASS`. **합성 이미지 6건은 모델 학습 정답이 아닙니다**. `--allow-fixtures`를 빼면 `B_GROUND_TRUTH_NOT_OBSERVED`로 실패해야 올바릅니다.

## 2. 실제 데이터 수집 — A 카메라가 준비된 후에만

A가 트레이를 촬영한 원본 파일과 시뮬레이션 전후 물리 상태 기록(낙하/전도/지지)을 제공해야 합니다. 그 다음 운영자가 직접 라벨을 확인하고 등록합니다.

```bash
python3 ai/scripts/collect_tableware.py --image /path/to/tray_capture.png \
  --label STABLE --scene-id scene-A1 --stack-id stack-A1 \
  --source GAZEBO_TRAY --license-status OWNED \
  --physics-evidence /path/to/after_settle_pose_or_video.log \
  --camera /smartdish/tray/image_raw --root . --manifest ai/data/manifest.csv
python3 ai/scripts/prepare_dataset.py --root . \
  --manifest ai/data/manifest.csv --out ai/data/split_manifest.csv \
  --report ai/data/quality_report.json
```

**주의**: 위 `--image` / `--physics-evidence` 경로는 예시이며 현재 실제 파일은 없습니다. B-06부터 `--physics-evidence`는 실제 존재하는 독립·비어 있지 않은 파일이어야 하고 SHA-256 및 크기를 기록합니다. 파일의 진위와 물리 안정성은 자동 인증하지 않으므로 C가 학습하기 전 사람이 라벨/증거를 검토해야 합니다. 원본 `images/`·`private/`는 Git 무시 대상입니다. ROS 이미지 1장 캡처 절차는 [`B_TRAY_CAPTURE_GUIDE_KO.md`](B_TRAY_CAPTURE_GUIDE_KO.md)에 정리했습니다.

### B-07 인계 직전 근거 재감사

수집 시 저장한 근거 파일의 SHA/크기를 **데이터 준비 시에도** 대조합니다. 관측 로그를 삭제·수정한 경우 무조건 PASS로 승격하지 않으며, 원본을 복구하고 다시 검증해야 합니다. 실행 명령은 기존 `prepare_dataset.py` 그대로이며 실제 카메라·물리 관측은 별도의 선행 조건입니다.

## 3. 결과 읽기와 디버깅

- `B_PHYSICS_EVIDENCE_MISSING` / `B_PHYSICS_EVIDENCE_SHA_MISMATCH`: 등록 당시 관측 파일이 유실/변조됐습니다.\n- `B_PHYSICS_EVIDENCE_METADATA_INVALID`: 관측 참조 또는 SHA/크기 필드 누락/형식 오류입니다.\n- `B_INVALID_LABEL`: `STACKED` 등 틀린 라벨 → 물리 판정이 있는 `STABLE/UNSTABLE`만 등록
- `B_IMAGE_MISSING` / `B_IMAGE_CORRUPT`: 경로/원본 파일 점검
- `B_DUPLICATE_IMAGE`: 해시 동일 → 연속 프레임 중복 제거
- `B_SCENE_SPANS_STACKS`: scene_id 하나가 여러 적재 배치를 나타냄 → 배치마다 scene_id 분리
- `B_STACK_LABEL_CONFLICT`: 같은 stack_id의 라벨이 모순 → 물리 관측 근거로 재라벨링
- `B_INSUFFICIENT_INDEPENDENT_GROUPS`: 학습·검증·시험에 필요한 별개의 stack 그룹 부족 → 물리 표본 수집 후 재실행

- `B_PHYSICS_EVIDENCE_FILE_MISSING` / `B_PHYSICS_EVIDENCE_EMPTY`: 관측 파일을 생성하고 사람 검토 후 재등록
- `B_TRAY_CAMERA_TIMEOUT_NO_IMAGE`: A의 전용 트레이 RGB 토픽 준비 확인 (S7 기본 전방 카메라를 대체로 사용 금지)

오류 발생 시 첫 메시지·원본 파일 SHA·재현 명령만 남기고 다른 개발자의 소스를 변경하지 않습니다. 커밋 전에 `git status --short`로 외부 데이터가 추적되지 않는지 확인하십시오.

## 4. C 담당의 계약 수신

`ai/data/split_manifest.csv`, `ai/docs/DATASET_CARD_KO.md`, 이 문서, SHA와 품질 보고를 받습니다. 같은 파일을 C 브랜치로 복사해 중복 수정하지 않고, **B Draft PR 리뷰 후 통합 담당이 B를 먼저 병합**합니다. 실제 데이터 0건이므로 C의 실제 모델 학습/성능은 아직 불가합니다.
