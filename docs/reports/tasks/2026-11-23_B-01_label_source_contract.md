# B-01 — 라벨·출처·권리/데이터 형식 계약

- 기준: `main@2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`, 작업 브랜치 `feat/smartdish-b-dataset`
- 작업 커밋: 본 문서와 같은 Git 커밋 (GitHub History에서 조회). PR: Draft PR 본문에서 조회.
- 검증: **PASS(계약 문서 정적 점검)** / DACON ZIP·실제 식기 영상 **NOT_RUN**

## 목적과 결정 근거

S7 `STACKED`는 접시 존재이고 SmartDish B/C의 `STABLE`은 물리 안정성이므로 직접 매핑은 라벨 오류입니다. DACON 구조물 2개 시점과 10초 물리 영상은 문제 정의 참고용이지 트레이 정답이 아닙니다. 저작권이 명확하지 않은 자료는 공개 소스에서 제외하므로 사람 검수/재현성 먼저 고정했습니다.

## 산출물

- `ai/docs/DATASET_CARD_KO.md`: 표본 목표, 라벨/제외, 사용권, C 계약
- `ai/data/manifest.csv`, `split_manifest.csv`: 의도적으로 헤더만 기록(실제 0건)
- `ai/data/.gitignore`: 외부/현장 데이터 공개 반입 방지
- `ai/data/README.md`: 원본 데이터 0건 명시

## 검증과 한계

- 실제 관찰: main S7 RGB prototype과 트레이 물리 안정성의 라벨 의미 차이, 공식 DACON 데이터 페이지에 설명된 예상 파일 구조.
- DACON 데이터 ZIP 다운로드/비교: NOT_RUN (로그인 권한/데이터 없음). 개별 사용·재배포 허가는 추가 확인 필요.
- `main` 기존 서비스 코드 수정 없음. S7 성공을 새 AI 성능으로 주장하지 않음.

## 교육 질문과 다음 경계

`unknown`이 왜 분류 정답이 아니라 추론 상태인지 설명하십시오. 다음 B-02에서 실제 파일 경로/권리·물리 관측을 입력 조건으로 받는 collector를 구현합니다.
