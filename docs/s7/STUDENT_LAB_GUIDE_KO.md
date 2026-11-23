# S7 — 초심자 학생 실습 가이드: 식기가 먼저 놓인 레스토랑

> ROS 2 Jazzy / Gazebo Harmonic / WSL2 Ubuntu 24.04. S7 기능 최종 L3 인수 전까지는 개발 중 자료이며, 영상 육안 검수는 강사가 수행합니다.

## 학습 목표
1. Gazebo World 파일에 처음부터 존재하는 접시와, Goal 도착 후 생성하던 기존 S6 접시의 차이를 설명합니다.
2. ROS 2 /scan, /odom, /restaurant/rgbd/image, Nav2 Action, Vision 모델, Collision Monitor의 데이터 흐름을 설명합니다.
3. 접시가 있는 경우에만 복귀하며 빈 테이블에서는 복귀 Goal이 발행되지 않음을 증거로 판단합니다.
4. 코드 출력 문자열이 아니라 Action 결과, RGB PPM SHA256 및 cmd_vel/Odom 정지를 실제 증거로 사용합니다.

## 실습 1. GitHub 준비 — 반드시 Ubuntu 터미널에서 실행
    git clone https://github.com/silverbjin/samsung_AXI.git
    cd samsung_AXI
    git fetch origin feature/s7-startup-dishes-negative-teaching-20261123
    git switch --detach origin/feature/s7-startup-dishes-negative-teaching-20261123
    git rev-parse HEAD
    python3 --version
    source /opt/ros/jazzy/setup.bash
    ros2 --help >/dev/null
    gz sim --version

개발 브랜치 HEAD는 바뀔 수 있습니다. 강사 실제 인수는 최종 CI에서 PASS가 확인된 고정 40자리 SHA를 사용해야 합니다.

## 실습 2. ROS를 실행하지 않고 S7 월드 파일 생성
    mkdir -p generated/s7
    python3 scripts/s7_scene.py --source src/restaurant_world/worlds/restaurant.sdf --out generated/s7/restaurant_stacked.sdf --scenario stacked
    python3 scripts/s7_scene.py --source src/restaurant_world/worlds/restaurant.sdf --out generated/s7/restaurant_empty.sdf --scenario empty
    grep -n s6_stacked_dishes generated/s7/restaurant_stacked.sdf
    grep -n s6_stacked_dishes generated/s7/restaurant_empty.sdf || true
    python3 -m pytest -q tests/test_s7_scene.py

예상: stacked에는 정적 식기 모델 정확히 한 개, empty에는 식기 모델이 없습니다. 원래 restaurant.sdf 및 저장된 S5 지도는 바뀌지 않습니다. 생성된 manifest.json에서 SHA256을 확인하십시오.

## 실습 3. 코드에서 구조 추적
| 파일 | 볼 항목 | 학생 설명 과제 |
|---|---|---|
| scripts/s7_scene.py | build_world, validate_world | S5 원본 월드 보호 이유 |
| src/restaurant_bringup/launch/world.launch.py | world_file | Gazebo 최초 월드 로딩 시점 |
| scripts/ci_s3_amcl_smoke.py | s7_scenario, TABLE_3 | 첫 Goal과 식기 로딩의 순서 |
| scripts/s6_camera_gate.py | odom settle, 이미지 임시 구독 | 주행 중 이미지 AI 미사용 이유 |
| scripts/s6_vision_ai.py | infer, accept_return | STACKED만 복귀 가능한 이유 |
| scripts/s7_negative_contract.py | validate | 빈 테이블 no-return 증거 |

주의: lazy ROS 이미지 브리지는 Gazebo RGBD 물리적 센서 OFF와 같은 말이 아닙니다. RTF 90%는 이번 MVP에서 HOLD입니다.

## 실습 4. 강사 시연 관측
최종 S7 L2 CI에 성공한 뒤 강사가 전달한 S7 공식 SHA 단일 실행 블록을 사용합니다. 이 도중 인수자의 실물 TTY 입력 YES-S5-LIVE-GOALS 전에는 주행 Goal이 발행되면 안 됩니다.

관측 순서: S7 world startup 접시 존재 → TABLE_3 Action SUCCEEDED → Odom 정지 → 실제 RGB 2~3 프레임 → AI STACKED → PICKUP_RETURN Action SUCCEEDED → LiDAR Collision Monitor STOP → 출력 속도와 Odom 0. 육안 장면 확인은 강사 담당이며 자동 합격과 별개입니다.

## 실습 5. 학생 TODO로 증거 분석
    python3 education/s7/student/s7_evidence_todo.py --help
    python3 education/s7/student/s7_evidence_todo.py --evidence generated/s6/real_vision_evidence.json --ppm generated/s6/s6_table_rgb.ppm

여기서 직접 구현할 TODO는 원본 PPM SHA256 대조, TABLE_3과 PICKUP_RETURN Action 순서, 도착 이후 이미지 획득, Vision 승인, 실제 LiDAR STOP, cmd_vel/Odom 0 검증입니다. 미완성 스켈레톤은 PASS를 출력하지 않습니다.

## 실습 6. 빈 테이블의 안전 차단
S7 실제 Gazebo CI는 별도 empty 월드를 시작하고 TABLE_3 첫 Goal이 성공한 뒤 RGB를 관찰합니다. 예측이 NOT_STACKED/UNKNOWN이면 PICKUP_RETURN Goal이 없어야 합니다. 원래 로봇 실행기가 기대한 Vision HOLD 예외로 비영 종료하더라도 첫 성공 Action, 실제 RGB, 후속 Goal 미발행이 모두 입증될 때만 안전 차단 시험 PASS입니다.

## 제출물
- 정확한 Git SHA, CI 링크 및 World manifest SHA.
- 시작 식기 모델 수 1개와 0개 비교.
- TABLE_3과 PICKUP_RETURN Action status 4, 이동 거리, 정지 증거.
- RGB 원본 해시와 JSON 증거의 일치 여부.
- 빈 테이블 Goal 1개, 안전 HOLD 및 복귀 Goal 0개를 증명한 기록.
- 한 가지 실패·원인 후보·반증·GREEN 증거·PASS/HOLD/NOT_RUN을 포함한 짧은 보고서.

금지: 가짜 RGB와 모의 Action을 실제 Gazebo 인수로 제출하거나 Collision Monitor를 끄고 성공으로 취급하는 행위.
