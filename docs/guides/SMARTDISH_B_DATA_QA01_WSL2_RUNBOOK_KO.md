# SmartDish B-DATA-QA-01 — WSL2 원샷 및 판정 실습 가이드

## 실행 조건

- GitHub `feat/smartdish-b-real-dataset` 최신 검증된 SHA, 별도 B checkout `~/samsung_AXI_B_REAL`.
- 이미 수집한 A13 전체 원본 TAR는 `~/samsung_AXI_A_TRAY/generated/smartdish_tray/run_*/smartdish_a_tray_evidence.tar.gz` 또는 `--source-archive`의 실제 경로.
- B12R 작업 폴더 `ai/data/private/b12_operator_review_*`의 `raw/`, `review/`. 신규 Gazebo/SLAM/ROS 실행 불필요.
- 소스 코드 SHA를 최종 PR HEAD로 핀합니다. 문서에 임시 SHA를 고정하지 않습니다.

## 배포 명령(최종 승인된 SHA로만 수정)

```bash
(
  set -Eeuo pipefail
  cd "$HOME/samsung_AXI_B_REAL"
  PIN="<최신_검증된_40자리_B_SHA>"
  git fetch origin feat/smartdish-b-real-dataset
  git merge --ff-only "$PIN"
  bash scripts/smartdish_b_dacon_qa01_one_shot.sh --sha "$PIN"
)
```

**원샷 내부에서 Git SHA·원본 TAR·기존 B12R 작업폴더를 검증**합니다. 원본 TAR가 조회되지 않으면 B-Q01은 HOLD(다른 항목 감사 계속). `--source-archive`와 `--workspace`에 정확한 경로를 지정하면 명시적 검수가 가능합니다. 이 명령은 자식 셸에서 실행되어 오류 시 부모 터미널을 종료하지 않습니다. HTML만 개별 추출한 경우가 아니라 검증된 B12R 폴더를 사용해야 합니다.

## 수집 파일과 결과를 읽는 순서

1. `B_QA_CODE_SHA_PIN_PASS`가 현재 checkout Git HEAD와 일치하는지 확인합니다.
2. `B-Q01=PASS`는 실제 A13 원본 TAR 88개가 재검된 경우에만 기대합니다. 원본이 없으면 HOLD가 정확합니다.
3. `B-Q02~B-Q07=HOLD`는 현재 4장면 파일럿에서 정상적인 품질 보류입니다.
4. 자동 생성된 `B_QA_PRIVATE_RUN_DIR` 아래 `qa/qa_report.json`과 CSV/PNG를 엽니다. 디지털 파이프라인 검수와 데이터셋 최종 출고를 혼동하지 마십시오.
5. `B_QA_DIAGNOSTIC_ARCHIVE_CREATED` TAR.GZ 및 `.sha256` 두 파일을 비공개로 전달합니다. GitHub 공개 PR에 이미지·Pose 원본을 업로드하지 마십시오.

## 비정상 결과

- `B_QA_CODE_SHA_PIN_MISMATCH`: 실행 코드와 명령 PIN 불일치. 자동 update/force push 금지.
- `B_QA_WORKSPACE_NOT_FOUND`: 검증된 B12R `raw/`와 `review/`가 없음. 기존 증거 재사용/인수 실패 확인.
- `B_Q01_ORIGINAL_ARCHIVE_SHA_MISMATCH`: A13 원본의 다른 SHA. B-Q01 HOLD; 임의 TAR를 원본으로 바꾸지 않음.
- `B_QA_CANDIDATE_SHA_DRIFT`: PNG·물리 원본 불일치. 감사 FAIL·증거 보존.
- `B_QA_DIAGNOSTIC_ARCHIVE_FAILED`: 진단 생성 실패 시 private 실행 폴더와 원인 확인.

## 배포 전 QA 체크리스트

- [ ] `bash -n` 셸 문법 / Python 컴파일 PASS
- [ ] 다양한 CWD·공백 괄호 경로에서 한 번에 실행 PASS
- [ ] 원본 A13 TAR 직접 재검(가능 시) / 그 외 Q01 HOLD
- [ ] SHA·경로 이탈·샘플 변조·중복 / 오류 주입 PASS
- [ ] 기존 B 119개 회귀 테스트 제거 없이 PASS
- [ ] 같은 최종 B SHA의 GitHub B CI SUCCESS
- [ ] 실제 파일럿 4장면 B-Q01~07 판정 원장 보존
- [ ] 대표 이미지/CSV/증거 SHA 모두 private로 보관
- [ ] WSL2 Owner 실행은 Owner 로그가 와야 PASS로 승격
