# S6 G11 — 강사 WSL2 최종 기능 L3 인수 및 main 병합 심사 (2026-11-23)

## 인수 정책 및 최종 판정
**S6 기능 L3 PASS.** 강사 WSL2 실제 실행은 CI L2 성공 SHA 9d402a991d1ee0a1c46027abe91a55266b69d9bd와 동일합니다. 주행/영상/안전 원본 증거를 통과했습니다.

**GUI 화면의 시각적 육안 검수는 사용자가 담당하며 자동 기능 인수 및 main 병합 게이트에서 제외합니다.** 기존 ZIP의 WSL2_GUI_ACCEPTED=NOT_RUN_UNTIL_HUMAN_VISUAL_CHECK 및 VERDICT=GUI_VISUAL_REVIEW_REQUIRED는 이전 실행기의 안내 마커이며, 기능 실패로 승격하지 않습니다. 이 정책 변경으로 실제 이미지/ROS Action/안전 STOP 체크를 제외하지 않습니다.

## RED 원본과 GREEN 현장 파일
| 자료 | 원본 ZIP SHA256 | 내용 |
|---|---|---|
| samsungaxi_gui_20261123T041032Z-1810.zip | 310322ea4190e26934ccda0dd8bea55313a76469ce1c653ddb8e75ccd0449f70 | NO_GOAL 사전검사 PASS |
| samsungaxi_gui_20261123T041033Z-1847.zip | 557bfe00b8be2203470c1bca15589a0112814bb3dd1286ce39f6c08a9073dfe9 | WSL2 실제 Action·Vision·CM 증거 |

두 ZIP 모두 CRC 검사 PASS. 개인정보와 로컬 환경정보가 포함될 수 있으므로 원본 ZIP을 공개 GitHub에 업로드하지 않고 해시와 최소 요약만 기록합니다.

## 요구사항→실제 관측→판정
| 요구사항 | 원본 증거 | 판정 |
|---|---|---|
| 동일 SHA | PIN=PUBLIC_SOURCE_SHA=OWNER_SOURCE_SHA=9d402a991d1ee0a1c46027abe91a55266b69d9bd | PASS |
| NO_GOAL | RUN_RC=0, GOAL_AUTHORIZED=FALSE, GOAL_SENT=FALSE, PREFLIGHT_PASS_NO_GOAL | PASS |
| 운영자 TTY 승인 | 31.859초 대기 후 승인, 승인 후 /scan age 0.000s, Odom age 0.007s | PASS |
| TABLE_3 | Nav2 Action status=4 SUCCEEDED, Odom 5.138m, AMCL error 0.183m | PASS |
| 정지 이후 RGB | Odom speed 0, 이미지 3프레임 320×240, captured_after_arrival=true, captured_after_subscribe=true | PASS |
| Vision AI | learned prototype STACKED, confidence=0.6652, REAL_RGB_MODEL_INFERENCE | PASS (고정 fixture 시나리오 한정) |
| RGB 무결성 | PPM P6 헤더를 제외한 RGB 230400바이트 SHA256 = 3a28475d8568b5a59d088796376c1e6539d6aa16b58d5cc9e7477626ef6ad492; JSON과 일치 | PASS |
| PICKUP_RETURN | Vision 승인 뒤 Action status=4 SUCCEEDED, Odom 5.079m, AMCL error 0.139m | PASS |
| 메뉴 속도 | NORMAL p75=0.23 m/s, SOUP p75=0.11 m/s | PASS |
| 실제 LiDAR STOP | 29점, cm_state=STOP, upstream positive command, downstream 44표본 max=0.0m/s, odom drift=0.0m | PASS |
| 통합 | s5_integrated=true, s6_integrated=true, FIRST_FAILED_MARKER=NONE | PASS |
| 사용자 GUI 시각 | 별도 운영자 확인 영역 | OWNER-ONLY, NOT A GATE |
| RTF 90% | moving median=0.4975, overall median=0.5508 | HOLD, 기능 릴리스 차단 아님 |

## 종료·그래픽 주의사항 (비차단 후속 이슈)
RUN_RC=130은 모든 통합 성공 마커 출력 뒤 사용자가 Ctrl+C로 SIGINT 종료한 사실과 부합합니다. Gazebo server/GUI와 다수 ROS 노드는 clean finish를 기록합니다. RViz 맵 셰이더 GLSL link 오류와 종료 중 'terminate called without an active exception'은 관측됐으므로 GUI/종료 *무오류*라고 주장하지 않습니다. 해당 이슈는 별도 후속 유지보수 대상으로 보존하고 S6 핵심 기능 인수와 구분합니다.

## 주니어 교육을 위한 RED→GREEN
1. 과거 RED: G01 OpenGL GUI context fail, G08 Nav2 FollowPath ACK/Map lifecycle timeout; 잘못된 SHA 또는 과거 성공을 이번 SHA의 PASS로 사용하지 않기.
2. L2 GREEN: GitHub 실제 Gazebo [#45106929216](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216)에서 동일 SHA Nav2 2 Goal + RGB STACKED + CM STOP PASS.
3. L3 GREEN: 위 강사 WSL2 ZIP 2건에서 NO_GOAL·Goal 2개·PPM 해시·정지 증거를 실증으로 재확인.
4. 기능과 GUI를 분리: 사람 눈으로 보는 지도와 카메라 화면은 사용자 영역; 이미지 원본 바이트·Nav2 Action·CM STOP은 자동 기능 인수.
5. Action 상태 코드 4는 SUCCEEDED이고, 게이트 스냅샷의 return_goal_sent=false와 실제 통합 필드 s6_return_goal_sent=true가 다른 시점 값임을 설명하기.
6. 성공 뒤 Ctrl+C로 인한 RC=130을 곧바로 기능 실패나 완전한 graceful shutdown 증명으로 혼동하지 않기.

## 변경 범위와 릴리스 정책
이번 G11 보고서는 문서 및 검수 정책 변경만 수행하며 성공한 S6 코어/지도/Collision Monitor/Goal을 수정하지 않습니다. 기존 실행기가 출력하는 GUI_VISUAL_REVIEW_REQUIRED는 정책상 정보성 표시이며 기능 릴리스 판정을 덮지 않습니다.

후속 작업은 [S6 릴리스 이후 로드맵](../../S6_POST_RELEASE_ROADMAP_KO.md)을 참조하십시오. 새로운 기능은 별도 브랜치·각 사이클 주니어 교육 보고서·범위별 CI로 검수합니다.
