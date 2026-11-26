# SmartDish B-10 DBG-04 — 실제 A-13 원본 TAR의 0바이트 진단 로그 오탐 및 원샷 배포 게이트 개선

- 기준일: **2026-11-25 KST**
- B 후속 개발 브랜치: `feat/smartdish-b-real-dataset`, Draft PR #46 (main 미병합)
- A 실제 실행 Git SHA: `6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df`
- 직접 분석한 사용자 첨부물: `smartdish_a_tray_evidence.tar(6).gz` (보고서 `(5).gz`와 **SHA256 바이트 동일**)
- Archive SHA256: `bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e`
- 검증 환경: ChatGPT Linux 컨테이너의 오프라인 Python/Pillow / 실제 업로드 TAR, **사용자 WSL2에서 신규 구동한 결과 아님**.

## 1. 문제 / 최초 RED

사용자 WSL2에서는 원본 위치 자동 탐색이 성공했으나, 구버전 B 인수기가 다음 메시지로 종료했습니다.

```text
B_A13_ARCHIVE_SHA_PASS
ARCHIVE=/home/.../samsung_AXI_A_TRAY/generated/smartdish_tray/run_.../smartdish_a_tray_evidence.tar.gz
B_EVIDENCE_IMPORT_BLOCKED B10_ARCHIVE_MEMBER_SIZE_INVALID
```

첨부된 실제 TAR로 **구버전 B 인수기를 직접 실행**하여 동일하게 `B10_ARCHIVE_MEMBER_SIZE_INVALID` / exit 2를 재현했습니다. 압축 원본은 SHA256이 일치합니다.

## 2. 첫 실패 원인 및 관측 사실

