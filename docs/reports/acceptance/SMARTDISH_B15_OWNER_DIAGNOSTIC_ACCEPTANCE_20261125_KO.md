# SmartDish B-15 — WSL2 Owner 진단 아카이브 인수 기록

- 판정: **B-15 USER WSL2 DIAGNOSTIC ACCEPTANCE PASS** (코드 SHA `eae0e8553762addafb66fcee4ae8dd39b75d971f`).
- 인수 원본: 사용자 첨부 `smartdish_b_a13_20261125T055624Z_6624_diagnostics.tar.gz` + `.sha256`.
- 압축 SHA256: `912bfbc759e3fde3f48e70316638bc86dd30c52461ecd19410281bd7edf1f515` — sidecar와 직접 계산 일치.
- TAR 구성 54개 정규 파일; 진단 `SHA256SUMS`의 **53/53 직접 PASS**. 첨부 TAR는 B-15 진단 **부분집합**이며, A-13 원본 압축파일 전체 88개가 이 ZIP/TAR에 모두 실려 있는 것은 아님.
- `diagnostic_status.json`: `RUN_SUCCESS`, `exit_code=0`, `git_sha=eae0e855...`, `candidate_review_only=true`, `human_approved_labels=null`.
- 로그에 기록된 A-13 원본 SHA `bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e`, 이전 B-10 원본 무결성 88/88 PASS, B-11 `SMARTDISH_B_REAL_CANDIDATE_EXTRACTION_PASS 4`, 물리 감사 PASS 확인.
- B-15 진단 TAR에 실제 `raw/trial_0001..0004/tray_rgb.png` 4장, Pose/physics JSONL, `review/review.html`, SVG 12개, `candidate_manifest.csv`가 모두 포함됨. 최종 사용권·사람 라벨 **승인 0**.

| 단계 | 판정 |
|---|---|
| B15 진단 아카이브 SHA | PASS |
| B15 내부 53/53 | PASS |
| B15 실행 성공·종료코드 | PASS |
| 기존 B10 TAR 직접 SHA 88/88 | 이전 B-10 + 이번 사용자 로그에서 PASS, 진단 부분집합만으로 재계산한 것은 아님 |
| B12 운영자 검토 workspace | 준비 가능 / 실제 사용자 승인 대기 |
| B13 승인 manifest | NOT_RUN (승인 0) |
| B14 독립 그룹 | STABLE 후보 2 / UNSTABLE 후보 2, BLOCKED |
| C 모델 학습 | NOT_RUN |

## 주의: 이 인수가 증명하지 않는 것

- PNG 4개는 미래 물리 결과를 자동으로 승인한 라벨이 아님.
- 시뮬레이션 영상·물리 trace의 존재는 A의 과거 WSL2 시험을 대체하는 새 로봇 안전 인증이 아님.
- 사람 승인 및 C의 train/val/test 독립 그룹 조건은 여전히 남음.
- 생성된 진단 ZIP/TAR는 개인 경로·영상·물리 데이터를 포함할 수 있으므로 공개 Git에 첨부하지 않고 검증 숫자·코드·비공개 참조만 저장.
