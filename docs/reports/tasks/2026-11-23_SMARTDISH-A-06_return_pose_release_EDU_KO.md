# SMARTDISH-A-06 — 검증된 DISH_RETURN 좌표 운영 설정 승격

- 날짜: 2026-11-23 KST
- 상태: **A 로봇 단독 L2 증거 확인 후 운영 YAML 승격 / 최종 출고 SHA CI 추가 확인**
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

## 4. 후속 재검·위험

- 최종 운영 YAML에 대한 A L0 및 ROS L1 CI를 실행하고, CI L2가 다시 수행된다면 새 SHA/Action 결과를 따로 기록합니다.
- 본 변경은 기존 S7 `restaurant.sdf`/Map/Nav2/Collision Monitor를 수정하지 않았습니다. 새로운 planner나 복잡한 센서 안전 게이트도 추가하지 않았습니다.
- 아직 검증하지 않은 것: D Mission Manager의 UI 타이머(10초/5초), `COMPLETED`, AI ON 카메라/추론.
- 주니어 교육 핵심: '후보 좌표 → 실제 주행 증거 → 운영 설정'의 3단계는 성능 최적화가 아니라 **추적 가능한 변경 승인**입니다.
