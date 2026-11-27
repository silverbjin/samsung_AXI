# A-PROD-04-04 — A 내부 실제 무부하/적재 주행 개발 원장

A04 자체 개발 진행 중 (E 미인계 / OWNER_L3_NOT_RUN). A03 정지 LOAD/UNLOAD 성공 증거는 재사용하지만 이동 성공으로 승격하지 않는다. 현재 구현: 같은 실제 월드에서 NO_GOAL→empty 3 legs→loaded mission 3 legs+LOAD/UNLOAD, A 기존 exact UUID 및 stop/transfer controller, 10/5s 및 20/20s 유지. 실제 pose/relative/tilt/ID/contact, 1ms read-only Gazebo ECM, 속도/가감속 증거와 lifecycle shutdown gate 포함. A 전용 CI이며 제품 배포 아님.

| 실제 Run | 결과 |
|---|---|
| 45958030964 | 바닥 지지 접촉 양방향 분류 RED, 수정 DBG04 |
| 45958451276 | 실제 2.888m 이동 후 등록 오차 .100302m, exact cancel+stop |
| 45958928009 | dual map 실제 적용 GREEN, 등록 오차 .107083m, exact cancel+stop |
| 45959501785 | ECM 28900 ticks/1ms gap 0 GREEN, 등록 오차 .107328m, exact cancel+stop. 종료 콜백 결함 DBG08 |
| 45959741594 | 9394f1e AMCL 후보 및 exact TF decomposition 실제 CI, 결과 미확정 |

각 상세 Artifact/해시는 DBG04~08 참조. 완료된 무부하 leg 0, A04 실제 LOAD/UNLOAD 미도달. E handoff 보류는 A 내부 개발 상태이며 E에 수정/중간 검수 요청하지 않는다. 다음 gate: 새 PIN 실제 six legs+transfer+ECM+terminal stop+shutdown 모두 통과. 원본 및 E/main 미변경.
