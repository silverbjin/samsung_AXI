# SMARTDISH-A-L2-DBG-01 — GitHub Actions 컨테이너에서 SHA 조회 실패

- 날짜: 2026-11-23 KST
- 상태: **OPEN — 한 줄 수정 후 같은 실제 Gazebo L2 재검 대기**
- 최초 실패 Run: https://github.com/silverbjin/samsung_AXI/actions/runs/45123777661
- 최초 실행 SHA: `113f77ea8f4be0fe17a877905ca04c1e0c72c796`
- 연결 작업: [A-05 실제 Gazebo 3-leg L2](../tasks/2026-11-23_SMARTDISH-A-05_real_gazebo_3leg_EDU_KO.md)

## 1. 실제 첫 실패 지점과 영향

- L0: 지도 후보 검사 `3 passed in 0.05s`, `SMARTDISH_A_CANDIDATE_MAP_L0_PASS`.
- ROS L1: `Summary: 5 packages finished [11.4s]`, `SMARTDISH_A_GAZEBO_BUILD_PASS_NO_GOAL`.
- **L2 실패:** 증거 데이터 `source_sha` 생성 중 `git rev-parse HEAD` 호출에서 컨테이너의 Git `safe.directory` 권한 검사를 위반했습니다.

```text
fatal: detected dubious ownership in repository at '/__w/samsung_AXI/samsung_AXI'
subprocess.CalledProcessError: Command '['git', 'rev-parse', 'HEAD']'
returned non-zero exit status 128.
```

`run()` 진입 즉시 증거 딕셔너리를 만드는 단계에서 중단되었으므로, **Gazebo/Nav2 프로세스가 시작되지 않았으며 어떤 Goal도 전송되지 않았습니다.** 따라서 좌표, Nav2, lidar 성능 문제로 판단하지 않습니다.

## 2. 원인 → 증거 → 최소 수정

- 원인: GitHub Actions가 호스트에서 checkout한 workspace와 `ros:jazzy-ros-base-noble` 컨테이너 사용자 사이에 Git 소유권 경계가 달랐습니다. Git은 보안을 위해 조회를 거절했습니다.
- 해결: `scripts/smartdish_a_real_gazebo_l2.py`에서 증거용 SHA를 `git rev-parse HEAD` 대신 GitHub Actions의 `GITHUB_SHA` 환경 변수에서 취득합니다. CI 전용 실행기이므로 해당 값은 실행된 workflow checkout을 식별합니다.
- 배제: `git config --global --add safe.directory '*'`, Git 보호 해제, `sudo chown`으로 전체 파일 소유권 변경 및 Nav2/World 코드 수정.
- 변경 행: `"source_sha": os.environ["GITHUB_SHA"],` 딱 한 위치.

## 3. 재검 절차 및 상태

기존 CI의 A-04 L0 → A-05 실제 Gazebo L2를 동일 workflow로 재실행합니다. 독립 원격 Run의 `SMARTDISH_A_REAL_GAZEBO_3LEG_L2_PASS`와 3×Nav2 SUCCEEDED + /odom 원본이 확보될 때만 `RESOLVED`로 변경합니다. 현재는 **OPEN / Gazebo 3-leg NOT_RUN**입니다.

## 4. 초심자를 위한 요점

로그의 '최초 실패'가 소스코드와 시뮬레이터 가운데 어느 계층에서 발생했는지 분리해야 합니다. Git 소유권 에러에 Nav2 속도/지도/TF를 수정하는 것은 문제를 악화시킵니다. CI 메타데이터 한 줄만 고치면 해당 실패 경계를 다시 좁게 확인할 수 있습니다.
