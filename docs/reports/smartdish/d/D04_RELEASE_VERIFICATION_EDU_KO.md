# D04 — D 서비스 출고 검증·교육용 최종 보고서

- 기준일: 2026-11-23
- S7 main 원점: \`2dd7f968dd3d24e2afb48e0917ef8c9d054ac894\`
- D 기능 최종 수정 SHA: \`b3e9bfdb80b96607faf5f5f121429370f36ec1d6\`
- Draft PR: https://github.com/silverbjin/samsung_AXI/pull/38
- 범위: D 단독 Python 계약 + ROS Jazzy 패키지 빌드, **신규 Gazebo L2/L3 미실행**

## 1. 개발·검증 타임라인
| 단계 | 실제 커밋 | 증거와 판정 |
|---|---|---|
| S7 기준선 | 2dd7f968 | 기존 S7 L3/Gazebo 별도 PASS. 신규 D 아님 |
| D01 FSM + pytest | 22a78f6d | 개발 코드와 교육 보고서 커밋 |
| D02 ROS 통신 | e8b559be | JSON fixture·ament·교육 보고서 커밋 |
| D03 GUI + CI | f6aaecbe | Actions #45121462007 L0 **24 PASS**, Jazzy L1 **PASS** |
| D-DBG-001 | b3e9bfdb | request ID 스키마·AI 필수필드 정렬 |
| D-DBG 재검 | b3e9bfdb | Actions #45121672872 L0 **26 PASS**. 동일 run의 L1 판정은 PR 최신 상태 확인 |

## 2. 검증 실행과 명령
- [D03 소스 기준 공개 GitHub Actions #45121462007](https://github.com/silverbjin/samsung_AXI/actions/runs/45121462007): L0 Python 24 PASS, Jazzy L1 성공.
- [D-DBG 수정 후 공개 GitHub Actions #45121672872](https://github.com/silverbjin/samsung_AXI/actions/runs/45121672872): L0 Python 26 PASS; ROS L1 최종 상태는 Actions 원본 참조.
- L0 명령: \`python3 -m compileall -q src/smartdish_service tests/test_smartdish_d_service.py tests/test_smartdish_d_ui.py\` 및 \`python3 -m pytest -q tests/test_smartdish_d_service.py tests/test_smartdish_d_ui.py tests/test_s7_scene.py tests/test_s7_negative.py\`.
- L1 명령: ROS Jazzy 환경 \`colcon build --packages-select smartdish_service --symlink-install\` 후 \`ros2 pkg executables smartdish_service\`, Python 모듈 import 검사.

## 3. 테스트 수준과 오해 방지
| 수준 | 의미 | 결과 |
|---|---|---|
| D L0 | FSM에 모의 nav_result를 넣어 조건·대기시간 검증 | PASS, **MOCK_ONLY** |
| D L1 | ROS 패키지 설치·Python import/엔트리포인트 | 첫 CI PASS, 수정 후 CI 확인 |
| E/A L2 | 실제 Gazebo 3-leg, Nav2 SUCCEEDED, odom | NOT_RUN |
| WSL2 L3 | 사용자 환경 UI+Gazebo 시연 및 원본 증거 | NOT_RUN |

ROS 2 패키지 성공만으로 pub/sub 실제 전달과 실제 주행 성공을 입증하지는 않습니다. GUI는 구현됐지만 WSLg 스크린샷이나 렌더링 성공 증거는 없습니다. 시각적 검수는 사용자 담당으로 자동 게이트에서 제외했습니다.

## 4. 변경 영향 검토
- 원본 \`src/restaurant_world/**\`, \`src/restaurant_delivery/**\`, \`src/restaurant_bringup/**\`, \`scripts/s7*\`, \`tests/test_s7*\` 변경 없음.
- A/B/C 브랜치 소스 수정 없음. 계약명·QoS 변경 없음.
- A의 \`DISH_RETURN\` null은 사용자 실환경에서 지도 확인 없이 추정하지 않았습니다.
- 신규 주행 성공을 꾸미는 \`nav_result\` 시뮬레이터를 서비스 코드에 넣지 않았습니다.

## 5. 요구사항 대비 부족한 증거와 통합 체크리스트
1. A가 \`DISH_RETURN\` map Pose 값을 실제 주행 가능 지점으로 확정하고 YAML SHA를 인계.
2. E는 A의 TTY 승인·READY 후 D UI에서 T03 클릭, 동일 request_id Goal 3개 발행·결과 수신 확인.
3. 각 A SUCCEEDED의 실제 /odom 이동, D의 10/5초 monotonic 타이머, UI COMPLETED를 한 묶음으로 확보.
4. C 준비 전에는 AI OFF 유지. 실물 사진 없이 AI STABLE을 만들어 성공 주장 금지.
5. 실제 실패 발생 시 독립 D-DBG 후속 보고서 추가하고 실행 SHA·수정 전후 CI 링크 제시.

## 6. 학생을 위한 분석 질문
- 26개의 PASS가 실제 서비스 완주를 의미하지 않는 이유는 무엇인가요?
- 왜 로봇 전용 \`table_poses.yaml\`을 D GUI 좌표로 대체하면 안 되나요?
- \`D-DBG-001\`을 통합 후 발견했다면 어떤 문제가 생기며, 사전 계약 검사가 절약한 비용은 무엇인가요?
- E 단계에서 \`request_id\` 하나로 로그를 묶으면 디버깅이 쉬워지는 이유는 무엇인가요?
