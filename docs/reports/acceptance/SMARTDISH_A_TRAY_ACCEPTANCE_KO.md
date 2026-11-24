# SmartDish A-11/A-12/A-13 — 최종 Gazebo L2 인수 및 WSL2 GUI L3 경계

- 보호 AI OFF main: `cc66b66a16ffc8020498d973ebe31a5c4ca439e0`, PR #44 merged.
- A 단독 브랜치: `feat/smartdish-a-tray-camera`; Draft [PR #45](https://github.com/silverbjin/samsung_AXI/pull/45) main **미병합**.
- 실증: [GitHub Actions #45325486957](https://github.com/silverbjin/samsung_AXI/actions/runs/45325486957), 코드 SHA `05779ae191ff41c922e067ec7cc5c2356dcffeaa`.
- CI: **L0 26 PASS, Jazzy L1 PASS, Gazebo Harmonic L2 4/4 PASS**. 별도 사용자 WSL2 GUI L3 **NOT_RUN**.
- 관측: ST-01/ST-02 `HELD_OBSERVED`, UN-01/UN-02 `FALL_OBSERVED`; 각 실제 RGB→B 캡처 함수 PNG 저장과 10s Pose 시계열·SHA 검증 성공.

| 요구 ID | 확인된 출처/조건 | 상태 |
|---|---|---|
| G-A11-01 | 실제 Gazebo camera Image 4회 | PASS(L2) |
| G-A11-02 | ROS2 Image stamp 0.200s, 640×480, RGB 포맷 validator 통과 | PASS(L2) |
| G-A11-03 | B 기존 `save_unlabelled_frame()`로 PNG 4건 | PASS(L2) |
| G-A12-01 | ST-01/ST-02/UN-01/UN-02 각각 독립 Gazebo 실행 | PASS(L2) |
| G-A12-02 | 실제 안정 유지 2·낙하 2 관측 | PASS(L2) |
| G-A12-03 | 동적 Pose JSONL 원본 파일·SHA 검증 | PASS(L2) |
| G-A13-01 | CLI batch 4 trials 독립 실행 | PASS(L2) |
| G-A13-02 | 새로운 trial/world/partition/domain과 별도 파일 | PASS(L0+L2) |
| G-A13-03 | `summary.json` verdict, trial SHA/시각 및 tar.gz | PASS(L2) |
| G-REG-01 | GitHub main→A compare 보호 자산 변경 0개 | PASS |
| G-CI-01 | L0 26/L1/L2 4개 실제 실행 | PASS(검증 SHA) |
| G-DOC-01 | 교육용 개발·디버깅·인계 보고서 GitHub 보관 | PASS(문서 기록) |
| G-PR-01 | Draft PR #45 생성/유지 | PASS |
| G-L3-01 | 사용자 WSL2 GUI 4개 실제 실행 및 영상 시야 검수 | NOT_RUN |
| G-B-LABEL | B 전문가 권리·물리 근거·정답 검수 | NOT_RUN |
| G-C-INFERENCE | C 실모델 AI ON 물리 영상 추론 | NOT_RUN |

현재 최종 인수 단계: **`READY_FOR_WSL2_ACCEPTANCE`**. 사용자가 현장에서 직접 GUI/실물리 증거를 첨부하기 전까지 `SMARTDISH_A_TRAY_WSL2_L3_PASS`를 보고서에서 주장하지 않습니다.

재검 원칙: 같은 검증 코드/World/기본 실행 옵션이면 기존 AI OFF 실제 주행 재검 생략. 카메라 실제 로봇 탑재 위치와 독립 overhead World의 시야 동등성은 별도 후속 항목입니다.

교육용 교차 추적: [A-11](../tasks/SMARTDISH_A11_TRAY_RGB_EDU_KO.md) / [A-12](../tasks/SMARTDISH_A12_PHYSICS_SCENE_EDU_KO.md) / [A-13](../tasks/SMARTDISH_A13_DATA_COLLECTOR_EDU_KO.md) / [DBG-09](../issues/SMARTDISH_A13_DBG_09_CAMERA_FIRST_FRAME_KO.md) / [DBG-10](../issues/SMARTDISH_A13_DBG_10_READINESS_TEST_KO.md).
