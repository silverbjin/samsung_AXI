# S3-NAV-CI02 — 배달 성공 증거의 kind 메타데이터 불일치

- 기록: 2026-11-20 KST
- 원본 성공: [Run #44564927414](https://github.com/silverbjin/samsung_AXI/actions/runs/44564927414), `nav_delivery.json`.
- 현상: `goal_sent=true`, `delivery_return=true`, `real_nav_legs`의 2개 `status=4`가 있는 반면 `kind=s3_real_gazebo_no_navigation_goal`이 그대로 남음.
- 원인: AMCL 사전검사 단계의 딕셔너리를 뒤이어 배달 결과로 확장하되 `kind` 값을 갱신하지 않았음. Action·Odom·AMCL 실증은 성공이며 데이터 내용이 상충한 것은 결과물의 종류 식별자에 한함.
- 최소 수정: 두 Leg 실제 완료 후 `result['kind']='s3_real_gazebo_navigation_delivery_return'`로 교정. 회귀 계약 테스트 추가. `--exercise-goals`가 없으면 기존 `kind=no_navigation_goal`을 유지.
- 원본 ZIP/로그를 수정하지 않음. 동작 코드는 그대로 두고 결과 스키마만 정합. 후속 CI 확인 전 코드 출고는 보류.
- 교육 교훈: 로그가 PASS여도 **증거 JSON 필드끼리 모순이 없는지** 별도 점검해야 추후 자동 집계/감사에서 잘못 분류하지 않습니다.
