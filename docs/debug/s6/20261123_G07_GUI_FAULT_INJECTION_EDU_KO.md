# S6 G07 — 실제 런타임 GUI 로그 가상 실패주입 테스트·교육 보고서

## 문제
상위 Launch는 종료 코드 0으로 끝나더라도 Gazebo GUI OpenGL 실패나 ROS 파이프라인 성공을 대변하지 않습니다. 실제 WSL2 GUI를 CI에서 재현하기 어려우므로, GUI 실패 문자열을 주입해 Goal 전에 멈추는 **실제 런타임 코드 경로**를 별도로 검증합니다.

## 방법
테스트는 scripts/ci_s3_amcl_smoke.py의 중첩 함수 spin_once를 Python AST로 추출하여, ROS 모듈 없이 원본 함수 내용을 실행합니다. args/proc/rclpy/node만 검수용 fake 객체로 대체합니다. 테스트 중 실제 ROS 노드나 Nav2 Goal은 없습니다.

## RED 입력과 GREEN 기대 결과
| 입력 | 사전 조건 | 기대 결과 |
|---|---|---|
| Gazebo GUI Failed to create OpenGL context | S6 + GUI True | S6_GUI_OPENGL_CONTEXT_CREATE_FAILED 예외, ROS spin=0 |
| Gazebo GUI Aborted (core dumped) | S6 + GUI True | S6_GUI_PROCESS_ABORTED 예외, Goal=0 |
| 동일 오류 | S5 기본 | 기존 S5 경로를 임의 변경하지 않음 |
| 동일 오류 | S6 headless | GUI 모드 아님, 실제 ROS spin 지속 |
| Launch 종료 코드 0 | S6 | S3_NAV2_LAUNCH_EXITED:0 예외, Goal 성공으로 오판 금지 |

## 주니어 교육 핵심
- **실패주입(Fault Injection)**: 실제 GPU 고장을 만들지 않고 관련 입력을 강제로 재현하여 방어로직을 검증합니다.
- **의존성 격리**: ROS와 Gazebo가 설치되지 않은 L0에서도 Python AST로 비즈니스/오류 처리 함수의 실제 소스를 실행할 수 있습니다.
- **실행경로 커버리지**: 문자열 존재만 검사하는 것과, 해당 오류가 실제 예외를 발생시키는지 검사하는 것은 다른 수준입니다.
- **LIMIT**: 이 테스트의 GREEN은 '에러 감지 코드'에 한정됩니다. WSLg Qt/GPU 그래픽이 고쳐졌다는 뜻이 아니며, GUI 화면 L3 검수는 NOT_RUN입니다.

## 실행
python3 -m pytest -q tests/test_s6_wslg_gui_injected_failure.py

## 소스 무결성과 증거
- 런타임 코드는 변경하지 않았습니다. 기존 CI L0/L2 대상 런타임 SHA는 611ac7b9edf5aa275dc4dbbde86530a573165a77.
- G07은 새 회귀 테스트와 보고서만 릴리스 후보 브랜치에 추가하며, 실제 Gazebo L2를 불필요하게 재실행하지 않습니다.
- 이 커밋의 독립 L0 성공은 신규 릴리스 CI에서 확인해야 합니다. WSL2 현장 L3는 미인수입니다.
