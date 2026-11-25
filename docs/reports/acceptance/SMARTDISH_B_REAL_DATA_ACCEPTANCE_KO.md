# SmartDish B A-13 실제 데이터 인수 및 C 출고 검증 원장 — 2026-11-25 개정

## 기준과 증거 경계

- A 실행 소스 SHA: `6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df`.
- A 원본의 이전 사용자 WSL2 인수: 4/4 PASS (A 보고서).
- B가 **이번에 직접 읽어 재계산**한 파일: 첨부 `smartdish_a_tray_evidence.tar(6).gz`. Archive SHA256은 원래 A 보고서의 `(5).gz`와 동일하게 `bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e`.
- 검증 환경: ChatGPT Linux 컨테이너 오프라인 입력 파일. 사용자 WSL2의 **신규 B 원샷 acceptance는 별도**.
- GitHub 브랜치: `feat/smartdish-b-real-dataset` → Draft PR #46, `main` 미병합.
- A 이전 인수 종료 후 Gazebo/GUI/Nav2를 이번 B 작업에서 다시 실행하지 않음.

## 직접 검증 결과

| Gate | 판정 | 원본 확인 범위 |
|---|---|---|
| B-G01 A 실행 코드 SHA | PASS | summary/source/gate/trial 4개 출처 SHA 대조 |
| B-G02 Archive SHA | PASS | 실제 업로드 바이트 SHA256 일치 |
| B-G03 내부 SHA | **PASS 88/88** | 파일 누락·추가·링크·크기 및 SHA256SUMS 검사 |
| B-G04 원본 PNG | PASS 4/4 | PNG RGB 640×480, trial SHA 일치 |
| B-G05 물리 JSONL·Pose | PASS 4/4 | 시계열·유한수·entity·SHA·길이 |
| B-G06 시간/Pre-fall | PASS 4/4 (계약) | 이미지 0.600s, Pose 0.550s (50ms), 10초 이상 물리, 초기 배치 대비 전도 전 캡처 정렬 검사 |
| B-G07 후보 추출 | PASS 4 | ST-01, ST-02, UN-01, UN-02 원본 후보 |
| B-G08 리뷰 패키지 | PASS (오프라인) | HTML 1개, PNG 4개 링크, SVG 12개, CSV/JSON 감사 |
| B-G09 사람 승인 | **PENDING / 0** | 누구도 운영자 명의 승인하지 않음 |
| B-G10 승인 후보 등록 | **NOT_RUN** | 승인 0건 / 학습 manifest 신규 등록 없음 |
| B-G11 독립 그룹 분할 | **BLOCKED** | 예비 후보 STABLE 2 / UNSTABLE 2; 최소 클래스별 3개 부족 |
| B-G12 C 실학습 readiness | **BLOCKED** | 승인·그룹 분할 미충족, 실제 C 학습 미실행 |
| B-G13 A/S7 보호 | PASS(코드 diff) | A, C, D, Nav2, CM, AI OFF 소스 무변경 |
| B-G14 B 계약 CI | 로컬 완료·원격 Run 별도 확인 | fixture CI와 실제 TAR 인수 다름 |
| B-G15 교육·PR 출고 | Draft PR #46 | 디버깅·워크북 및 인수 원장 갱신 |

## 실제 후보별 확인 기록

| 장면 | 후보 식기 | Pose rows | 물리 sec | 관측 | 추천 라벨(미승인) | 시간 검토 |
|---|---:|---:|---:|---|---|---|
| ST-01 | 2 | 407 | 10.286 | HELD_OBSERVED | STABLE | PASS |
| ST-02 | 3 | 609 | 10.229 | HELD_OBSERVED | STABLE | PASS |
| UN-01 | 2 | 407 | 10.227 | FALL_OBSERVED | UNSTABLE | PASS |
| UN-02 | 2 | 407 | 10.232 | FALL_OBSERVED | UNSTABLE | PASS |

이 라벨은 **A 관측에서 유도한 추천 후보**이며 사람 검토를 거친 `PHYSICS_OBSERVED` 학습 정답으로 자동 승격하지 않습니다. 이미지 callback은 장면당 52건이나 저장 대표 PNG는 장면당 1장입니다.

## 상태 원장

- `A13_SOURCE_REFERENCE_CONFIRMED`: PASS (문서·코드 관계 확인)
- `B_REAL_EVIDENCE_IMPORT_PASS`: PASS (실제 TAR·내부 88개 B 재검)
- `B_REAL_CANDIDATES_VERIFIED`: PASS 4
- `B_LABEL_APPROVAL_PENDING`: **0 승인**
- `B_APPROVED_PILOT_DATA_READY`: NOT_RUN
- `B_DATASET_SPLIT_BLOCKED`: 유지
- `B_DATASET_READY_FOR_C_REVIEW`: NOT_READY

이전 B 문서의 `A13_ARCHIVE_BYTES_NOT_AVAILABLE` 상태는 **본 대화에서 원본 TAR가 업로드되기 전의 기록**입니다. A의 4/4 WSL2 인수와 이번 B 오프라인 직접 인수는 서로 다른 수행 결과입니다.

상세: [DBG-04](../issues/SMARTDISH_B10_DBG_04_REAL_ARCHIVE_EMPTY_DIAGNOSTIC_LOGS_KO.md), [주니어 워크북](../../guides/SMARTDISH_B_A13_EVIDENCE_WORKBOOK_KO.md).


## B-15 — 사용자 WSL2 실행 로그 인수 및 진단 자동 보관

사용자 WSL2 로그(2026-11-25)에 따르면 B 원샷은 기존 A 원본 자동 검색, archive SHA 비교, 내부 SHA **88/88**, trial 4개 PNG/물리 JSONL/시간 정렬 및 `review.html` 생성까지 **PASS**했습니다. 출력의 `B_LABEL_APPROVAL_PENDING approved=0`은 정상 계약이며 C 학습 가능을 뜻하지 않습니다. `review.html`만 첨부됐으므로 상대경로 이미지·SVG의 실제 GUI 렌더링은 HTML 단독으로는 QA하지 않았습니다.

후속 코드에는 **성공/실패 모두** private 진단 TAR·외부 SHA sidecar 자동 생성 기능을 추가했습니다. 인수와 검토 자료는 `ai/data/private/b_a13_diagnostics/`에만 보관하고, A 원본 전체 TAR·승인 ledger·학습 manifest를 자동 출고하지 않습니다. 새 코드에서 발생한 사용자 WSL2 진단 TAR는 아직 별도 인수 상태입니다.

- B-G01~B-G08: 사용자 WSL2 실행 로그 **PASS** (실제 파일 재해시·물리 그래프은 이전 ChatGPT Linux 직접 검증으로도 확인)
- B-G09~B-G12: 승인 0건, 독립 그룹 부족으로 HOLD
- B-15 자동 진단 패키징: 로컬 실제 A TAR 스모크 **PASS**. 최종 동일 SHA GitHub CI 및 새 WSL2 실행은 별도 확인
- [개발 보고서](../tasks/SMARTDISH_B15_ONE_SHOT_DIAGNOSTIC_ARCHIVE_EDU_KO.md)
