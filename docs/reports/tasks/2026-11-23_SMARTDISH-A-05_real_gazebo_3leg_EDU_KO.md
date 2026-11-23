# SMARTDISH-A-05 — Gazebo 실제 3구간 Nav2/odom 교육용 인수 보고서

- 날짜: 2026-11-23 KST
- 현재 상태: **A-05 실제 Gazebo 3-leg L2 PASS / R03 #45124877004**, 후속 D 통합 NOT_RUN. 앞선 R01/R02 RED는 하단에 별도 보존.
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

## 5. 최초 CI 실패 및 교육용 디버깅

[Run #45123777661](https://github.com/silverbjin/samsung_AXI/actions/runs/45123777661): A-04 L0 **3 PASS**, ROS 패키지 빌드 PASS, 실제 Gazebo 기동 전 `git rev-parse HEAD`가 컨테이너 Git ownership 검사에서 차단되었습니다. [원인과 수정·재검 보고서](../issues/2026-11-23_SMARTDISH-A-L2-DBG-01_git_safe_directory_EDU_KO.md) 참조. 실제 물리 Goal은 **0건**, MAP 좌표의 유효/무효 결론을 낼 수 없는 환경 진단 실패입니다.

## 6. R02 — Gazebo 사전검사 PASS, TTY 승인 경계 첫 실패

[Run #45124267209](https://github.com/silverbjin/samsung_AXI/actions/runs/45124267209)에서 실제 Gazebo/AMCL/Nav2와 scan/odom은 준비됐으나, 승인 함수의 `os.fdopen(fd,"r+")` 비탐색 스트림 오류로 Goal 전송 전에 실패했습니다. 원인/로컬 최소 재현/수정과 테스트를 [A-L2-DBG-02](../issues/2026-11-23_SMARTDISH-A-L2-DBG-02_tty_rplus_EDU_KO.md)에 기록했습니다. **실물 3-leg 성공은 여전히 미확인**이며 새 Run으로 재검합니다.

## 7. 문서·테스트 교차 QA

TTY 승인 함수를 ROS 독립 모듈로 이동한 뒤 기존 `test_smartdish_a_package.py`의 **정적 문자열 검사 위치도 함께 변경**했습니다. 단순 문자열 검사가 실제 TTY 동작을 대신하지 않도록 `test_smartdish_a_tty.py`에서 프로세스와 pseudo-TTY로 승인/거절을 별도로 실행합니다.

## 8. R03 — 최종 실 Gazebo L2 GREEN (검증 SHA 고정)

- [실제 GitHub Actions #45124877004](https://github.com/silverbjin/samsung_AXI/actions/runs/45124877004) **PASS**, 실행 SHA `6d7e3508ea1f4a5d32ab257904b2335f859b3f0b`.
- 동일 `request_id=SMARTDISH-A-CI-L2-001` / 3개의 JSON nav_goal과 대응하는 3개의 실제 `nav_result=SUCCEEDED`.
- 실 Gazebo/AMCL/Nav2 `A_L2_REAL_GAZEBO_PREFLIGHT_PASS_NO_GOAL` 및 `SMARTDISH_A_SENSOR_PREFLIGHT_PASS_NO_GOAL`.
- 실제 CI pseudo TTY는 프롬프트 관측 **10초 뒤** 승인, `SMARTDISH_A_OPERATOR_APPROVED` → `SMARTDISH_A_READY` 순서 확인.

| 구간 | Action | odom 최대 변위(m) | odom 표본 | scan 표본 | AMCL 목표 오차(m) |
|---|---|---:|---:|---:|---:|
| TO_TABLE / T03 | SUCCEEDED | 5.181 | 679 | 136 | 0.098 |
| TO_RETURN / DISH_RETURN | SUCCEEDED | 6.459 | 943 | 189 | 0.196 |
| TO_HOME / HOME | SUCCEEDED | 1.940 | 613 | 123 | 0.166 |

3구간 종료 마커: `SMARTDISH_A_REAL_GAZEBO_3LEG_L2_PASS`, `SMARTDISH_A_REAL_GAZEBO_L2_EVIDENCE_VERIFIED`. 각 /odom 값은 **구간 시작점 대비 최대 위치 변화**입니다(누적 주행 길이 아님). L2 JSON 및 Gazebo 로그는 해당 Run의 GitHub Actions Artifact `smartdish-a-l2-evidence-45124877004`에 보존되었습니다.

**판정 경계:** A 단독 로봇 이동만 `ROBOT_ONLY_REAL_GAZEBO_L2_PASS`. D 서비스 UI의 실제 `COMPLETED`, 대기시간 10초/5초, AI ON 판정은 검증하지 않았습니다. 실제 현장 WSL2 L3도 재실행하지 않았습니다.
