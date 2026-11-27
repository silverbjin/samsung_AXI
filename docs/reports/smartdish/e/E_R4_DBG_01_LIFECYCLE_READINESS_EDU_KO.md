# E-R4 DBG-01 — Lifecycle 서비스 발견과 ACTIVE 구분
## RED (실제 CI)
- Run [45937032371](https://github.com/silverbjin/samsung_AXI/actions/runs/45937032371), job 140302497432, SHA 553cd06b241819640ba43300425330383463271e.
- Artifact 15170983025 ZIP SHA256 `d7442f3074965794cc8e55493796596bcad442e79251a06f4ac06b3ba6256fbe` 직접 검증.
- 최초 실패: `AssertionError('E_R4_CM_NOT_ACTIVE')`. map/scan/odom/AMCL/TF/action 및 lifecycle service 발견 이후, lifecycle manager 로그는 collision_monitor와 bt_navigator를 아직 Configuring 중. 서비스 발견은 활성화 완료와 다르다.
- events=[], legs=[], action_status={}; Goal 0건, nav2 정리 exit 0. 안전 게이트는 정상 동작하였다. 주행이나 모델 문제가 아니라 시작 준비 순서 문제다.
## 수정
- 실제 GetState 응답으로 collision_monitor, bt_navigator가 모두 ACTIVE(3)가 될 때까지 최대 90초 제한 대기. 상태 ID/label 변화와 monotonic 시각을 기록한다. 서비스 응답 타임아웃 10초, 프로세스 생존 검사 유지.
- TTY 승인 이전 /cmd_vel sole publisher가 collision_monitor임을 검사하고 Goal 0을 확인한다. CM 우회/임계값 완화 없음.
- C/D 종료 실패가 있으면 결과 JSON도 FAIL로 기록한다. 종료 전에는 PASS 로그를 발행하지 않는다.
## 검증 계획
동일한 실제 Nav2 + 독립 Gazebo station 3-leg CI. 새 SHA에서 lifecycle 기록, 3 action UUID, 실제 odom, 직원 승인, camera hash 및 cleanup 검사. 결과는 CI 종료 후 별도 기록한다. 본 수정은 사용자 v1 checkpoint나 실제 UI 클릭을 검증하지 않는다.
