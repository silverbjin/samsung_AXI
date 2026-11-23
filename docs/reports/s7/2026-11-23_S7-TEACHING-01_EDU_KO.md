# S7-TEACHING-01 — 강사·학생 통합 실습 패키지 교육용 개발 보고서

## 목적과 배경
학생은 파이썬/AI 기초가 있지만 ROS 2 로봇 하드웨어 지식이 부족합니다. 이미 성공한 S6의 Nav2/CM/요청형 이미지 소스를 최대한 재사용하면서, S7의 **시작부터 접시가 있는 세계**와 **빈 테이블 복귀 금지**를 한 수업의 사건 순서로 이해하도록 설계했습니다.

## RED(교육 이슈)
- 개발 코드는 있지만 학생이 월드 모델 생성, 첫 Nav2 Goal, Odom 실제 정지, RGB ROI/이미지, 비전 결과, 복귀 허가, LiDAR STOP을 한 장면으로 연결하기 어려웠습니다.
- 로그의 특정 PASS 문자열만 외우면 실제 RGB SHA나 Action status가 누락돼도 합격으로 오판할 수 있었습니다.
- 초기 SHA/G06/G09 이력 때문에 실행기 SHA와 런타임 SHA가 섞일 위험이 있어 S7은 하나의 불변 SOURCE_SHA로 동일 코드·실행기 파일을 받아야 합니다.

## GREEN(실제 작성한 파일)
| 구분 | 파일 | 핵심 내용 |
|---|---|---|
| 강사용 | docs/s7/INSTRUCTOR_DEMO_GUIDE_KO.md | 배경/주제/데이터 파이프라인, 라이브 양성·빈 테이블 음성 시연, 역할별 점검, 교육 질문 |
| 학생용 | docs/s7/STUDENT_LAB_GUIDE_KO.md | 리포지토리 clone, SDF 생성, 코드 추적, 이미지와 Nav2 결과 분석, STOP과 미발행 Goal 확인 |
| 강사용 솔루션 | docs/s7/INSTRUCTOR_SOLUTIONS_KO.md | 원본 PPM raw RGB SHA와 JSON 비교, 상태 결과의 인과 해설, 오판 방지, 평가표 |
| 학생 TODO | education/s7/student/s7_evidence_todo.py | 미완성 TODO가 임의 PASS를 출력하지 않는 fail-closed 스켈레톤 |
| 강사 정답 코드 | education/s7/instructor/s7_evidence_solution.py | 실제 Action/이미지/STOP 원본 증거 읽기 전용 검사기 |
| 회귀 | tests/test_s7_teaching.py | 잘못된 Goal/이미지/STOP/월드 조건에 대한 L0 교재 코드 테스트 |

## 코드·아키텍처와 교육용 순서
`S7 generated world SDF (stacked|empty)` → `Gazebo startup` → `NavigateToPose TABLE_3` → `Odom settle` → `fresh RGB` → `AI STACKED/NOT_STACKED/UNKNOWN` → `Return or HOLD` → `Collision Monitor STOP`.  강사 정답 코드는 실제 ROS/Goal을 실행하지 않고 파일만 분석합니다.

## 예상 결과 vs 검증 범위
- L0: 제출된 증거 파일의 SDF/Action/RGB 해시/STOP 계약을 검사하는 테스트, 학생 TODO fail closed. 실제 Gazebo 데이터를 만드는 검증이 아닙니다.
- L2: 별도 S7 실제 Gazebo workflow의 positive+negative가 완료되어야 PASS.
- L3: 강사 WSL2의 불변 SHA 동작과 사용자 TTY 확인 후 실증. GUI 육안 검수는 사용자 전담/자동 게이트 제외.
- 성능 RTF 90% 목표 및 범용 식기 ML 성능은 HOLD.

## 학습·평가 질문
1. ROS 2 Action SUCCEEDED 후 실제 정지를 별도로 검증하는 이유는?
2. Gazebo 초기 World model vs 목표 도착 후 ros_gz_sim create의 운영 차이는?
3. 왜 빈 테이블 HOLD는 첫 Action 성공과 둘째 Goal 미발행을 동시에 보여야 하나요?
4. PPM 파일 해시 전체와 ROS 원본 RGB 바이트 해시의 차이는?
5. CI L0 PASS를 실제 Gazebo L2 PASS라고 부르면 어떤 검수 오류가 생기나요?

## 보고서·GitHub 판정
본 개발 단위는 별도 교육용 브랜치의 코드/문서로 보존하며, 정적 CI를 확인한 후 S7 기능 브랜치에 통합합니다. 기존 성공 S6 안전 원본은 변경하지 않습니다. 현재 실물 L2/L3 판정은 별도 증거가 필요합니다.
