# SAMSUNGAXI — 강사 WSL2/WSLg Gazebo·RViz 원샷 검수

- 공개 저장소: https://github.com/silverbjin/samsung_AXI
- 현장 실행기: scripts/samsungaxi_wsl2_gui_acceptance_once.sh
- 고정된 실제 ROS 실행 소스: f39dc1757588b9f7cde1a56f73659f629c57e703
- 범위: Ubuntu 24.04 WSL2, ROS 2 Jazzy, Gazebo Harmonic, RViz2, 기존 S2 저장 지도, NO_GOAL / NO_MAPPING
- 강사 WSL2 GUI 화면 결과: NOT_RUN. 실제 사용자 시각 확인 후 승인할 것.

## 원샷 명령

아래 명령의 SRC_SHA는 **원샷을 올린 GitHub 커밋 SHA**로 고정해 사용하십시오. 검증된 원샷 출고 SHA는 최종 안내 메시지에서 제공합니다.

    SRC_SHA=<40자리_출고_SHA>
    SCRIPT="$(mktemp --suffix=.sh)"
    curl -fLsS --retry 3 --connect-timeout 10 --max-time 90 \
      "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$SRC_SHA/scripts/samsungaxi_wsl2_gui_acceptance_once.sh" -o "$SCRIPT"
    bash -n "$SCRIPT" && bash "$SCRIPT" --self-test && bash "$SCRIPT"
    rc=$?
    rm -f "$SCRIPT"
    exit "$rc"

기본값에서는 설치를 하지 않습니다. 기존 ROS 패키지가 빠졌고 설치 승인을 받은 경우에만 마지막 명령에서 bash "$SCRIPT" --install-deps 로 실행하십시오.

## 사용자 검수

1. Gazebo에 식당 전체 월드와 Waffle Pi 실물 모델이 표시되고 로봇/월드가 빈 창이 아닌지 확인.
2. RViz2에 Map, TF, LaserScan를 확인. Displays에서 Map /map, LaserScan /scan, Fixed Frame map 지정.
3. 메뉴별 속도나 실제 CM STOP이 이번 GUI 검사에서 다시 증명되는 것은 아닙니다. 공개 CI의 기존 실제 Gazebo 검증을 인용합니다.
4. NO_GOAL만 실행. 맵 다시 생성하거나 RViz Goal을 클릭하지 않음.
5. 약 40초 이상 센서 출력을 관찰한 뒤 터미널에서 Ctrl+C 한 번으로 종료.

## 오류 ZIP

- 출력: ~/samsungaxi_gui_evidence/samsungaxi_gui_날짜-프로세스ID.zip
- ZIP 내부: environment.txt, run.log, status.txt, error_clues.txt, log_tail.txt, ros_diagnostics.txt(40초 이상 구동 시), owner_tails.txt(있을 때).
- SAMSUNGAXI_DIAGNOSTIC_ZIP=... 경로의 ZIP 한 개만 전달하면 로그를 분석할 수 있습니다.
- 자동 verdict GUI_VISUAL_REVIEW_REQUIRED는 PASS가 아닙니다.
- 실제 WSL2 GUI 수동 관찰을 완료하지 않았다면 WSL2_GUI_ACCEPTED는 NOT_RUN입니다.
- 전역 pkill, 무단 /cmd_vel 발행, 새 Planner 또는 WSL2 재매핑 없음.

## 범위 확인

원샷은 GitHub에 고정된 owner_wsl2_once.sh의 navigation 모드를 이용합니다.
해당 버전은 navigation 모드 종료 시 delivery_manager로 떨어지지 않도록 패치되어 있습니다.
