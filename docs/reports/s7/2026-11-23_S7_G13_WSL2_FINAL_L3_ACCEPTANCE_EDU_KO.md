# S7 G13 — 강사 WSL2 최종 L3 인수 검토 및 main 병합 심사

2026-11-23. 기능 인수 소스 SHA: **097e5aca022f59b18f289e7d383a3a6b85a5da1a**.

## 1. 원본 무결성과 실행 SHA
| 제출 파일 | SHA256 | CRC | 판정 |
|---|---|---|---|
| samsungaxi_gui_20261123T045023Z-454.zip | 52e8c96d0dd2086b5dbba2138c6ba9c41287262428716fdfbb013ce4be3144fc | PASS | NO_GOAL 사전검사 PASS |
| samsungaxi_gui_20261123T045024Z-491.zip | 8d368281949b60ab130afa8ac4e7ece0423080f18838e414a9a85501eae5998d | PASS | 실제 S7 주행·Vision·STOP 기능 PASS |

원본 ZIP은 현장 정보가 포함되어 공개 GitHub에 올리지 않고 원본 SHA256과 핵심 수치만 기록합니다.
사전검사 PIN=PUBLIC_SOURCE_SHA=097e5aca...; RUN_RC=0, GOAL_AUTHORIZED=FALSE, GOAL_SENT=FALSE, VERDICT=PREFLIGHT_PASS_NO_GOAL.
실주행 PIN=PUBLIC_SOURCE_SHA=OWNER_SOURCE_SHA=097e5aca...; GOAL_AUTHORIZED=TRUE, GOAL_SENT=TRUE, FIRST_FAILED_MARKER=NONE.

## 2. 요구사항 → 실제 관측 → 판정
| 요구사항 | 실제 WSL2 원본 증거 | 판정 |
|---|---|---|
| 시작 식기 | S7 scene stacked, fixture_preloaded_at_world_start=true, dynamic_fixture_spawn_requested=false. world SHA256 914e09c51c55a8f531eb8b95b977def9ed1508cf6d608212f64aabdf5e31a8ff | PASS |
| TTY·센서 freshness | 수동 승인 8.848초 후 scan age=0s, odom age=0.005s | PASS |
| Nav2 TABLE_3 | Action status 4 SUCCEEDED, Odom 5.093m, AMCL error 0.247m | PASS |
| 실제 RGB | 정지 후 320×240 3프레임, captured_after_arrival=true, captured_after_subscribe=true | PASS |
| 이미지 출처 | P6 헤더 제외 RGB 230400바이트 SHA256 66b347204e38320da31698413f8e58e57cf4bddfde2bd1b10d04f41454708239, Vision JSON과 일치 | PASS |
| AI 판단 | learned-prototype STACKED confidence 0.6635, REAL_RGB_MODEL_INFERENCE, authorized=true | PASS (고정 Gazebo 식기 시점 한정) |
| Nav2 PICKUP_RETURN | Action status 4 SUCCEEDED, Odom 5.026m, AMCL error 0.155m, s6_return_goal_sent=true | PASS |
| 메뉴 속도 | NORMAL/SOUP p75 0.23/0.11m/s | PASS |
| LiDAR 안전 | 장애물 29점, CM STOP, upstream cmd 0.08m/s, downstream 69표본 최대 0m/s, 실제 odom 정지 0m | PASS |
| 통합 | S6/Vision 및 S7 startup 성공 마커, 최초 실패 NONE | PASS |
| 빈 테이블 | 현장에서는 미실행, 실제 GitHub Gazebo CI #45112942260에서 RGB 3프레임 NOT_STACKED 후 복귀 Goal 0건 실증 | PASS (CI L2) |
| 시각 검수 | 사용자 책임, 자동 인수 게이트 제외 | NOT_GATE |
| RTF 90% | WSL2 이동 중 median 0.704, 전체 median 0.7437 | HOLD |

Vision 내부 snapshot return_goal_sent=false는 그 시점 값이며 최종 s6_return_goal_sent=true와 실제 반환 Action 성공이 확인되어 미발행으로 오진하면 안 됩니다.

## 3. 별도 기술 이슈 및 안전한 판정
- RUN_RC=130은 기능 성공 후 Ctrl+C로 종료한 결과와 일치하나, 전체 종료 무오류 PASS를 의미하지 않습니다.
- RViz GLSL indexed_8bit_image shader link error, SIGINT 종료 중 terminate called without an active exception 및 rviz2 exit -6이 관측됐습니다. GUI/종료 안정화 별도 백로그에 보존합니다.
- 사용자 승인 정책에 따라 GUI 육안 검수는 자동/병합 게이트에서 제외합니다. 그러나 ROS 이미지·Nav2 Action·Collision Monitor 실제 기능 인수는 계속 필수입니다.
- RTF 이동 중앙값 0.704는 90% 목표 미달이며 이번 릴리스 게이트가 아닌 HOLD입니다.
- 이번 현장 결과로 일반 식기·새 조명/각도 모델 정확도나 현장 빈 테이블 음성 재실행 성공을 주장하지 않습니다.

## 4. GitHub CI 및 주니어 개발 이력
- S7 실제 양성·음성 Gazebo L0/L1/L2: https://github.com/silverbjin/samsung_AXI/actions/runs/45112942260 (PASS).
- 해당 원본 Artifact: https://github.com/silverbjin/samsung_AXI/actions/runs/45112942260/artifacts/14790562351.
- 강사/학생 교육 코드 L0: https://github.com/silverbjin/samsung_AXI/actions/runs/45113383076 (PASS), 교육 PR #34는 S7 기능 브랜치에 병합.
- S7 최종 기능 브랜치 실 Gazebo CI: https://github.com/silverbjin/samsung_AXI/actions/runs/45113799703 (PASS).
- S7 최종 기능 브랜치 MVP CI: https://github.com/silverbjin/samsung_AXI/actions/runs/45113860623 (PASS).
- 앞선 RED: 처음 S6는 Goal 도착 후 dish create; S7은 시작 static dish로 수정. 처음 S7 전체 L2 workflow YAML step name colon 오류(#45112888666)는 ROS 장애가 아니라 workflow 문법 RED로 분리하여 최소 수정. 실제 L2 GREEN 확보.
- 주니어 보고서: S7-01 startup scene, S7-02 ROS/Goal, S7-03 empty no-return, S7-TEACHING-01, S7-ACCEPT-01 문서와 본 최종 G13 검수.

## 5. 결론과 인수 범위
**강사 WSL2 S7 양성 기능 L3 PASS.** 기능·원본 데이터·동일 source SHA·실 Gazebo CI·교육 문서 모두 검수돼 PR #35 main 병합 요건이 충족됩니다.
이 문서는 병합 이전 검수 결과이며 실제 merge commit은 GitHub PR #35 결과로 확인합니다.
남은 별도 이슈: RViz 셰이더/종료 예외, Vision 일반화, 실제 이미지 timeout 고장 주입, RTF≥90% (HOLD).

### 학생 토론 질문
1. Nav2 Action SUCCEEDED와 실제 Odom/AMCL 도착 판정을 왜 함께 확인합니까?
2. PPM raw RGB SHA와 전체 파일 SHA는 왜 다릅니까?
3. 빈 테이블의 HOLD가 단순 프로세스 오류와 다른 이유는 무엇입니까?
4. GUI 육안 검수가 제외되어도 실제 이미지·안전 STOP이 자동 필수인 이유는 무엇입니까?
5. main 병합 SHA와 실제 L3 runtime SHA가 달라질 수 있는 이유는 무엇입니까?
