# SAMSUNGAXI S6 G01~G09 디버깅 총괄 — 교육 및 WSL2 최종 인계

작성일 2026-11-23, GitHub Release 후보 `release/s6-wslg-gui-reaccept-20261123`.

## I. 기초 RED와 성공 기준
- 현장 실패 ZIP `samsungaxi_gui_20261123T023211Z-4761.zip` SHA256 `e045f50f6e66c305eed22885d37c1fa533b20bfe37c720f82b07adaa190aa8d3`: 최초 `[GUI][QT] Failed to create OpenGL context`, 후속 Gazebo GUI core dump→ROS context invalid→Nav2 Launch 종료. NO_GOAL 사전검사 ZIP은 PASS.
- 기존 안전 기능 성공 SHA `937fbf025cefec01489c40bc5104c39e3d4709be`와 CI #45098202033 불변 보존. 운영자 TTY 승인 없이 Goal 금지.

## II. 사이클별 RED→GREEN 추적
| 사이클 | 최초 실패/요구 | 수정·증거 | 상태 |
|---|---|---|---|
| G01 | 포괄적인 OWNER_NONZERO_EXIT가 Qt 첫 실패를 가림 | ZIP 읽기 전용 GUI 첫 오류 classifier 및 sha256 | L0 PASS / L3 HOLD |
| G02-G03 | GLXINFO accelerated=yes여도 Qt 컨텍스트 생성 실패 | 프로세스별 baseline/xcb/XWayland/D3D12/llvmpipe 독립 비교 NO_GOAL 진단 | L0 PASS / 강사 A/B NOT_RUN |
| G04-G05 | GUI abort 후 server/Nav2까지 연쇄 종료 | S6 scoped XCB, GUI exit 독립, 원본 오류 선제 분류·Goal 차단 | L0 PASS / GUI L3 HOLD |
| G06 | 재현 가능한 인수 원샷 필요 | GitHub 불변 SHA 다운로드+NO_GOAL+TTY 승인 | L0 PASS |
| G07 | 오류 인지 코드는 실제 주행보다 먼저 차단해야 함 | 진짜 spin_once 함수에 Qt abort 오류주입 | L0 PASS / 실물 GPU NOT_RUN |
| G08 | 구버전 후보 L2의 반환 FollowPath ack timeout 및 Map/Lifecycle 응답 타임아웃 | 실패 2회를 모두 보존, 원인 분류·안전 HOLD | 옛 SHA L2 FAIL, 원본 보존 |
| G09 | Jazzy BT 기본 20ms 응답 대기, Gazebo와 Nav2 초기화 경합 가설 | **S6 전용 10초 stagger + BT ack 200ms**, 기존 S5 원본 불변 | **새 SHA L0/L1/L2 PASS** |

## III. 실제 Gazebo GREEN 원본 (검증하지 않은 범위는 제외)
- [G09 실제 CI #45106929216](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216); 런타임 SHA `9d402a991d1ee0a1c46027abe91a55266b69d9bd`.
- TABLE_3 5.137m, AMCL 0.206m SUCCEEDED → 도착 후 RGB 3프레임 → 실제 학습된 모델 STACKED 신뢰도 0.6652 → PICKUP_RETURN 5.054m, AMCL 0.160m SUCCEEDED.
- 메뉴별 속도 0.23 / 0.11m/s, 실제 LiDAR polygon 29점, CM STOP, `/cmd_vel` 0m/s(68개 표본), Odom 0m.
- 원본 이미지 sha256 `4922a3f48d75ceb8206e67b20c54b35b54595a2eb51649f5566f827d6454e7a5` 및 [CI ZIP #14787673933](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216/artifacts/14787673933) 원본 해시 `a9ee749ef91586b27a19de04e6e2cc902176701d3f66971c4225ab1a96cd528c`.
- **정확한 의미**: 이 성공은 일반 GitHub-hosted Ubuntu의 실제 Gazebo simulation L2. 강사 NVIDIA WSLg GUI L3는 아님.

## IV. 주니어 교육 과정
1. 완전한 오류 타임라인 만들기: GUI OpenGL first fail vs ROS 뒤따른 shutdown.
2. A/B 설계: 환경변수는 subprocess에만 적용; glxinfo와 Qt OGRE 컨텍스트는 서로 다른 검증.
3. Launch lifetime 이해: 왜 GUI가 죽어도 서버/안전 노드를 임의로 죽이면 안 되는가? GUI 실패를 성공으로 가릴 수 없는 이유는?
4. RED→GREEN 실제 이미지/주행: TABLE_3 → 정지 Odom → 최신 RGB → Vision STACKED → 반환 Goal → CM STOP.
5. 단일 반례와 불확실성: 옛 SHA의 2회 실패는 이유가 달랐고, 로그만으로 CPU 경합이 확정된 것은 아님.
6. 정적 L0, 빌드 L1, 실제 CI Gazebo L2, 강사 WSL2 GUI+주행 L3를 독립적으로 판정.

## V. 다음 WSL2 최종 인수
- 실행기 원본 불변 Git SHA `6fc1ac685858cb075e56514e03f72ad3a504fd87`의 `scripts/samsungaxi_s6_wslg_reaccept_once.sh`. 내부 런타임 SHA는 `9d402a991d1ee0a1c46027abe91a55266b69d9bd`.
- GUI 3D 장면이 실제로 보이는지 확인하고 운영자 TTY `YES-S5-LIVE-GOALS` 직접 입력. 실제 Action 2개 SUCCEEDED+RGB+STOP이 한 실행에 있는 ZIP을 인수 기준으로 합니다.
- 그래픽 장애 재발시 동일 원샷 `--diagnose-only`로 Qt renderer A/B만 구분해 작은 ZIP을 보존. Goal 없음.
- **L3 상태** NOT_RUN; **main** 기존 SHA 유지, PR #30/#31 DRAFT, 자동 병합 금지. RTF≥0.90 및 범용 식기 AI 모델 정확도 HOLD.

## 관련 GitHub 문서
- [G01 보고서](20261123_G01_FIRST_FAILURE_EDU_KO.md)
- [G02/G03 보고서](20261123_G02_G03_GL_AB_EDU_KO.md)
- [G04/G05 보고서](20261123_G04_G05_GUI_LIFECYCLE_EDU_KO.md)
- [G06 보고서](20261123_G06_RELEASE_EDU_KO.md)
- [G07 보고서](20261123_G07_GUI_FAULT_INJECTION_EDU_KO.md)
- [G08 보고서](20261123_G08_NAV2_RETURN_ABORT_EDU_KO.md)
- [G09 보고서](20261123_G09_NAV2_CONTROLPLANE_EDU_KO.md)
