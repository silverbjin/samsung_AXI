# S4-MENU-CI06 — main 병합 후 Action readiness 불필요한 의존성 분리

- 최초 실패: main merge `88fa583fd42a69a04cc1e63191ed00e0ec746bff`, [Run #44655682930](https://github.com/silverbjin/samsung_AXI/actions/runs/44655682930), `S3_AMCL_TF_OR_NAV2_ACTION_NOT_READY`.
- 원본: AMCL 좌표 [-0.0012, 0.0379], map_to_odom=true, odom_to_base=true, Scan count=121. Action server 미발견, CM 안전 구역 계측까지 도달하지 못함. 정확한 Action 준비 지연 원인은 미확정.
- 실패 경계: Nav2 Action discovery (불필요한 테스트 사전 조건). STOP-only 시험은 Goal을 보내지 않으며 공식 CM ACTIVE를 별도 확인.
- RED→GREEN 최소 변경: `args.s4_stop_only or action.wait_for_server(...)`와 main STOP-only CI FLAGS, L0 회귀 테스트. Nav2 Planner, 지도, 정책, 원본 S3 Action 검수 불변.
- GREEN: [main Run #44656669479](https://github.com/silverbjin/samsung_AXI/actions/runs/44656669479), exact executable SHA `236cd4060abb443c95c414e37f0a51173d70c2ae`. 실제 STOP rectangle LiDAR points 29, official CM STOP, upstream input, `/cmd_vel` zero, `/odom` 정지 테스트 통과.
- Artifact: [#14593432791](https://github.com/silverbjin/samsung_AXI/actions/runs/44656669479/artifacts/14593432791) (7349 bytes, SHA256 `7971bb95011e650ed2cfc241ae60085bf7ee37eaba146468c4d5ba4cfcca3fa6`).
- 중요 경계: 과거 메뉴 속도와 Goal 왕복 실증은 [Run #44651716546](https://github.com/silverbjin/samsung_AXI/actions/runs/44651716546) 원본 그대로 사용; 이 STOP-only 검수는 메뉴별 주행을 다시 실행한 것이 아님. WSL2 GUI L3 미실시.
