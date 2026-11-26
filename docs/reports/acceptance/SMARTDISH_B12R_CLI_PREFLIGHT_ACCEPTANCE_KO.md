# SmartDish B12R CLI — 2026-11-25 배포 게이트 및 PASS/HOLD 원장

## 범위

기준 B `feat/smartdish-b-real-dataset@e2a8db39ed3e9382aa832019eb3732bd2a4ec974`, main `63e147289e307e0b9900ca365e9c4557c5921804`. 새 배포 SHA는 커밋과 PR/CI 확인 후 작성해야 하며 기존 결과를 소급해 PASS라고 표시하지 않습니다.

## 실증 기준

- **기존** 사용자 B15 TAR SHA `912bfbc759e3fde3f48e70316638bc86dd30c52461ecd19410281bd7edf1f515`와 B15 내부 53/53는 이미 Owner PASS.
- 현재 변경의 로컬 재검: 동일 사용자가 첨부한 TAR를 새로운 원샷에 지정, 코드 SHA는 테스트용 clean checkout SHA; 후보 4·B14 2/2 분할 차단·승인 0·성공 진단 TAR 및 외부 SHA 생성: **PASS (오프라인 Linux)**.
- 실제 새 B SHA의 사용자 WSL2 인수는 **HOLD**, 사용자 재실행 결과를 기다립니다.
- 독립 학습 데이터 split은 `B_DATASET_SPLIT_BLOCKED`, C 학습 NOT_RUN.

| Gate | 로컬/계약 상태 | 원격 동일 SHA/Owner 상태 |
|---|---|---|
| CLI-G01 Git SHA와 실행기 일치 | 임시 clean Git checkout PASS | 신규 SHA 인계 시 확인 |
| CLI-G02 bash -n | PASS | CI 확인 |
| CLI-G03 compileall | PASS | CI 확인 |
| CLI-G04 여러 CWD·공백/괄호 | PASS | CI 확인 |
| CLI-G05 오류 주입·fail-fast | PASS | CI 확인 |
| CLI-G06 기존 B 계약 회귀 | 신규 환경 기존 B12R/B14R 21 PASS | GitHub 전체 CI 확인 |
| CLI-G07 같은 SHA GitHub CI | NOT_RUN(신규 커밋 전) | 새 Run ID 갱신 |
| CLI-G08 실제 B15 TAR | 오프라인 직접 PASS | WSL2 새 SHA Owner HOLD |
| CLI-G09 성공/실패 진단 TAR | PASS / 내부 SHA 및 sidecar PASS | GitHub fixture CI 확인 |
| CLI-G10 최종 복붙 한 번 실행 | Linux 독립 쉘 PASS | WSL2 Owner HOLD |
| CLI-G11 사람 미승인 차단 | PASS, 0 approved | 사용자 리뷰 HOLD |
| CLI-G12 A/C/D/S7 보호 | 기존 기능 코드 직접 변경 없음 | 변경 파일 Git diff 및 PR 검수 |

## 외부 CI 분리

이전 Robot CI #45555957977은 S2-MAP-02 RELOAD_CONFIGURE 실패가 있었으나, 이후 B SHA `e2a8db39...`의 Robot CI #45557988000은 **SUCCESS**로 종료했습니다. 신규 SHA의 Robot CI는 완료 후 별도 기록합니다. 해당 S2 기능을 B 코드에서 변경하지 않습니다.

## 사용자 배포 후 검수

새 SHA 고정 원샷이 기록하는 `B12R_REVIEW_WORKSPACE_READY candidates=4`, `B_DATASET_SPLIT_BLOCKED`, `B_LABEL_APPROVAL_PENDING approved=0`와 생성된 진단 TAR `.sha256`를 필수로 확인합니다. 사용자 시각 검수는 별도이며 모델 학습 게이트가 아닙니다.
