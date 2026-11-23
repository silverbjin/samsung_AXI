# SmartDish S6 기능 릴리스 이후 작업 계획 (2026-11-23)

## 완료·고정 기준
S6 최종 기능 런타임 SHA 9d402a991d1ee0a1c46027abe91a55266b69d9bd. 공식 ROS Jazzy/Gazebo Harmonic L2와 강사 WSL2 L3에서 TABLE_3 배달→실제 정지→RGB 3프레임→고정 fixture STACKED→복귀→LiDAR CM STOP 확인. 정확한 SHA와 보고서는 G11에 기록했습니다.

GUI 육안 검수는 사용자가 직접 수행하며 자동 L3/병합 게이트에서 제외. 기술적 GUI/종료 경고는 백로그로 보존합니다. 실제 Goal 승인용 TTY 확인은 안전 기능이므로 계속 필수입니다.

## P0 — 다음 MVP 개발 단위
**S7-DISH-STARTUP-01: 접시의 시작 시점 배치.** 지금은 TABLE_3 Action 성공 뒤 s6_camera_gate.py가 Gazebo에 접시 3단 fixture를 동적 생성하므로 실행 초기의 테이블에 접시가 없는 것이 정상입니다. 교육·서비스 시나리오에서는 테이블에 접시가 이미 있어야 합니다. 기존 레스토랑 world와 S6 성공 소스를 보존하면서 S7 opt-in 시작 fixture를 제공하고, 첫 화면에서 접시가 존재함을 확인(사용자 눈 확인은 비차단), 실제 RGB/STACKED/2 Action/STOP 증거를 기능 게이트로 검수하십시오. 기존 지도·Collision Monitor·속도 변경 금지.

**S7-VISION-NEGATIVE-01: 빈 테이블 반례.** 식기 없음·이미지 없음·가림의 대표 입력 1~2개에서 NOT_STACKED/UNKNOWN과 자동 복귀 Goal 미발행을 검증합니다. 현재 프로토타입은 고정 Gazebo 시점으로 학습되었으므로 일반 물체 인식 정확도를 주장하지 않습니다.

**S7-TEACHING-01: 초심자 강사/학생 시연 가이드.** 리포지토리 clone부터 ONE-SHOT, ROS 2 Action/Topic·PPM 이미지·AI 판정·STOP evidence 연결, 학생 TODO/강사 해설을 제작합니다. 개발 단위마다 RED→GREEN→REFACTOR→REVIEW→COMMIT 교육용 보고서를 함께 올립니다.

## P1 — 별도 비차단 안정화
- S5-GUI-RENDER: RViz GLSL indexed_8bit_image shader error, 기존 Gazebo/Qt/OpenGL 진단과 분리. 사용자의 육안 검수는 자동 게이트가 아닙니다.
- S5-SHUTDOWN: Ctrl+C 중 RViz 'terminate called without an active exception' 및 RUN_RC=130, 실제 종료 시 프로세스 로그 정리. 해당 오류를 S6 기능 성공 증거로 지우거나 재분류하지 않습니다.
- S6-RGB-IDLE: 현재 lazy ROS 브리지는 Nav2 주행 시 Vision의 일시적인 이미지 구독만 확인; Gazebo renderer가 실제 OFF인지 미검증. 성능 관련 개발은 사용자 HOLD 유지.

## P2 — 확장 과제 (현재 인수 범위 밖)
- AI 데이터 수집/전처리·서로 다른 조명/카메라 각도/식기 종류·train/val/test 분리와 일반화 평가.
- 실제 인식 추론 결과 UI 및 교육 시각 자료 확장(사용자 시각검수 담당).
- RTF>=0.90 목표는 HOLD. 최신 WSL2 moving RTF 중앙값 0.4975이며 성능 목표 달성으로 보고하지 않습니다.

## 검증·GitHub 규칙
이번 G11의 SHA와 원본 기능 성공 증거 보존. 새 기능은 별도 브랜치에서 구현하고 변경 경계에 해당하는 실제 Gazebo 검증만 추가합니다. 기능 인수(GitHub L2 + 강사 WSL2 L3)와 사용자 전담 GUI 육안 검수는 독립 판정합니다.
