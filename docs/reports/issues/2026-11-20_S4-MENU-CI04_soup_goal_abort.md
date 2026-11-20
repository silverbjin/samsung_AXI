# S4-MENU-CI04 — 저속 SOUP 복귀 간헐 Nav2 ABORT와 안전 게이트 분리

- 원본 Run #44653541553: https://github.com/silverbjin/samsung_AXI/actions/runs/44653541553
- L0/L1 통과 및 NORMAL TABLE3 Action SUCCEEDED/5.208m/0.074m. SOUP PICKUP_RETURN Action `GoalStatus.STATUS_ABORTED=6`, 안전 fixture 실행 이전의 경계.
- 기준 Run #44651716546, #44652530997에서는 동일 SOUP 제한 p75=0.11 및 실제 복귀 SUCCEEDED. 이번만으로 저속 계획기 자체 결함이라 단정 불가.
- 실패 artifact는 Nav2 full log 대신 축약 진단으로만 제공되어 내부 Goal ABORT의 최하위 원인은 미확정. 상태를 임의 PASS 승격하지 않음.
- 결합 CI에서 원인과 무관한 5m 왕복을 계속 반복하지 않도록 `--s4-stop-only` 개별 검증으로 우선 좁힘. S4 안전 원본 증거 확보 후 전체 통합 PASS 여부 판단.
- 출력 형식: Odom 움직임, 충돌 상태, LiDAR polygon 점수, output `/cmd_vel` 제로가 모두 있어야 CM STOP PASS.
- 교육용 해설: 하나의 E2E 테스트가 여러 기능을 묶으면 앞 단계의 비결정적 실패 때문에 후속 실패 원인을 관측할 수 없습니다. 최초 실패 경계에 맞춰 검증을 쪼개고 성공 증거는 보존합니다.
