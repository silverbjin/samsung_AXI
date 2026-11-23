# S7 — 강사용 정답 코드·검증 가이드

> 본 문서는 학생 TODO의 정답을 공개하는 강사용 자료입니다. ROS 실제 주행 없이 파일만 읽는 검사기이며 테스트의 PASS는 **증거 파일 형식의 합격**을 뜻합니다. CI L2/L3 자체의 PASS를 대체하지 않습니다.

## 1. 원본 확인과 실행

기준 파일은 실제 S7 stacked 시나리오에서 출력한 generated/s6/real_vision_evidence.json 및 generated/s6/s6_table_rgb.ppm입니다.

    python3 education/s7/instructor/s7_evidence_solution.py \
      --evidence generated/s6/real_vision_evidence.json \
      --ppm generated/s6/s6_table_rgb.ppm

강사 정답이 수행하는 검사는 S7 world 시작 식기 여부, TABLE_3와 PICKUP_RETURN Action 상태 4, Vision STACKED·신뢰도·fresh frame, RGB PPM raw payload SHA256, 안전 CM downstream 속도·물리 Odom 정지, S6 통합 플래그입니다. 가짜 또는 부정확한 증거는 ValueError로 종료합니다.

## 2. 강사 정답과 학생 TODO 매칭
| 학생 TODO | 강사 정답 위치 | 확인 목적 |
|---|---|---|
| 월드가 startup stacked인지 | evaluate / s7_scene 검사 | 접시가 시뮬레이션 시작부터 있어야 함 |
| Nav2 Goal 2개 SUCCEEDED | evaluate / real_nav_legs | 문자열 한 줄이 아닌 Action 결과 |
| RGB가 실제 도착 뒤 받은 것인지 | evaluate / s6_vision.image | 이전 프레임·임의 이미지를 오인하지 않음 |
| 이미지 무결성 | ppm_rgb + SHA256 | P6 헤더 제외 raw RGB payload 320×240×3 |
| Vision STACKED에서만 복귀 | evaluate / prediction + s6_return_goal_sent | NOT_STACKED/UNKNOWN은 HOLD |
| Collision Monitor STOP | evaluate / s4_safety_stop | 최종 필터 cmd_vel와 Odom 정지 |

## 3. 왜 PPM 전체 파일 해시가 아닌 raw 데이터인가?
P6 PPM 헤더에는 형식·가로·세로·최대 채널값(255)이 포함됩니다. ROS Image의 원본 SHA와 비교해야 할 대상은 **헤더를 제외한 RGB 바이트**입니다. 위 정답은 첫 세 개의 줄만 헤더로 보고 나머지 픽셀 바이트 길이 = width×height×3을 검사합니다. BGR8→RGB8 변환은 원본 S6 저장 코드가 이미 수행합니다.

## 4. 음성 테스트 정답 해설
S7 빈 테이블의 올바른 출력은 복귀 Action이 없고, Vision NOT_STACKED 또는 UNKNOWN이어서 안전 차단된 것입니다. `scripts/s7_negative_contract.py`는 실제 빈 테이블의 evidence와 RGB PPM·원본 console log를 대조합니다.

    PYTHONPATH=scripts python3 scripts/s7_negative_contract.py \
       --evidence generated/s7/empty_vision_evidence.json \
       --ppm generated/s7/s6_table_rgb.ppm \
       --log logs/s7_empty_console.log

이 코드는 단독으로 Gazebo를 실행하지 않습니다. PPM이나 첫 Action이 없으면 PASS를 출력하지 않습니다. 시각적 화면 평가는 강사의 별도 과제이고 자동 게이트가 아닙니다.

## 5. 권장 3단계 데모

**첫 번째 질문**: “접시는 언제 생깁니까?” 원본 S6은 Goal 도착 후 생성, S7은 world 로딩 순간 정적 객체로 생성됩니다.

**두 번째 질문**: “로봇이 도착했으면 사진을 바로 찍어도 됩니까?” 아닙니다. Nav2 Action SUCCEEDED 후에도 물리 Odom 정지 유지를 별도로 확인해야 합니다.

**세 번째 질문**: “AI 판단이 UNKNOWN인 경우는?” HOLD이며 자동 PICKUP_RETURN Goal을 보내면 안 됩니다.

## 6. 평가 기준 및 오판 방지
- 학생이 데이터를 조작해 예상 숫자를 넣었을 경우 검증 파일을 사용하되 실제 CI 원본이 아니므로 L2 PASS라고 채점하지 않습니다.
- 단위 테스트의 가상 증거와 실제 Gazebo artifact의 증거 등급을 명확히 구별합니다.
- Goal/Tty 승인, LiDAR CM 안전, map/AMCL을 학생 실습에서 우회하지 않습니다.
- 성능 RTF 90%는 HOLD, Vision 범용 정확도도 미검증입니다.

## 7. 학습 결과와 반복 개발 보고서
각 개발 단위는 RED 증상·입력 조건·원인 가설·수정한 코드·GREEN 실제 로그·차이·회고·초심자 질문·Git SHA·CI 링크·PASS/HOLD를 기록합니다. G11 S6 기준 성공 증거와 새 S7 성공/실패 증거를 구분해 보존합니다.
