# SMARTDISH-A-06 — 검증된 DISH_RETURN 좌표 운영 설정 승격

- 날짜: 2026-11-23 KST
- 상태: **PASS — 운영 YAML 승격 후 동일 SHA 실제 Gazebo/Nav2 3-leg L2 재검 완료**
- 이전 L2 성공 소스: `6d7e3508ea1f4a5d32ab257904b2335f859b3f0b`
- 근거: [실제 Gazebo Actions #45124877004](https://github.com/silverbjin/samsung_AXI/actions/runs/45124877004), `SMARTDISH_A_REAL_GAZEBO_3LEG_L2_PASS`
- 목표: A 코드 변경이 아닌 **검증된 map 목적지 좌표만 생산 설정에 반영**

## 1. 왜 이 변경이 필요한가?

A-01에서는 위치가 미확정이어서 `DISH_RETURN`을 `null`로 두고 잘못된 Goal을 차단했습니다. A-04에서 원본 S2-MAP-03 waypoint를 추적하고 정적 map free-space를 확인했습니다. A-05에서 신규 위치까지 실제 Nav2 SUCCEEDED + /odom·AMCL로 확인한 후, 더 이상 `null`을 유지할 이유가 없으므로 운영 좌표로 승격합니다.

## 2. 변경

- `src/smartdish_robot/config/table_poses.yaml`: `DISH_RETURN: {x:-1.15,y:1.60,yaw:-1.57079632679}`.
- `tests/test_smartdish_a_contract.py`: 실제 확정 값 및 `null` 방어 테스트를 분리하여 원래 안전 원칙 보존.
- `tests/test_smartdish_a_return_candidate.py`: 운영 값과 L2 검증 후보가 완전히 동일한지 회귀 검사.
- `.github/workflows/smartdish-a-gazebo-l2.yml`: 새 실제 시뮬레이션 CI는 이제 **운영 YAML 자체를 입력**으로 사용하여 소스·설정 일치 확인.
- `A_HANDOFF.md`: D/E 연동용 확정 좌표·실행 명령·기존 PICKUP_RETURN과의 차이 기록.

## 3. 검증 근거 (source SHA 및 역할 구분)

| 구간 | Nav2 | /odom 최대 변위 | AMCL 오차 |
|---|---|---:|---:|
| HOME→T03 | SUCCEEDED | 5.181m | 0.098m |
| T03→DISH_RETURN | SUCCEEDED | 6.459m | 0.196m |
| DISH_RETURN→HOME | SUCCEEDED | 1.940m | 0.166m |

동일 `request_id=SMARTDISH-A-CI-L2-001`. 결과는 실제 Gazebo + 공식 Nav2/AMCL + 원본 LiDAR/odom + 신규 NavigationAdapter 토픽의 측정입니다. 증거를 가공하여 PASS를 만들지 않았습니다.

## 4. 운영 YAML 재검 결과·잔여 범위

- [ROS Jazzy L0/L1 #45125551813](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551813) PASS (운영 SHA `5b063a0`).
- [실제 Gazebo L2 #45125551884](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884): 정적 지도/TTY **6 PASS**, 운영 YAML 경로로 실제 Nav2 `SUCCEEDED` 3건, 실제 odom 5.148/6.462/1.958m, AMCL 도착 오차 0.189/0.142/0.235m. 실물 로그 [Artifact #14795667913](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884/artifacts/14795667913).
- 두 실제 L2 Run은 후보 파일 사용 R03 `6d7e350`과 운영 파일 R04 `5b063a0`를 구분해 기록했습니다. 후자는 **최종 운영 설정 출고 근거**입니다.
- 본 변경은 기존 S7 `restaurant.sdf`/Map/Nav2/Collision Monitor를 수정하지 않았습니다. 새로운 planner나 복잡한 센서 안전 게이트도 추가하지 않았습니다.
- 아직 검증하지 않은 것: D Mission Manager의 UI 타이머(10초/5초), `COMPLETED`, AI ON 카메라/추론.
- 주니어 교육 핵심: '후보 좌표 → 실제 주행 증거 → 운영 설정'의 3단계는 성능 최적화가 아니라 **추적 가능한 변경 승인**입니다.

## 5. 훈련생용 근거 추적표

| 요구사항 ID | 소스·검증 | 실제 인수 증거 | 판정 |
|---|---|---|---|
| A-COORD-01 | `return_pose_candidate.yaml` → `table_poses.yaml` | S2-MAP-03 World waypoint #5 및 R04 실제 Goal | PASS |
| A-NAV-01 | `navigation_adapter.py` `goToPose/getResult` | R04 `SUCCEEDED` 3개 | PASS (L2) |
| A-EVD-01 | R04 `l2_evidence.json` | /odom·/scan 3구간, AMCL 오차 | PASS (L2) |
| A-SAFE-01 | `tty_approval.py`, 기존 Collision Monitor 재사용 | TTY 승인 후 Goal, 안전 소스 변경 없음 | 보호 동작 관측 / STOP 별도 신규 재검 없음 |
| D-INTEG-01 | Mission Manager 타이머/UI | **이번 A 단독 CI에 포함되지 않음** | NOT_RUN |

L0/L1/L2 범위를 상향 승격하거나 기존 S7의 현장 WSL2 L3 성과를 신규 SmartDish 현장 인수로 복제하지 않습니다.
