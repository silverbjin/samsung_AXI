# SMARTDISH-A-04 — 실제 지도에서 DISH_RETURN 후보 선택과 정적 지도 검증

- 날짜: 2026-11-23 KST
- 이전 HEAD: `7c0ba45762df58548eb8fae4ea5e24a5deaa3376`
- 현재 상태: **CONFIRMED_BY_REAL_GAZEBO_L2 / Run #45124877004 (3 Nav2 SUCCEEDED)**
- AI OFF 목표: `HOME → T03 → DISH_RETURN → HOME`, 기존 S7 주행/안전 유지

## 1. 후보 좌표는 어디서 왔습니까?

S2-MAP-03 실 Gazebo 전체 지도 조사 보고의 `maps/candidates/s2_map03/restaurant_map_quality.json`에는 Waypoint #5, World `(-3.75,-0.60)`의 실제 관측 이력이 있습니다. 주방 카운터는 원본 World의 `(-4,-2.2)`에 있으며, 이 지점은 북쪽 접근 통로에 위치합니다.

기존 `scripts/s3_map_contract.py`의 World spawn `(-2.60,-2.20)` ↔ map `(0,0)` 변환을 적용하면 World `(-3.75,-0.60)` → **map `(-1.15,1.60)`**입니다. `yaw=-π/2`는 주방 카운터를 향하는 시작 방향 **후보**이며 실제 주행 확정 전에는 변경 가능합니다.

## 2. 왜 바로 운영 YAML에 쓰지 않습니까?

S2의 Waypoint 방문 성공이 Nav2 `NavigateToPose` 목표 도착을 자동으로 증명하지 않기 때문입니다. 별도 `return_pose_candidate.yaml`에만 수치를 넣고 운영 `table_poses.yaml`은 `DISH_RETURN: null`로 유지했습니다.

## 3. 최소 RED→GREEN 검사

- `tests/test_smartdish_a_return_candidate.py`는 조사 Waypoint 출처, 지도 파일 SHA·프레임, 접근 셀의 known-free 여부, 0.25m 반경의 알려진 자유 공간 및 HOME/T03 연결성을 검사합니다.
- `0.25m` 반경은 단순한 정적 위험 선별이며 **Nav2 비용지도·동적 장애물·실제 footprint 도착 보장은 아닙니다.**
- [Run #45123777661](https://github.com/silverbjin/samsung_AXI/actions/runs/45123777661)에서 `3 passed in 0.05s`, `SMARTDISH_A_CANDIDATE_MAP_L0_PASS` 확인. 이 검사는 **정적 지도 PASS**이지 실제 이동 PASS가 아닙니다.
- 실제 A 전용 3-leg ROS Action/odom/AMCL L2를 성공한 뒤에만 운영 YAML을 승격합니다.

## 4. 재현·디버깅

```bash
python3 -m pytest -q tests/test_smartdish_a_return_candidate.py
```

실패 시 최초 오류(예: `RETURN_CLEARANCE_NOT_FREE`)와 지도 원본 SHA를 기록하고 **후보를 교체**합니다. 기존 S7 지도나 임계값을 완화하여 통과시켜서는 안 됩니다.

## 5. 주니어 핵심 질문

왜 (1) SDF World, (2) SLAM map 좌표, (3) Nav2 실제 Action 성공을 순서대로 확인해야 할까요? 세 단계가 서로 다른 의미를 가짐을 보고서의 증거 수준과 함께 설명해 보세요.

## 6. 최종 확정 추가 기록

[실제 3-leg CI #45124877004](https://github.com/silverbjin/samsung_AXI/actions/runs/45124877004)의 `TO_RETURN/DISH_RETURN`은 AMCL map(-1.10345,1.40938), 목표(-1.15,1.60), 오차 0.196m, odom 시작점 대비 최대 변위 6.459m, Action **SUCCEEDED**를 기록했습니다. 따라서 본 문서에서 과거 '후보'라고 기술한 좌표는 이후 **A-06 운영 YAML에 승격**되었습니다. 초기 설계 단계에서 null을 유지한 이력은 교육 목적상 그대로 보존합니다.
