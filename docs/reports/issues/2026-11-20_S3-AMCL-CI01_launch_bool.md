# S3-AMCL-CI01 — 공식 Nav2 bringup PythonExpression의 lowercase false

- 일자: 2026-11-20 KST
- 상태: RED 재현, 최소 수정 후보
- L2 실패 원본: [Run #44560469349](https://github.com/silverbjin/samsung_AXI/actions/runs/44560469349), job S3 L1+L2, 업로드된 `samsungaxi-s3-first-failure-44560469349` ZIP
- 최초 오류: `[ERROR] [launch]: Caught exception in launch ... name 'false' is not defined`.

## 원인
- 공식 Nav2 Jazzy `nav2_bringup/launch/bringup_launch.py`는 `IfCondition(PythonExpression(['not ', slam, ' and ', use_localization]))`를 포함합니다.
- LaunchConfiguration의 소문자 `false`는 이 PythonExpression 내부에서 Python의 `False`가 아니라 미정의 식별자로 평가될 수 있습니다.
- S3 navigation.launch.py에서 `slam:'false'`, `use_composition:'false'`, `use_respawn:'false'`를 문자열로 전달한 코드가 실패 경계입니다.
- ROS Map Server와 AMCL이 시작되기 전 에러이므로 실제 지도/SLAM 오작동으로 분류하지 않습니다.

## 최소 수정·재검
- PythonExpression에 전달되는 bool launch_arguments를 `True` / `False` 대소문자로 변경; 나머지 코드와 합격 기준 불변.
- L0 계약 테스트에서 `slam:'False'`, `use_composition:'False'` 확인.
- 실제 Gazebo Nav2-AMCL L2 재검 GREEN을 확보하기 전까지 이슈 해결 판정 보류.

## 교육 포인트
- ROS 2 Launch의 IfCondition과 PythonExpression은 불리언 문자열 처리 방식이 다를 수 있습니다. 프로세스가 뜨기도 전에 실패하면 센서/TF 대신 Launch 단계의 첫 예외부터 분석해야 합니다.

## RESOLVED — actual Gazebo regression GREEN
- [Run #44561573820](https://github.com/silverbjin/samsung_AXI/actions/runs/44561573820) official Nav2 lifecycle starts, released Map Server publishes actual saved map, AMCL publishes finite covariance and map→odom TF, Nav2 action server ready, NO GOAL.
- Code merged via PR #9, main 2e0b145983b621a3061cca5085fa5b88c87332f7. Launch bool error confined to launch_arguments; official ROS Nav2/SLAM not modified.
