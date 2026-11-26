# R03 — WSL2 Owner 출고 실행기 개발·교육 보고서

## 문제와 해결
기존 A14-07 bootstrap은 pinned SHA 요청 뒤 branch 최신 HEAD를 merge하여 SHA_DRIFT가 발생했다. 사용자는 별도 디렉터리에서 exact SHA fetch/branch checkout 후 실제 교정 PASS를 제출했다. R03 bootstrap은 매 실행마다 새 mktemp 디렉터리, exact SHA fetch(120s), 동일 local branch 이름과 HEAD 확인, 기존 workspace 무변경. 기존 A14-07은 이미 인수했으므로 재실행 금지. 로컬 fixture는 원격 HEAD가 진전된 상태에서도 과거 SHA checkout, 기존 폴더 거부 및 파일 보존을 확인한다. fixture helper와 bootstrap의 동일 동작은 별도 코드 경로이므로 bootstrap 직접 WSL 검증은 Owner에서만 확인 가능하다.

## Owner 실행 계약
R02-2 / R02-3 Cloud 실제 PASS 및 packaging fixture PASS 확인 후에만 최종 SHA 출고. GUI 기본; GPU 환경 변수는 사용자 설정 그대로 상속. Harmonic 8.15.0 EXACT, 빌드 전 ROS vendor package 및 physics binary fingerprint 기록. 설치/환경 변경을 자동 수행하지 않는다. cmake 120s, build 180s, GUI 65s, 신규 ST-02/UN-01 각 600s 상한. 증거 capture 검수 PASS ≠ production GT PASS. 실패시 최초 경계와 가능한 원본 TAR/SHA 저장, 다음 장면으로 무한 retry 금지. 

## 출고 명령 (검증 전 실행 금지)
```bash
PIN=<R02-3 및 R03 packaging CI 검증 완료 SHA>
curl -fsSLo "$HOME/a14_r03_bootstrap.sh" \\
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/a14_r03_bootstrap.sh" \\
  && SMARTDISH_A14_SOURCE_SHA="$PIN" bash "$HOME/a14_r03_bootstrap.sh" --gui
```
경로: ~/samsung_AXI_A14_R03_<sha7>_*/generated/smartdish_a14/r03_owner_*/a14_r03_owner_evidence.tar.gz 및 .sha256. 사용자 제출 전에 Owner L3 PASS라고 쓰지 않는다. B 사람 승인 0, main merge 금지. 현재 CI/WSL 미검증.
