# S4-MENU-CI01 — S3 브랜치 분기 계약의 구형 기대 문자열

- 최초 RED Run: https://github.com/silverbjin/samsung_AXI/actions/runs/44651503909
- 현상: L0 14 PASS / 1 FAIL, S4 새 속도/CM 계약은 PASS했으나 S3 테스트 한 건이 main의 과거 단독 S3 step 조건 문자열을 요구.
- 원인: 기존 S3 테스트는 `s3/nav-delivery-20261120 || main` 조건을 고정. S4가 main에서 S3 preflight/Goal까지 포함하는 상위 통합 인수 단계를 수행하도록 바꾼 뒤에도 테스트만 갱신되지 않음.
- 해결: 현재 CI 단계 경계대로 S3 전용 분기와 S4/main 통합 분기를 각각 확인하도록 계약 1건 수정. ROS/SLAM/Nav2/CM 제어 코드는 수정하지 않음.
- 상태: 실제 Actions GREEN 재검 전까지 HOLD.
- 교육용 핵심: 기존 테스트가 RED일 때 코드를 되돌리기 전에 정책/계약 변경과 테스트가 불일치한 것인지 최초 실패를 분류합니다.
