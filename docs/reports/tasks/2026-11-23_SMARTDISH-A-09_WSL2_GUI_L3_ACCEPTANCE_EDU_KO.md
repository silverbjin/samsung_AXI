# SmartDish A-09 — WSL2 GUI 3구간 현장 인수 검수·교육 보고서

- 검수 일자: 2026-11-23 KST
- 범위: A_ROBOT_ONLY, Gazebo Harmonic + ROS2 Jazzy + AMCL/Nav2 실제 WSL2 L3
- 사용자 첨부 원본: `smartdish_a_owner_evidence.tar.gz`; **SHA256 `9edc0009713dda472c826859ea00a383dac8553b4c6f04a7e7771b0d0e990fbf`**
- 원본 내부: `summary.json`, `l3_evidence.json`, `build-tail.log`, `nav2-tail.log`, `adapter-tail.log`, `console-tail.log`
- 현장 구동 소스: `2ec54a0ea91566a1bd100aab569f25589dff3f05`
- 사용자 데이터 보호: 장비명·홈 디렉터리 절대경로·원본 콘솔 로그를 GitHub에 다시 게시하지 않고, 검증에 필요한 최소 수치만 기록함

## 1. 판정

원본 JSON과 터미널/Adapter 로그를 교차 확인했습니다.

- `summary.json`: `verdict=PASS`, `exit_code=0`, `first_error=null`
- `l3_evidence.json`: `verdict=ROBOT_ONLY_REAL_GAZEBO_WSL2_L3_PASS`, `gui_requested=true`
- AMCL과 지도의 `map` 좌표계, `map→odom`, `odom→base` TF 준비: 모두 확인
- `tty_policy=HUMAN_OPERATOR_TYPED_TO_DEV_TTY` 및 Adapter `SMARTDISH_A_OPERATOR_APPROVED` 관측
- **같은 `request_id`로 ROS JSON nav_result 3건, 세 구간 모두 SUCCEEDED**
- 운영 좌표 `HOME=(0,0,0)`, `T03=(5.25,0.38,-π/2)`, `DISH_RETURN=(-1.15,1.60,-π/2)` 확인

| 구간 | Nav2 | /odom 시작점 대비 최대 변위 | odom 수신 | /scan 수신 | 최종 AMCL 목표 오차 |
|---|---|---:|---:|---:|---:|
| TO_TABLE/T03 | SUCCEEDED | 5.162m | 655 | 131 | 0.186m |
| TO_RETURN/DISH_RETURN | SUCCEEDED | 6.498m | 933 | 187 | 0.134m |
| TO_HOME/HOME | SUCCEEDED | 1.978m | 557 | 111 | 0.175m |

위 /odom은 **누적 주행거리 아니며 구간 시작점으로부터의 최대 이동 변위**입니다.

판정: **`A_ROBOT_ONLY_WSL2_L3_PASS`**. C 모델·B 실제 데이터·D 상태머신 UI/10초/5초/COMPLETED·A+D 통합은 **NOT_RUN**. 이 결과를 `SMARTDISH_ALL_DONE`으로 승격하지 않습니다.

## 2. 로그의 GUI 종료 예외를 어떻게 해석하는가?

Nav2 로그 뒷부분에 Gazebo/RViz의 종료 처리 중 `SIGINT`와 `rviz2 exit code -11`이 있습니다. 정확한 근본 원인은 현재 증거만으로 확정할 수 없습니다. `summary.json`에서 모든 3-leg 결과와 수집이 끝나 정상 종료 코드 0이었고 GUI는 `true`로 요청됐으므로 **이 종료 경고를 선행 주행 실패로 뒤바꾸지 않습니다.** 반대로 GUI 프로세스가 모든 시간대에 안정적이었다고 추가로 단정하지도 않습니다. 사용자 시각 검수는 별도이며 자동 인수 Gate가 아닙니다.

이상 징후의 향후 재발은 `docs/reports/issues/`에서 원인·재현 경계를 좁혀 진단하되, 현재 기능이 성공했으므로 중복 실주행으로 MVP 일정을 소모하지 않습니다.

## 3. 교육용 요구사항 추적성

| 요구사항 | 원본 필드/로그 | 판정 |
|---|---|---|
| A-TTY-01 운영자 승인 뒤 Goal | `tty_policy`, Adapter `OPERATOR_APPROVED` | PASS |
| A-MAP-01 검증된 T03/RETURN/HOME | `poses`, `map_pgm_sha256`, map TF | PASS |
| A-NAV-01 실제 Nav2 3연속 | `nav_results` 3건, 동일 request_id | PASS |
| A-SNS-01 실제 물리 이동·감지 | `odom_count`, `odom_max_m`, `scan_count` | PASS |
| A-AMCL-01 목표 도달 위치 | `amcl_error_m` 0.186/0.134/0.175m | PASS |
| D-M1~D-M6 UI·대기·COMPLETED | 원본에 D Manager/UI 기록 없음 | NOT_RUN |
| C-REAL-01 실데이터 AI 추론 | 원본에 학습/실추론 증거 없음 | NOT_RUN |

## 4. 후속 작업(현재 A 경계)

1. A-10 GUI 기본값 변경 후 **ROS 없는 정적/실행기 인자 L0**만 실행, Nav2/Map/Goal 코드는 그대로 보존.
2. D PR #38의 오래된 `DISH_RETURN=null` 선행 의존 문구를 E 통합 시 정정: 실제 A-06 좌표와 본 L3 증거로 해소.
3. A+D 서비스 AI OFF 통합, Manager가 동일 요청 ID의 세 구간 결과를 실제로 소비하고 10초/5초 뒤 UI COMPLETED를 표시하는지 확인.
4. B/C는 실제 물리 이미지·라벨·학습 모델이 준비되기 전까지 OPTIONAL로 유지.
