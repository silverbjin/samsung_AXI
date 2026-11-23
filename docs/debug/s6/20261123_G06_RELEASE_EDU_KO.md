> **역사적 G06 보고서:** G06 당시 실행한 SHA 611ac7...은 G09에서 교체됐습니다. `samsungaxi_s6_wslg_reaccept_once.sh`의 현재 유효 런타임은 9d402a...이며, 공식 인수 명령은 [단일 실행 가이드](../../S6_OFFICIAL_OWNER_ENTRY_KO.md)를 참조하십시오. 아래 NOT_RUN 표기는 G06 작성 시점 기록입니다.

# S6 G06 — WSL2 최종 현장 재인수 원샷 출고 및 주니어 교육 보고서

## 범위
- G01/G02-G03/G04-G05의 런타임 소스 SHA: 611ac7b9edf5aa275dc4dbbde86530a573165a77
- 이 파일은 **릴리스용 실행기 추가만** 수행하며 Nav2·Collision Monitor·식기 모델을 재개발하지 않습니다.
- 강사 WSL2 현장 OpenGL 문제의 GREEN은 아직 NOT_RUN. GitHub CI가 실제 Harmonic/Nav2를 검증한 뒤에만 후보 실행기를 안내합니다.

## 실행 순서와 안전
1. 고정 SHA에서 기존 Owner wrapper를 내려받습니다. SHA를 실행 시작 전 화면에 출력합니다.
2. 실행기 자체 Bash syntax/self-test → 기존 원본 NO_GOAL 사전검사.
3. Gazebo GUI/RViz 실제 화면을 확인한 운영자가 TTY에서 YES-S5-LIVE-GOALS를 입력할 때만 기존 두 Goal과 S6 Vision 게이트를 시작합니다.
4. GUI OpenGL 오류가 다시 발생하면 runtime의 GUI 로그 감지기가 실패를 판정하고 Goal로 넘어가지 않습니다.
5. --diagnose-only는 Gazebo GUI 전용 A/B 프로파일을 생성하지만 ROS/Nav2/Goal은 실행하지 않습니다. ZIP은 HOME/samsungaxi_gui_evidence에 생성됩니다.

## 오류주입 및 교육
- 셸 표준 입력을 파이프로 바꾼 테스트에서 LIVE 진입 자체를 차단하는 것이 중요합니다.
- 기존 wrapper의 GPU probe 성공과 Gazebo GUI OpenGL 컨텍스트 생성을 동일한 상태로 보고하지 않습니다.
- 각 디버깅 사이클별 검증 보고서를 docs/debug/s6/ 아래에서 확인하고 첫 실패 근거→가설→테스트→수정→GREEN 순서로 발표하십시오.

## 실제 인수 기대 증거
- S6_WSLG_PREFLIGHT_PASS_NO_GOAL → GUI 화면 육안 확인 → 운영자 승인 → TABLE_3 SUCCEEDED → 실제 Odom 정지 → RGB STACKED → PICKUP_RETURN SUCCEEDED → LiDAR STOP, 출력과 Odom 정지.
- CTRL+C 이후 진단 ZIP과 동일 RUN ID의 s6_table_rgb.ppm 원본이 존재해야 합니다.
- GUI 렌더러의 실제 가시성은 인간 검토 전에는 NOT_VERIFIED; RTF 90% HOLD.

## 단계 판정
- 개발 코드 작성: 완료. 릴리스 L0: NOT_RUN (CI 전). 런타임 전체 L2: 기존 확정 SHA 대비 신규 테스트 진행 중. 강사 WSL2 L3: NOT_RUN. main 병합: HOLD.
