# S7-ACCEPT-01 — 실제 Gazebo L0/L1/L2 최종 검증 및 WSL2 인수 인계

작성일: 2026-11-23. 기능 검증 원본 SHA **097e5aca022f59b18f289e7d383a3a6b85a5da1a**. 이 보고서는 GitHub Actions의 완료된 로그에 기반하며 강사 WSL2 L3 결과를 미리 PASS로 처리하지 않습니다.

## 1. 범위별 판정
- S7 실제 Gazebo L0/L1/L2: **PASS**.
- 강사 WSL2 L3: **NOT_RUN**. 동일 SHA 원샷 출고 후 ZIP 현장 검수 필요.
- 사용자 GUI 시각 검수: OWNER-ONLY / NOT_GATE.
- RTF 90%: HOLD.
- main 병합: **보류**. L3 증거 검수 후 결정.

## 2. 원본 CI·Artifact
- [실제 S7 CI #45112942260](https://github.com/silverbjin/samsung_AXI/actions/runs/45112942260): Git SHA 097e5aca022f59b18f289e7d383a3a6b85a5da1a. L0·L1·L2 SUCCESS.
- [실제 양성·음성 원본 Artifact #14790562351](https://github.com/silverbjin/samsung_AXI/actions/runs/45112942260/artifacts/14790562351).
- [교육용 정답/학생 TODO L0 CI #45113383076](https://github.com/silverbjin/samsung_AXI/actions/runs/45113383076): PASS, 교육 PR #34 기능 브랜치에 병합 완료.
- 교육 자료는 기능 검증 SHA 뒤에 커밋됐으나 Gazebo/Nav2/CM 실제 런타임 파일은 변경되지 않았습니다. 출고 실행기는 검증 SHA 하나로 실행기와 실제 ROS 코드를 함께 선택합니다.

## 3. RED → GREEN 요구사항 추적성

| ID | 입력·조건 | 기대 결과 | 관측 원본 | 판정 |
|---|---|---|---|---|
| S7-01 | S5/S6 원본 restaurant.sdf | 원본 지도 및 SDF 불변 | STACKED/EMPTY 신규 generated SDF 생성·원본 유지 | PASS |
| S7-STARTUP | Gazebo 시작 시 stacked WORLD | 식기 1개 최초 배치·재스폰 없음 | world SHA256 914e09c51c55a8f531eb8b95b977def9ed1508cf6d608212f64aabdf5e31a8ff, no dynamic spawn | PASS |
| NAV-TABLE | 실제 TABLE_3 Goal | Action SUCCEEDED·실제 이동 | Odom 5.067m, AMCL 오차 0.251m | PASS |
| VISION | 도착/정지 후 요청형 RGB | 실제 이미지 기반 STACKED | S6_VISION_REAL_RGB_STACKED_RETURN_AUTHORIZED, 원본 PPM SHA 검사 | PASS |
| NAV-RETURN | 승인된 복귀 Goal | Action SUCCEEDED·실제 이동 | Odom 4.964m, AMCL 오차 0.183m | PASS |
| SAFETY | NORMAL/SOUP 및 실제 STOP | 0.23/0.11m/s, LiDAR·CM 정지 | 두 p75 실측 0.23/0.11m/s, LiDAR 29점, STOP·필터 및 Odom 제한 만족 | PASS |
| EMPTY | 접시 없는 월드·실제 RGB | NOT_STACKED/UNKNOWN | empty world SHA256 d9dd7847c826011695e9caf052c353fd8550c2b62917297673c21cc306597ed1, 실제 3프레임, NOT_STACKED | PASS |
| NO-RETURN | 빈 테이블 위험 차단 | 복귀 Goal 0건 | S7_REAL_EMPTY_TABLE_NO_RETURN_PASS, goal_sent=false | PASS |
| TEACHING | 초심자 교육 | 강사·학생·정답 분리 | 교육 L0 PASS, PR #34 병합 | PASS |
| OWNER-L3 | 강사 WSL2 동일 PIN | TABLE_3→RGB→RETURN→STOP | 원본 ZIP 아직 없음 | NOT_RUN |

## 4. 최초 실패와 원인 분리
- 기존 S6는 TABLE_3에 도착한 뒤 접시 모델을 스폰했습니다. S7은 시작부터 WORLD에 그 모델이 있으므로 도착 후 같은 모델을 추가하면 중복·충돌이 발생할 수 있습니다. S7은 월드 파일을 명시 연결하고 동적 스폰을 비활성화했습니다.
- 정적 SDF 분석만으로 Gazebo 성공을 주장하지 않았습니다. 실제 카메라의 RGB·Action·STOP 결과를 추가 확인했습니다.
- 빈 테이블의 Vision HOLD는 의도된 안전 동작입니다. 원본 런타임이 비영 종료했다고 성공으로 보지 않고 첫 Goal Action·RGB PPM SHA·두 번째 Goal 부재를 확인했습니다.
- 최초 full L2 workflow #45112888666이 YAML step name의 콜론 문법으로 실행 전 FAIL을 기록했습니다. 로봇 코드 FAIL이 아니므로 workflow 문법 수정 후 정상 실행 #45112942260에서 실제 Gazebo L2 PASS를 확보했습니다.

## 5. WSL2 단일 인수
[공식 S7 Owner L3 가이드](../../s7/S7_OWNER_L3_GUIDE_KO.md)를 사용하십시오.
- 실행기와 런타임 소스 동일 고정 SHA: 097e5aca022f59b18f289e7d383a3a6b85a5da1a.
- NO_GOAL 사전검사→실제 TTY 승인 YES-S5-LIVE-GOALS→Gazebo 최초 식기→TABLE_3→Odom 정지→새 RGB STACKED→PICKUP_RETURN→실제 LiDAR STOP.
- 성공 후 Ctrl+C로 생성된 preflight ZIP과 live ZIP 두 개를 제출해야 합니다. RUN_RC=130 자체를 실패나 무오류 종료 증거로 확대 해석하지 않습니다.
- 최종 PIN/Action/RGB 원본/STOP·FIRST_FAILED_MARKER 검수 후 main 병합 여부를 판정합니다.

## 6. 초심자용 보고서와 후속 질문
- [S7-01 시작 접시 생성](2026-11-23_S7-DISH-STARTUP-01_EDU_KO.md)
- [S7-02 실제 ROS/Nav2 시작 월드 연결](2026-11-23_S7-FLOW-STARTUP-02_EDU_KO.md)
- [S7-03 빈 테이블 안전 차단](2026-11-23_S7-VISION-NEGATIVE-01_EDU_KO.md)
- [S7-TEACHING-01 강사·학생 자료](2026-11-23_S7-TEACHING-01_EDU_KO.md)
- [강사용 시연 가이드](../../s7/INSTRUCTOR_DEMO_GUIDE_KO.md), [학생 가이드](../../s7/STUDENT_LAB_GUIDE_KO.md), [강사 정답](../../s7/INSTRUCTOR_SOLUTIONS_KO.md).

학습 질문: World model과 late spawn의 차이는? Action SUCCEEDED와 물리 정지는 왜 구분하나요? PPM 전체 해시와 RGB 원본 페이로드 해시 차이는? 빈 테이블은 왜 Goal 성공이 아니라 no-return 안전 차단의 증거가 핵심인가요?

향후 별도 범위: 이미지 누락 실제 fault-injection, 모델의 다른 조명/식기 일반화, RViz 표시·종료 이슈, RTF 90% 목표(HOLD).
