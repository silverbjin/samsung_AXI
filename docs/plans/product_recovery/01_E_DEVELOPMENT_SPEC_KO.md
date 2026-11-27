# E 담당 — 제품 복구 통합 개발 명세
역할: E-PROD-00~03, 통합 책임자/PM. [공통 계약](00_COMMON_CONTRACT_KO.md)과 [통합 절차](06_INTEGRATION_RUNBOOK_KO.md)를 필수로 읽는다.
## 기준 및 재사용
PR #64 및 검증 PIN 77a1ae25의 실제 Nav2/CM overlay, C runtime reuse, runner provenance 및 R3a/b/c/R4 CI를 보존. 기존 station 실행기를 제품 성공으로 재사용하지 않는다. 문서 merge 이후 E가 유일하게 기존 E head와 최신 docs main을 일반 merge로 결합하여 공통 seed를 발행한다. E 자체는 integration/smartdish-product-recovery, A/B/C/D는 seed의 동일 SHA에서 분기(다른 연구 브랜치 병합 금지).
## 작업 단위
| ID | 구현 및 소유 범위 | 게이트 |
|---|---|---|
| E-PROD-00 | 기존 증거/코드 감사, 공통 schema/profile 동결, branch seed SHA와 계약 버전 공지 | docs 및 source diff, main 보호, 기존 E PR #64 HOLD 기록 |
| E-PROD-01 | A/C/D 기능 PR을 순차 통합, B QA harness 연결, station partition 삭제하고 single restaurant world/robot/camera bridge 런치 | 실제 초기 식기·장착 camera·CM graph·DDS readiness, L0/L1 |
| E-PROD-02 | 실제 Gazebo positive 3leg + 대표 fault injection, 기존 AI OFF 회귀(변경된 경계만) | L2 증거와 13 예외 계약, B QA receipt, private model CI 금지 |
| E-PROD-03 | immutable bootstrap/runner SHA/overlay/installed module provenance, WSL2 GUI 기본, manual TTY/UI, tar sidecar | L0/L1/L2 완료, Owner 1회 최종 L3, merge 전 증거 감사 |
## 파일 및 책임
기존 scripts/smartdish_e_owner_aion.sh, scripts/smartdish_e_ci_station_nav_probe.py, scripts/smartdish_e_nav_velocity_overlay.py, scripts/smartdish_e_installed_origin.py를 읽고 product 전용 runner/witness/workflow를 새 파일로 분리 권장. 이름 후보 scripts/smartdish_e_product_{runner.sh,witness.py}, .github/workflows/smartdish-e-product-ci.yml. 실제 파일 존재 여부 먼저 확인. 기존 station 및 AI OFF 실행 경로 보호. E만 공통 계약 수정 승인, 역할 간 충돌은 각각 PR에 되돌려 수정; 공통 파일 임의 동시 편집 금지.
## 안전/인수
CM sole publisher, docking remap의 기존 실증 재사용, no direct cmd_vel, actual UUID cancel/terminal 및 zero dwell. C/D의 모델 성능 면제는 Owner 통합 전용. C test double + 실제 camera/physical movement를 분리 표기. 실제 private model checkpoint SHA 6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c 및 기존 ~/.venvs/smartdish-c-v1-py312-cpu 재사용; 새 torch/venv 금지. CI에서는 weight 없음. 실패 시 첫 오류→최소 수정→증거→교육 MD, 무한 재시도 금지. R4 old station PASS 유지, 신규 제품 L3 HOLD.
## 인계
다른 담당 Draft PR HEAD, 실제 CI Run/Artifact SHA, changed paths, scope/known issues, interface examples. E는 통합 원장 및 최종 사용자 원샷과 최종 보고서 커밋. 사용자 명시 승인 및 실제 L3 확인 전 제품 코드 main merge 금지. 문서 main merge는 별개.
