# S3-NAV-CI01 — Nav2 Action 서버 발견과 Lifecycle ACTIVE 차이

- 날짜: 2026-11-20 KST
- 원본 Run: https://github.com/silverbjin/samsung_AXI/actions/runs/44563771148
- 확인된 결과: 지도 SHA/AMCL MapServer·Scan·TF 준비 PASS. 첫 `TABLE_3` NavigateToPose Action Goal이 서버에서 거절되어 `NAV_ACTION_GOAL_REJECTED_TABLE_3`.

## 진단 근거
- 실제 `ci-s3-summary.txt`에서 Nav2 lifecycle manager가 map_server/amcl 활성화와 planner_server 구성을 아직 진행 중이었음.
- bt_navigator/planner_server/collision_monitor 등이 전환 대기인 상태에서 발견된 NavigateToPose Action 서버로 Goal을 바로 전송한 것이 최초 실패 경계.
- 서버 존재 = 요청 수신 가능성을 뜻할 뿐 **BT Navigator ACTIVE, Controller ACTIVE, Planner ACTIVE**를 보증하지 않습니다.

## 최소 해결 후보
- S3-NAV-02 전용으로 공식 `lifecycle_msgs/srv/GetState`를 사용해 bt_navigator, planner_server, controller_server, collision_monitor, behavior_server가 모두 PRIMARY_STATE_ACTIVE 인지 검증합니다.
- 활성 전에는 절대 Goal을 보내지 않습니다. 150초 내 ACTIVE가 아니면 실패 상태와 최초 로그를 보존.
- 기존 S3-AMCL-01 NO-GOAL 완료/실제 지도/ROS World/SLAM 변경 금지.
- 실제 L2 GREEN 전에는 NAV-02 성공으로 보고하지 않습니다.

## 교육용 메시지
Nav2 액션 서버가 보이는 것과 Nav2 Lifecycle 노드가 ACTIVE인 것은 다릅니다. Goal 거절 시 Planner를 새로 개발하거나 지도를 다시 만들기보다 lifecycle_manager의 전환 로그와 해당 노드의 GetState를 먼저 확인해야 합니다.

## RESOLVED — 2026-11-20 실제 Gazebo L2 검증
- [Run #44564927414](https://github.com/silverbjin/samsung_AXI/actions/runs/44564927414), commit `22d19347`: Nav2 Lifecycle ACTIVE 확인 뒤 TABLE_3 Action accepted/SUCCEEDED, 물리 Odom 5.185m, 도착 오차 0.192m. PICKUP_RETURN Action SUCCEEDED, Odom 5.214m, 도착 오차 0.066m.
- 초기 서버 발견만으로 Goal을 보내던 경합을 공식 Lifecycle GetState ACTIVE 게이트로 해소. 다른 Planner나 Collision Monitor 기능을 변경하지 않았음.
- 자료: `samsungaxi-s3-amcl-verified-44564927414` ZIP 내 JSON+축약 로그. 기존 성공 증거 보존.

## main 인수 확인
- PR #10 main 병합 후 [Run #44646848087](https://github.com/silverbjin/samsung_AXI/actions/runs/44646848087)에서 5개 Nav2 주요 Lifecycle ACTIVE 확인 뒤 TABLE_3/PICKUP_RETURN 두 Action 모두 SUCCEEDED. 이슈 CLOSED.
