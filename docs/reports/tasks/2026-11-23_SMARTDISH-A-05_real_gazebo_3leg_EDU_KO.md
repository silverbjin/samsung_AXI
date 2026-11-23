# SMARTDISH-A-05 — Gazebo 실제 3구간 Nav2/odom 교육용 인수 보고서

- 날짜: 2026-11-23 KST
- 현재 상태: **CI 실행 결과 미확인 (NOT_RUN)**. 완료 신호 없이 PASS라고 하지 않음.
- 기준 S7 main: `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`
- A 후보: `map (-1.15,1.60,-1.57079632679)`, S2-MAP-03 실제 World surveyed waypoint #5
- A 개발 브랜치: `feat/smartdish-a-robot`

## 1. 아키텍처와 재사용 판단

```text
GitHub CI isolated Gazebo Waffle Pi + existing Map/AMCL/Nav2/Collision Monitor
    → actual A NavigationAdapter started with ROS 2 Jazzy
    ← /collection/nav_goal JSON (one request_id, three legs)
    → official Nav2 NavigateToPose + actual odom + AMCL pose + scan
    → /collection/nav_result JSON x3
    → l2_evidence.json with exact SHA and real observation
```

S7의 World, original scan bridge, Nav2 and CM은 **변경하지 않았습니다.** 목표 장소의 정확도를 임의 성능 수치로 증명하지 않고, 세 번의 Action 완료와 물리 /odom 이동을 동일 request_id에 묶어 확인합니다.

## 2. 명시적 CI와 현장 TTY 분리

`smartdish_a_real_gazebo_l2.py`는 GitHub CI, 비-WSL2, 고유 GZ_PARTITION, ROS_DOMAIN_ID를 모두 요구합니다. CI의 시뮬레이션 환경에서만 기존 S7 CI와 유사한 **프롬프트 관측 후 10초 지연 pseudo-TTY 승인**을 사용합니다. 실제 운영자의 `ros2 run ... goals_enabled:=true`는 여전히 **직접 TTY 수동 승인**이 필요합니다.

## 3. RED→GREEN 및 증거

- A-04 L0: S2 실 방문 waypoint → map 변환 → PGM known free / clearance / 3 지점 연결
- A-05 L2: 실제 ROS 2 Nav2 Action / 3개의 독립 구간 / 각 /odom 이동 / 실제 AMCL / LiDAR
- RED: 잘못된 좌표, Map/TF 이상, Goal 실패, 결과 누락, 실제 Odom 정지라면 해당 경계에서 종료하고 첫 실패 기록
- GREEN 기대: `SMARTDISH_A_REAL_GAZEBO_3LEG_L2_PASS`

## 4. 실행 근거 및 남은 작업

CI workflow: `.github/workflows/smartdish-a-gazebo-l2.yml`

```bash
python3 -m pytest -q tests/test_smartdish_a_return_candidate.py
# Gazebo CI에서만 실행되는 실제 L2 파일: scripts/smartdish_a_real_gazebo_l2.py
```

Actions URL, 최초 RED, 원인·수정 및 마지막 L2 판정은 실제 CI 로그를 확인한 후 기록합니다. L2 성공하기 전 운영 `table_poses.yaml`의 DISH_RETURN은 **null 유지**. D UI/Manager `COMPLETED`는 A 단독 시연으로 PASS 처리하지 않습니다.
