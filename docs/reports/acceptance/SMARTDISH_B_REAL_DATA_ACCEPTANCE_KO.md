# SmartDish B A-13 데이터 인수 및 C 출고 검증 원장 (2026-11-25)

- Git 기준: `main 63e147289e307e0b9900ca365e9c4557c5921804` (A PR45+B PR37 병합), A 실행 코드 `6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df`.
- 기대 원본 TAR SHA256: `bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e`.
- **원본 TAR 현재 작업 환경에서 없음.** 이 SHA는 이전 A-13 인수 보고서의 명세이고 이번 B에서 재계산한 사실이 아님.
- 실제 운영자 승인 라벨: 0. 이미지 추출·물리 그래프 실제 생성: `NOT_RUN`.

| B Gate | 상태 | 확인 근거와 경계 |
|---|---|---|
| G01 출처 A SHA | A 기록 확인 | A 원본 바이트와 trial 별 재검 `BLOCKED` |
| G02 Archive SHA | `NOT_RUN` | TAR 없음 |
| G03 SHA256SUMS 88/88 | `NOT_RUN` | 이전 A 보고서 88/88과 구별 |
| G04 PNG 원본·해시 | `NOT_RUN` | 실제 TAR 없음 |
| G05 Physics·Pose·JSONL | `NOT_RUN` | 실제 TAR 없음 |
| G06 시간 정렬 | A 기록 50ms | B 원본 직접 재계산 `NOT_RUN` |
| G07 실제 4개 후보 | `BLOCKED` | 후보 검증 0건 |
| G08 사람 리뷰 기능 | 로컬/CI 계약 검증 결과 참조 | 원본 리뷰 생성 미실행 |
| G09 승인 | `B_LABEL_APPROVAL_PENDING` | 승인 0 |
| G10 기존 B 등록 | 계약 테스트 가능 | 실물 등록 0 |
| G11 독립 그룹 분할 | `B_DATASET_SPLIT_BLOCKED` | 예상 pilot 클래스별 최대 2그룹 |
| G12 C readiness | 실제 데이터 `BLOCKED` | 독립 그룹/승인 부족 |
| G13 S7·A‑13 보존 | 변경 없음(파일 diff 확인) | 새 물리 구동/재주행 없음 |
| G14 CI | 코드 commit 후 실제 Run 링크 보강 | fixture-only PASS ≠ owner 실물 PASS |
| G15 보고서·Draft PR | 신규 B branch / Draft PR에서 확인 | main 병합 미진행 |

**코드 구현 완료 상태와 실데이터 수집 상태는 별개입니다.** 원본 증거를 받은 뒤 실측값·검증된 후보·운영자 승인·독립 그룹 수·C 결과를 본 원장에 업데이트할 수 있습니다. 증거가 없는 칸을 A의 과거 수치로 대체하지 마십시오.
