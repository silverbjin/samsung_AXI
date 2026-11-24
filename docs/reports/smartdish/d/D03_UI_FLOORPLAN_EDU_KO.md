# D03 — 평면도 Tkinter UI 개발·시험 교육 보고서

## 1. 요구사항 → 코드 대응
| 요구사항 | 실제 코드 | 근거 |
|---|---|---|
| T01~T06 도면 표시 | \`ui_app.py:_draw_map\` + \`config/ui_layout.yaml\` | 픽셀 프레임 6개 사각 테이블 |
| T03만 활성 | \`select_t03\` + \`read_layout\` | 오동작 방지 |
| 대기시간 10/5 기본 | \`table_wait\`/\`dropoff_wait\` | 1~120/1~60 입력 방어 |
| AI OFF 기본 | \`ai_var=false\` + 비활성 토글 | C 모델 없어도 서비스 가능 |
| 동적 UI 상태 | \`on_status\` | 같은 요청 ID의 수신 상태만 반영 |
| UI 미정지 | \`root.after(60, poll_ros)\` | Tk 이벤트 루프와 rclpy spin_once 교대 |
| 직원 확인 | \`confirm\` | NEEDS_CONFIRMATION에서만 실제 버튼 표시 |

## 2. 좌표를 섞지 않아야 하는 이유
\`ui_layout.yaml\`의 \`frame:ui_pixels\`는 Canvas에 사각형을 그리기 위한 값입니다. 3개 Nav2 목표의 \`map\` Pose는 A가 소유하는 **별도 \`table_poses.yaml\`**의 진입 가능한 실제 지점입니다. UI에서 T03을 눌러 보내는 것은 \`table_id=T03\`뿐이며 그림 픽셀을 미터로 바꾸지 않습니다.

## 3. 실습 순서
1. \`ros2 launch smartdish_service smartdish_service.launch.py ai_available:=false\` 실행.
2. T03 버튼만 클릭 가능함을 확인하고 대기시간을 10초/5초로 둡니다.
3. A Navigation Adapter가 실행돼 \`/collection/nav_goal\`을 구독하는지 확인합니다.
4. 회수 시작 후 \`/collection/request\` JSON과 \`/collection/status\`를 기록합니다.
5. 실제 주행 검증은 A와 E 통합에서 3개 Nav2 SUCCEEDED 및 odom을 함께 확보합니다.
6. AI 옵션 미준비면 회색 \`AI 검사 OFF (준비 중)\` 상태를 유지합니다.

## 4. 검증 범위
L0: \`tests/test_smartdish_d_ui.py\`는 YAML frame/활성 테이블/상태 이름과 Pose 혼입 금지를 검사합니다. **GUI 렌더링 육안검수, ROS 그래프, 실제 Gazebo 이동은 포함하지 않습니다**. GUI 시각 검수는 사용자 책임이며 자동 게이트로 취급하지 않습니다.

## 5. 초심자 디버깅 과제
- 버튼 클릭이 안 될 때: \`canvas.tag_bind\`가 T03 사각형과 글자에 모두 연결돼 있는지 확인합니다.
- 클릭은 되는데 요청이 없을 때: Manager subscriber 발견 여부를 확인합니다.
- 요청은 있는데 UI가 움직이지 않을 때: \`/collection/status\`, \`request_id\` 필터, tkinter \`after()\` 폴링 주기를 확인합니다.
- 이동은 됐지만 대기가 없을 때: A \`nav_result\`의 \`leg\`와 \`request_id\`를 원본 JSON으로 비교합니다.