- Archive 파일 구성원: **89개 정규 파일**. 내부 `SHA256SUMS`가 인증하는 파일: **88개**(`SHA256SUMS` 자신 제외).
- 예외 없이 **8개 정상 진단 stdout 로그가 0바이트**입니다. 네 개 `trial_0001`~`trial_0004` 각각 `gz_image_probe.log`, `post_spawn_gz_probe.log` 두 개씩입니다.
- 각 빈 로그는 `SHA256SUMS`에 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`로 등록되어 있습니다.
- 기존 “0바이트 정규 파일도 무조건 거부”한다는 `if info.size <= 0` 조건이 **합법적인 A 생성기 출력과 불일치**했습니다.
- 원인 분류: 파일 권한, GPU/WSLg, 렌더링 문제가 아니라 **B-10 입력 스키마의 잘못된 보수적 검증 정책**입니다.

## 3. 최소 수정 및 보안 경계

`ai/scripts/import_a13_evidence.py`에서 0바이트가 허용되는 파일을 다음 **정확한 로그 패턴에만** 제한했습니다.

```text
logs/trial_000[1-4]_(gz_image_probe|post_spawn_gz_probe).log
```

PNG, 물리 JSONL, `trial_summary.json`, `summary.json`, `source_manifest.json`, `deployment_gate_manifest.json`, `SHA256SUMS` 및 기타 로그는 0바이트를 허용하지 않습니다. 크기 상한·압축 해제 전체 용량 상한·절대 경로/상위 경로 이탈·중복 이름·링크·특수 파일 차단·전체 및 내부 SHA 재계산·임시 staging 검증 후 승격·원본 읽기 전용 정책은 유지했습니다.

새 `scripts/smartdish_b_real_data_one_shot.sh`에는 다음 fail-fast를 추가했습니다.

- `--archive`가 없으면 **A_TRAY generated runs / Downloads의 한정된 경로**에서 *실제 SHA가 일치하는 원본*만 자동 선택합니다.
- `/path/to/...` 예시 경로는 `B_A13_ARCHIVE_PLACEHOLDER_PATH`로 차단합니다.
- 명시적 파일 부재 `B_A13_ARCHIVE_FILE_MISSING`, 읽기 불가 `B_A13_ARCHIVE_NOT_READABLE`, 후보 자체 부재 `B_A13_ORIGINAL_ARCHIVE_NOT_FOUND`, SHA 오류 `B10_ARCHIVE_SHA_MISMATCH`를 각각 분리합니다.
- 모든 해시 검사가 성공하기 **전에는** 신규 데이터 작업 디렉터리를 만들거나 실제 인수를 시작하지 않습니다.
- 실행기 `--mode review`는 사람 승인을 만들거나 학습 manifest를 갱신하지 않습니다.

## 4. GREEN — 실제 업로드 TAR의 직접 인수 결과

| 원본 검증 | 직접 결과 |
|---|---|
| 전체 Archive SHA256 | PASS / 기대 `bfc346...f8e6e` |
| 내부 `SHA256SUMS` | **88/88 PASS** |
| TAR 전체 파일집합 | 89개 (manifest 88 + SHA256SUMS 1) |
| A 실행 SHA / 4 trials | **PASS / 4/4** |
| 센서/GUI/물리 수용값 | **4/4 PASS (기존 A 원본에서 B가 재검증)** |
| 저장 PNG | **4장** / 640×480 RGB |
| 이미지-Pose 시간차 | **50ms** 각 장면 |
| 물리 관측 | **ST-01 10.286s / ST-02 10.229s / UN-01 10.227s / UN-02 10.232s** |
| Pose 시계열 건수 | **407 / 609 / 407 / 407** |
| 물리 관측 후보 | **HELD, HELD, FALL, FALL** |
| 후보 태그 | **4건 모두 `REVIEW_REQUIRED`** |
| 사람 승인 | **0건** |
| 학습 split 및 C readiness | **HOLD (클래스별 독립 그룹 각 2개 예상)** |

추출한 실제 `candidate_manifest.csv`에는 네 개 `B13-*` 후보 ID가 있습니다. PNG·JSONL·Pose가 모두 유효했고 **네 장면 모두 `temporal_review=PASS`**였습니다. 이는 자동 라벨 승인이 아닙니다.

## 5. 재현 명령 및 결과 구별

```bash
# 실제 사용자 WSL2 B clone: 기존 브랜치 변경은 보존, ff-only만 사용
git -C ~/samsung_AXI_B_REAL fetch origin feat/smartdish-b-real-dataset
git -C ~/samsung_AXI_B_REAL merge --ff-only origin/feat/smartdish-b-real-dataset
cd ~/samsung_AXI_B_REAL
bash scripts/smartdish_b_real_data_one_shot.sh --sha "$(git rev-parse HEAD)" --mode review
```

자동 검색 실패 시 `--archive '/실제/존재하는/파일.tar.gz'`로 원본 경로를 지정하십시오. A-13 Gazebo 재실행·Nav2 재주행은 필요 없습니다.

검증 스크립트의 오프라인 계약 테스트는 실제 A-13 원본이 없는 GitHub에서도 실행 가능하도록 합성 fixture로 수행합니다. **실제 TAR 직접 검증과 GitHub fixture CI는 서로 다른 증거**입니다.

## 6. 회귀 테스트 및 잔여 위험

- 0바이트 허용 로그 8개가 있는 합성 TAR 정상 인수.
- 0바이트 PNG·물리 JSONL·필수 summary·기타 GUI 로그는 반드시 거부.
- SHA256SUMS에 기록되지 않은 정상 이름의 빈 로그 및 거짓 SHA도 거부.
- 잘못된 예시 경로·명시적 경로 없음·SHA 불일치·자동 검색 후보 없음·자동 검색 SHA 불일치를 서로 다른 종료코드/메시지로 확인.
- 첨부된 **실제 TAR**를 통한 B-10 인수, B-11 후보 4장/12 SVG/HTML까지 실제 PASS (컨테이너 검증).
- **WSL2 사용자 재실행 PASS는 아직 미확인**. GitHub 새 HEAD 원격 CI와 같은 코드로 실행한 사용자 원샷의 최종 로그를 별도로 받아야 합니다.
- 사람 라벨 승인 0건이므로 B-13 학습 등록과 C 실제 학습은 수행하지 않았습니다.

본 디버깅 기록은 `A13 archive accepted`를 `approved learning labels`로 혼동하지 않기 위한 교육 자료입니다.
