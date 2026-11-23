# S6 WSLg — G01 최초 오류 분류 및 보존 (주니어 교육 보고서)

2026-11-23 | 개발 브랜치: fix/s6-wslg-gui-opengl-cycle01-20261123 | 기준 S6 성공 SHA: 937fbf025cefec01489c40bc5104c39e3d4709be

## 입력 데이터와 RED 재현
- 사전검사 원본: samsungaxi_gui_20261123T023209Z-4724.zip / SHA256 7c5b717f30fc0efece150add76d06a4e751b68b1ca0a969ec2db165dc0f2b801 / PASS_NO_GOAL.
- 실패 원본: samsungaxi_gui_20261123T023211Z-4761.zip / SHA256 e045f50f6e66c305eed22885d37c1fa533b20bfe37c720f82b07adaa190aa8d3 / RUN_RC=1.
- 실패 ZIP status.txt: GOAL_AUTHORIZED=FALSE, GOAL_SENT=UNKNOWN, FIRST_FAILED_MARKER=OWNER_NONZERO_EXIT.
- 실패 ZIP ci-s3-summary.txt: line 74 GUI OpenGL context failure → line 84 gazebo GUI aborted → line 87 rcl context invalid → Nav2/lifecycle/RViz shutdown.
- 기본 OpenGL=llvmpipe, 별도 GALLIUM_DRIVER=d3d12 GPU probe=NVIDIA accelerated. glxinfo 성공은 Qt/OGRE 정상 작동을 보장하지 않습니다.

## 프로세스/데이터 파이프라인
원샷 → S6 wrapper(GPU 환경 선택) → Owner/Tty 승인 → restaurant_demo.sh → ci_s3_amcl_smoke.py → navigation.launch.py → world.launch.py → [Gazebo server, Gazebo GUI, ROS bridge, AMCL/Nav2, RViz]. GUI OpenGL 실패가 on_exit_shutdown=true로 상위 Launch를 종료했을 가능성이 높습니다. 이 인과 가설을 G03/G04에서 확인합니다.

## 구현과 GREEN 조건
- scripts/s6_wslg_first_failure.py: ZIP 읽기 전용, 최초 Qt/OpenGL 오류와 뒤따른 context 종료를 별도 기록, 원본 SHA256 보존.
- tests/test_s6_wslg_first_failure.py: OWNER_NONZERO_EXIT가 있어도 Qt 오류가 1차로 분류되는지 및 GOAL_SENT UNKNOWN 보존 여부 검증.
- 명령: python3 scripts/s6_wslg_first_failure.py --zip <input.zip> --out <analysis.json>
- 실제 WSL2 GUI 자체는 아직 복구되지 않았으므로 이 사이클에서 GREEN은 오류 분류 코드 L0에만 해당합니다.

## 초심자 이해·확인 질문
1. 왜 Launch 종료 코드 0을 Nav2 Goal 성공으로 해석하면 안 될까요? 상위 프로세스 종료와 기능 완료는 별개이기 때문입니다.
2. 왜 Goal 마커가 없다는 이유만으로 GOAL_SENT=FALSE라 기록하면 안 될까요? 기록 누락과 실제 미발행을 구별할 원본이 없기 때문입니다.
3. SHA256이 필요한 이유는? 원본 수정을 막지 못하더라도 사후 변경 여부를 검출할 수 있기 때문입니다.

## 판정과 출처
- RED 원본 분석: PASS. 코드 L0: CI 전 NOT_RUN. Gazebo GUI WSL2 현장 GREEN: NOT_RUN. S6 기존 L2는 CI #45098202033 PASS 보존.
- 외부 참고: https://gazebosim.org/docs/harmonic/troubleshooting/ 및 https://github.com/gazebosim/ros_gz/issues/494
- 다음 사이클: G02-G03 최소 GUI 렌더링 단독 재현, G04 GUI 종료 소유권 최소 수정.
