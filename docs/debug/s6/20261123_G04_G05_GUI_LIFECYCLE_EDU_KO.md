# S6 G04/G05 — WSLg GUI 종료 격리·안전 차단 및 최소 수정 교육 보고서

## 1. 입력·RED
- 2026-11-23 S6 현장 원본 SHA e045f50f... 에서 GUI context 실패 → Gazebo abort → 상위 Launch 0 종료 → Nav2 context invalid. 기존 world.launch.py는 GUI/서버에 모두 on_exit_shutdown=true.
- 공식 Gazebo Harmonic 문서는 Qt/Ogre Wayland 충돌의 XCB 우회법을 제공하고, ros_gz_sim gz_sim.launch.py 최신 코드는 문자열 false일 때 shutdown 이벤트를 붙이지 않도록 구현되어 있습니다.
- ros_gz #494 이슈에는 이전 버전에서 on_exit_shutdown 문자열을 boolean으로 취급한 버그가 기록되어 있으므로 설치된 Jazzy 버전에서는 실제 동작을 반드시 확인해야 합니다.

## 2. 서버·GUI 프로세스 아키텍처 및 변경
원샷 → 래퍼(기존 NVIDIA 프로브) → Owner → restaurant_demo.sh → ci_s3_amcl_smoke.py → navigation.launch.py → world.launch.py → Gazebo server/GUI/RViz/Nav2.
- src/restaurant_bringup/launch/world.launch.py: GroupAction(scoped=True)로 GUI 서브프로세스에만 QT_QPA_PLATFORM=xcb를 선택적으로 적용합니다. 서버는 기존 on_exit_shutdown=true를 보존합니다. GUI의 on_exit_shutdown 값만 S6에서 false로 설정합니다.
- navigation.launch.py: 신규 인수를 세계 Launch에 전달하고, 기본값 false/true로 두어 기존 S5와 기타 교육 모드를 보존합니다.
- ci_s3_amcl_smoke.py: S6 GUI 모드에서만 XCB+GUI-종료 분리 인수를 전달합니다. ROS Launch 로그에 Qt context 오류가 있으면 즉시 S6_GUI_OPENGL_CONTEXT_CREATE_FAILED로 fail closed 처리하여 Goal을 보내지 않습니다.
- samsungaxi_wsl2_gui_acceptance_once.sh: S6에서는 glxinfo 성공만으로 D3D12를 강제하지 않습니다. 이후 현장 실험에서 고를 수 있도록 상속 GPU 환경을 보존합니다. 기존 S5 GPU 경로는 변경하지 않습니다.
- 동일 실행의 GUI 프로세스 exit 로그, 최신 Launch tail, 실제 S6 RGB PPM을 작고 추적 가능한 ZIP에 포함합니다.

## 3. GREEN 검증·반증
- L0: scoped GPU/Qt, GUI 종료 플래그, 서버 원본 shutdown, GUI 실패 문자열 분류, 원본 S5 기본 Launch, TTY 승인 계약 검증.
- L1: 공식 Jazzy/Harmonic 빌드. L2: headless 실제 RGB/Scan/Nav2/STOP 통합 재회귀 (변경된 Launch 경계 때문에 필요).
- 독립 WSL2 G03 A/B: xcb 후에도 GUI가 실패하면 해당 해법을 L3 PASS로 승격하지 않고 실제 OpenGL 환경을 추가 격리합니다.
- GUI 프로세스가 살아 있음은 영상 렌더링이 보이는 것과 다릅니다. 육안·시각적 성공은 운영자의 명시적 확인이 필요합니다.

## 4. 실무 학습
- 실습 1: GroupAction scope와 SetEnvironmentVariable이 서버에 불필요한 Qt 환경을 전달하지 않는 이유를 설명하십시오.
- 실습 2: 서버는 필수이므로 종료 시 전체 Launch가 멈춰야 하지만, GUI는 선택 표시 계층이므로 종료 소유권을 분리하는 이유를 설명하십시오.
- 실습 3: on_exit_shutdown=false만으로 충분할까요? GUI가 사라져도 배달 Goal을 보내지 않도록 별도 감시가 필요합니다.
- 확인 1: OpenGL first failure와 ROS context invalid의 순서를 바꾸어 로그를 읽으면 어떤 잘못된 조치가 나올까요?
- 확인 2: glxinfo accelerated=yes가 Qt 실제 Window create의 충분 조건이 아닌 이유는?

## 5. 불변 영역과 판정
지도/AMCL, /scan Costmap, CM STOP, NORMAL/SOUP 속도, Vision STACKED 후 복귀, TTY 승인 코드의 의미는 변경하지 않았습니다. 기존 S6 기능 PASS SHA 937fbf025cefec01489c40bc5104c39e3d4709be의 증거를 보존합니다.
- 현재 L0/L1/L2 및 WSL2 검증은 이 변경 SHA의 CI 확인 전이며, 이 문서는 코드 출고에만 해당합니다. main 병합 HOLD. RTF 90% HOLD.
