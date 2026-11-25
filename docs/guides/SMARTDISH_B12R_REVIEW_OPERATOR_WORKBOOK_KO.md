# SmartDish B-12R — WSL2 운영자 리뷰·B-13 인계 실습 워크북

## 0. 현재 완료/미완료

- 사용자 2026-11-25 B15 진단 TAR와 SHA: 53/53 PASS, 실행 `exit_code=0`, 후보 4개, 실제 이미지/물리 궤적 보존.
- 운영자 라벨 승인 **0건**. ST/UN은 A 자동 물리 관측이며 승인된 정답 아님.
- 클래스별 독립 원본 물리 레이아웃 **2 / 2**로 C 분할 차단; 이번 실습은 AI 학습을 하지 않습니다.

## 1. GitHub 코드 SHA 고정 및 원본 진단 아카이브 재사용

기존 작업공간을 버리거나 Gazebo를 재실행하지 마십시오. `--archive`로 B-15 원본 **진단 TAR**을 입력합니다. A-13 전체 TAR를 이 CLI에 넣으면 안 됩니다.

```bash
cd ~/samsung_AXI_B_REAL
PIN="$(git rev-parse HEAD)"
# 새 commit 적용 후에는 반드시 PIN을 실제 배포 SHA로 고정하여 입력
ARCHIVE="$(find "$PWD/ai/data/private/b_a13_diagnostics" -maxdepth 1 -type f \
  -name 'smartdish_b_a13_*_diagnostics.tar.gz' -printf '%T@ %p\n' \
  | sort -n | tail -1 | cut -d' ' -f2-)"
test -f "$ARCHIVE"
sha256sum -c "$ARCHIVE.sha256"
OUT="$PWD/ai/data/private/b12_operator_review_$(date -u +%Y%m%dT%H%M%SZ)_$$"
python3 ai/scripts/receive_b15_diagnostics.py \
  --archive "$ARCHIVE" --sha256-file "$ARCHIVE.sha256" --output "$OUT"
python3 ai/scripts/audit_a13_independent_groups.py \
  --candidate-manifest "$OUT/review/candidate_manifest.csv" \
  --report "$OUT/B14_INDEPENDENCE_AUDIT.json"
cat "$OUT/B12_REVIEW_RECEIPT.json"
cat "$OUT/B14_INDEPENDENCE_AUDIT.json"
```

이 작업은 `RUN_SUCCESS`, 내부 53개 SHA, 후보 원본 PNG·physics 개별 SHA를 실제로 재검합니다. 진단 TAR는 **A 원본 88개 전체를 포함하지 않는** 검토용 부분집합입니다.

## 2. 이미지·그래프와 물리 정답 근거 확인

`$OUT/review/review.html`을 Windows 브라우저로 열어 이미지와 z/tilt/XY 시계열을 확인합니다. 원본과 물리의 미래 관측값은 **정답 검토용**이며 C RGB 모델 입력으로 사용하면 안 됩니다.

| 장면 | candidate_id | 자동 관측 | 추천(미승인) |
|---|---|---|---|
| ST-01 | `B13-e7d88ff434e61ef45a3d` | HELD_OBSERVED | STABLE |
| ST-02 | `B13-1a7814fbd21a93239ca1` | HELD_OBSERVED | STABLE |
| UN-01 | `B13-18d55d6968c4548e77ba` | FALL_OBSERVED | UNSTABLE |
| UN-02 | `B13-95f2a62dcbe847317439` | FALL_OBSERVED | UNSTABLE |

이 ID는 이번 사용자 원본에 실제 기록된 값이며 재수집 시 변경될 수 있습니다. 명령에는 현재 출력 CSV의 ID를 사용해야 합니다.

## 3. 사람의 명시적 결정만 등록합니다

`$OUT/B12_REVIEW_DECISIONS_TEMPLATE.csv`에는 승인 칸이 **전부 비어 있습니다**. 이 파일을 수정해도 자동 승인되지 않습니다. 승인하려면 실제 운영자가 아래 CLI의 `candidate-id`, `reviewer-id`, `decision`, `reason`, `license-status`를 직접 입력해야 합니다.

```bash
# 예: 보류 결정을 별도 기록하는 방법(실제 결정을 내렸을 때만)
python3 ai/scripts/review_a13_labels.py \
  --review-dir "$OUT/review" --raw-dir "$OUT/raw" \
  --candidate-id 'B13-e7d88ff434e61ef45a3d' \
  --reviewer-id '운영자_ID_직접입력' \
  --decision DEFERRED --reason '영상 및 물리 증거 재검토' \
  --license-status UNVERIFIED
```

승인하려면 `--decision APPROVED`, `--approved-label STABLE` 또는 `UNSTABLE`, `--license-status OWNED` 또는 `AUTHORIZED`와 근거를 명시해야 합니다. AI가 이 명령을 대신 실행하지 않습니다. 중복 승인·원본 SHA 변경·시간 불확실 데이터는 차단됩니다.

## 4. B-13 승인 0건은 정상 HOLD입니다

```bash
python3 ai/scripts/register_a13_approved.py \
  --raw-dir "$OUT/raw" --review-dir "$OUT/review" \
  --release-root "$OUT/no_approval_check" \
  --b-ref "$(git rev-parse HEAD)"
```

**승인 0건**이면 `B_LABEL_APPROVAL_PENDING`과 품질 JSON만 만들고, 이미지·학습 manifest·split은 생성하면 안 됩니다. 실제 승인 후 별도 release 경로를 지정해 B-13을 실행합니다. 최초 네 후보를 모두 승인하더라도 **클래스별 독립 템플릿이 2개씩**이라 `B_DATASET_SPLIT_BLOCKED`가 정상입니다.

## 5. 교육 회고

- TAR Sidecar SHA/내부 SHA/후보 이미지 SHA는 별도 검증 층입니다.
- 같은 seed가 아닌 **다른 seed**라도 A의 초기 geometry가 약 ±1mm jitter일 뿐이면 새로운 적재 구성이 아닙니다.
- GitHub CI PASS는 실제 승인·C 학습 승인·전체 레스토랑 CI PASS와 별개의 검증입니다.
- 실험 원본은 private 저장하고, 공개 PR에는 코드·교육용 합성 fixture·검증 통계만 게시합니다.
