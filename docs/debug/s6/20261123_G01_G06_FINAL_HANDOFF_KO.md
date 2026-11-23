# S6 WSLg 디버깅 사이클 총괄 — 인수 준비·RED→GREEN 근거·교육 활용

## 1. 현장 실패 원본과 재현 경계
- 사전검사 zip: samsungaxi_gui_20261123T023209Z-4724.zip, SHA256 7c5b717f30fc0efece150add76d06a4e751b68b1ca0a969ec2db165dc0f2b801. NO_GOAL PASS.
- 실제 실패 zip: samsungaxi_gui_20261123T023211Z-4761.zip, SHA256 e045f50f6e66c305eed22885d37c1fa533b20bfe37c720f82b07adaa190aa8d3. RUN_RC=1.
- 최초 오류: Qt/OpenGL context 생성 실패, 그 뒤 Gazebo GUI abort, ROS context invalid 및 Lifecycle 종료. 전역 최적화나 RTF 조정 없음.

## 2. 진단 주기 별 완료 상태
| 단계 | 변경 | 회귀 근거 | 범위 판정 |
|---|---|---|---|
| G01 | ZIP 최초 오류 계층 분류 | 신규 L0 회귀 28개에 포함 | 정적 PASS |
| G02/G03 | 5개 프로세스별 WSLg GPU/Qt 비교 진단 | 신규 L0 회귀 28개에 포함 | 코드 PASS, 강사 실제 A/B NOT_RUN |
| G04/G05 | S6 Qt xcb 스코프, GUI exit 분리, GUI 오류 Goal 전에 감지 | 신규 L0 회귀 28개에 포함 | 정적 PASS, 실제 NVIDIA GUI NOT_RUN |
| G06 | 새 GitHub 고정 SHA 원샷 및 --diagnose-only, TTY 검사 | 릴리스 CI #45104827199 | L0 PASS, 실제 L3 NOT_RUN |

## 3. L0 CI 근거
- CI https://github.com/silverbjin/samsung_AXI/actions/runs/45104473441 의 L0 테스트 28/28 PASS.
- 신규 런타임 SHA: 611ac7b9edf5aa275dc4dbbde86530a573165a77. 기존 S6 동작 SHA 937fbf025cefec01489c40bc5104c39e3d4709be의 실제 L2 증거를 보존합니다.
- 변경 영향 런타임 L2는 CI 진행 중이므로 이 문서 작성 시점에 PASS가 아닙니다.

## 4. 남은 정확한 인수 조건
- 공개 CI 실제 S6 기능 L2 성공: TABLE_3 Action → Odom 정지 → 새 RGB 프레임 → STACKED → 복귀 → LiDAR STOP.
- 강사 WSL2 동일 SHA에서 실제 GUI context 오류 없이 3D 장면이 보여야 하고, TTY 승인 후 S6 전체 기능이 성공해야 합니다.
- 최종 원본 ZIP에서 first failure=NONE, Goal 2개 성공, Vision AI 이미지 해시, CM STOP, GUI 육안 확인을 독립적으로 검수합니다.
- WSL2 현장 결과와 무관하게 RTF 90% 목표는 HOLD; 기존 CI L2 PASS를 L3 PASS로 승격하지 않습니다.

## 5. 초심자 평가 질문
1. 왜 glxinfo accelerated=yes가 Gazebo GUI 정상 렌더링 보증이 아닌지 설명하십시오.
2. `on_exit_shutdown`은 런타임 안전 제어와 어떤 관련이 있고, GUI와 server에 같은 값을 적용하면 어떤 일이 발생할까요?
3. Why: `GOAL_SENT=UNKNOWN`을 FALSE로 임의 변경하면 안 될까요?
4. 편집하지 않은 S5 LiDAR/CM의 성공 증거는 왜 보존하고 새 GUI 경계만 검증할까요?

## 출처
- 공식 Gazebo Harmonic 문제해결 문서: https://gazebosim.org/docs/harmonic/troubleshooting/
- ros_gz #494 종료 인수 버그 이력: https://github.com/gazebosim/ros_gz/issues/494
