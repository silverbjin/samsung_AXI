# A-PROD-04-04 — 실제 무부하·적재 주행 및 종료 검수 원장
A_INTERNAL_L2_PASS_COMPOSED / E_FINAL_REVIEW_REQUIRED / OWNER_L3_NOT_RUN. 최신 기능 PIN 7d8bf9ec30f88c79ed1035b485a40aa3e7c3b688. 세 독립 actual Gazebo/Nav2 session의 성공 구간을 재사용한 검수. 동일 session 전체 성공으로 확대하지 않는다.

| Run | Source PIN (short) | 실제 결과 |
|---|---|---|
| 45958030964 | 9e7f098 | 바닥 지지 접촉 양방향 분류 RED, DBG04 |
| 45958451276 | c10f9dd | 2.888m 이동, 등록 오차 .100302m, cancel/stop |
| 45958928009 | f3ea542 | dual map 적용 GREEN, 등록 오차 .107083m |
| 45959501785 | 1f5d949 | actual ECM 28900 ticks, 등록 RED 및 종료 writer 오류 |
| 45959741594 | 9394f1e | 무부하 3/3 + loaded TO_TABLE/LOAD GREEN; pre-goal stale |
| 45960123978 | 7bb0271 | 등록 오차 재현 RED; 종료 writer 해소 |
| 45967974937 | e48778e | empty 3/3 + loaded 2/3 GREEN, LOAD GREEN, pre-unload stale |
| 45970380453 | 247db79 | loaded 3/3 + LOAD/UNLOAD actual ACK + ECM PASS; shutdown nav NO_ACK |
| 45972717341 | 7d8bf9e | focused actual terminal stop + manager 3/3 ACK + pause + clean parent exit PASS |

Evidence: empty artifact15184188608; full loaded mission artifact15185112687; focused shutdown artifact15185567891. 각각 내부 70/72/60개 해시 확인. DBG09/10/11/11_GREEN 상세 참고. 실제 3+3 legs, UUID, postterminal stop, .10m registration, .05m conservative clearance, same 3 dishes, 10/5s wait, 20s transfer deadline 유지. Loaded mission ECM 186122 steps, 3 legs all PASS, LOAD 10.640s, UNLOAD 7.734s. No inferred zero-contact from silence. E/main/Owner 배포 미실행. E에서 full actual integrated mission+shutdown same-session 최종 검수.
