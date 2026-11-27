# A-PROD-04 DBG-06 — CI 범위 검수의 의존성
RED b859acea3bd0539af5e7d2d3266e818c7b7862ea, Runs 45959159895/45959159965/45959159914: scope job /usr/bin/python3 No module named pytest. Actual BEFORE/HEAD 정확히 확인. Heavy jobs skipped; no Gazebo test or artifact. stdlib 직접 실행 5 assertions로 변경, apt/pip 의존 제거. 추가 공통 scene/nav overlay dependency 범위 보완. 수정 후 실제 scope job 검수. 이전 실제 motion f3ea542 CI와 독립. E 인계 없음.
