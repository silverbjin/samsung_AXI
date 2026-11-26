# R03 DBG03 — 독립 verdict 및 원본 재검수

RED 설계: 기존 owner는 rc!=0이면 독립 verifier 이전에 종료한다. 새 테스트는 GUI late exit만의 경우에도 원본 확인 이후 data PASS, GUI FAIL을 요구한다. 시작/센서/서버/해시/phase/role 오류와 다른 exit code는 거부한다. 단순 fixture는 실제 GUI 실험이 아니다.

GREEN 구현: 별도 read-only verifier에서 모든 archive member와 manifest coverage, path/size/duplicate, A13 RGB/pose/timing 계약, R02-3 SHA 및 원본 ECM/ROS에서 refresh/cross_check를 다시 계산한다. 이전 Owner 재사용은 정확한 기존 SHA 및 raw SHA만 허용한다. 새로운 evidence는 reviewer SHA와 동일한 source SHA 및 process trace가 필요하다. 과거 ST-02 server -11은 cleanup FAIL/HOLD; all_owned_stopped true인 경우만 다음 독립 실험을 허용한다. GT는 항상 UNKNOWN/HOLD. CI 이전에는 테스트 결과 미확정.

## CI 첫 실패 (2026-11-26)
Run #45730294064, job #139610339695: Python/Bash syntax 이후 `/usr/bin/python3: No module named pytest`. L0 환경 준비 실패, verdict fixture 및 L2 NOT_RUN. 기존 R02 CI와 동일하게 python3-pytest 명시 설치. 소스/실제 물리 계약 변경 없음. 신규 CI 결과 전 GREEN 선언 금지.
