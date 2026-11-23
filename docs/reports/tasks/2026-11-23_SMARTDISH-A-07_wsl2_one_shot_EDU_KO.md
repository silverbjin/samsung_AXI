# SMARTDISH-A-07 — WSL2 운영자 단일 실행기 제작·교육 보고서

- 날짜: 2026-11-23 KST
- 저장소: `silverbjin/samsung_AXI`
- 작업 브랜치: `feat/smartdish-a-robot`
- 소스 기준: 실 Gazebo CI 검증 `5b063a0076a78f624171e401f8041fce86d36a4e`
- 출고: `scripts/smartdish_a_wsl2_one_shot.sh` + `scripts/smartdish_a_wsl2_l3.py`
- 판정: **전용 GitHub L0 42 PASS / ROS Jazzy L1 PASS; 실제 운영자 WSL2 L3 NOT_RUN**

## 1. 왜 WSL2 전용 실행기가 필요한가?

GitHub Actions [#45125551884](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884)에서는 운영 `table_poses.yaml`으로 실제 Gazebo 주행 3구간 `SUCCEEDED`를 확인했습니다. 그러나 해당 CI는 격리된 컨테이너에서만 사용할 수 있는 자동 pseudo-TTY를 쓰므로 사용자의 WSL2에서 그대로 실행하면 안 됩니다.

따라서 본 실행기는 **실물 ROS Nav2·AMCL·Gazebo 센서와 경로를 동일하게 재사용**하되, 사용자 승인 방법을 **실제 `/dev/tty` 직접 입력**으로 분리합니다. UI(D) 10초/5초 타이머는 A 소유가 아니므로 구현·PASS 판정에서 제외합니다.

## 2. 원샷 실행 순서 및 주요 파일

```text
WSL2 Bash 1회 실행
  ├─ WSL2 + 터미널/브랜치/소스 SHA/ROS Jazzy + /mnt/c 위험 점검
  ├─ 공식 ROBOTIS Waffle Pi pinned SHA 검증
  ├─ S2-MAP-03 저장 map SHA 및 A map 목적지 고정 좌표 확인
  ├─ 기존 restaurant_* + 신규 smartdish_robot 패키지 colcon build
  ├─ 공식 Waffle Pi RGBD overlay 및 Nav2 params overlay 생성
  └─ scripts/smartdish_a_wsl2_l3.py
       ├─ Gazebo + Nav2/AMCL + /scan + /odom + map/TF 실제 readiness
       ├─ 운영자 실제 /dev/tty 승인 (자동 입력/환경변수 우회 없음)
       ├─ /collection/nav_goal → TO_TABLE / T03 → Nav2 SUCCEEDED
       ├─ /collection/nav_goal → TO_RETURN / DISH_RETURN → SUCCEEDED
       ├─ /collection/nav_goal → TO_HOME / HOME → SUCCEEDED
       └─ 3×/odom·/scan·AMCL 결과 JSON 및 간결한 tar.gz 아카이브
```

기본값은 `--headless`입니다. `--gui`로 Gazebo/RViz를 볼 수 있지만 **GUI 시각 검수는 인수 Gate가 아닙니다**.

## 3. 실제 WSL2에서 따라 하기

Ubuntu 24.04 WSL2의 **새로운 터미널**에서:

```bash
cd ~
git clone --single-branch --branch feat/smartdish-a-robot \
  https://github.com/silverbjin/samsung_AXI.git samsung_AXI_A
cd ~/samsung_AXI_A
bash scripts/smartdish_a_wsl2_one_shot.sh --headless
```

기존 클론을 최신화할 때:

```bash
cd ~/samsung_AXI_A
git fetch origin feat/smartdish-a-robot
git switch feat/smartdish-a-robot
git pull --ff-only
bash scripts/smartdish_a_wsl2_one_shot.sh --headless
```

GUI 확인이 필요하면 마지막 인수 명령만 다음과 같이 변경합니다.

```bash
bash scripts/smartdish_a_wsl2_one_shot.sh --gui
```

Nav2/AMCL + 센서 준비가 끝난 후 터미널에서 아래 문구가 요청될 때만 주변 위험/로봇 스폰을 확인하고 직접 입력합니다.

```text
YES-SMARTDISH-A-GOALS
```

안전상 명령을 파이프나 환경변수로 자동 승인할 수 없습니다. 원하지 않으면 다른 문자열을 입력하거나 `Ctrl+C`로 취소합니다.

## 4. 검증 증거와 결과 판독

성공을 인정하려면 **모두** 확인해야 합니다.

- `SMARTDISH_A_WSL2_BUILD_PASS_NO_GOAL`
- `SMARTDISH_A_WSL2_REAL_GAZEBO_PREFLIGHT_PASS_NO_GOAL`
- `SMARTDISH_A_WSL2_HUMAN_TTY_APPROVED_READY`
- `TO_TABLE`, `TO_RETURN`, `TO_HOME`별 `SUCCEEDED` + 실제 odom 이동 및 scan 3건
- `SMARTDISH_A_WSL2_ROBOT_ONLY_3LEG_L3_PASS`
- `SMARTDISH_A_WSL2_EVIDENCE_VERIFIED`
- `SMARTDISH_A_WSL2_OWNER_L3_PASS`

개별 로그 및 압축 파일은 `generated/smartdish_a_wsl2/<run_id>/`에 저장합니다. 제출용은 `SMARTDISH_A_WSL2_EVIDENCE_BUNDLE=...` 뒤의 `smartdish_a_owner_evidence.tar.gz` **하나만** 업로드하시면 됩니다. 압축본에는 원본 JSON, 실패 경계, 빌드·Gazebo·Adapter·터미널 로그 꼬리만 담습니다.

실패 `SMARTDISH_A_WSL2_FIRST_FAILURE`는 **원인 조사 출발점**이며, 실패 결과를 PASS로 바꾸지 않습니다. 완료된 검증은 기존 CI SHA `5b063a0`이고, 신규 **WSL2 현장 L3는 실제 사용자 실행 증거가 도착하기 전까지 NOT_RUN**입니다.

## 5. RED→GREEN 및 디버깅 교육 포인트

| 실패 신호 | 먼저 확인할 범위 | 하지 말아야 할 대응 |
|---|---|---|
| `BLOCKED_NO_GOAL` | WSL2/ROS/지도 SHA/좌표/TTY | 막연히 ROS/Gazebo 전부 재설치 |
| `BUILD` 실패 | `build-tail.log`, ROS Jazzy source | 이미 성공한 S7 World/Map 수정 |
| `TIMEOUT_CLOCK_SCAN_ODOM_MAP` | Gazebo 센서·브리지·TF 초기화 | 가짜 `/scan` publish |
| `TIMEOUT_HUMAN_OPERATOR_APPROVAL` | 실제 TTY 메시지·승인 문구 | CI pseudo-TTY로 우회 |
| `NAV_RESULT_TIMEOUT` | Goal Action/Map/Costmap/센서 | `SUCCEEDED` 임의 기록 |
| `PHYSICAL_ODOM_MOVEMENT_NOT_PROVEN` | 실제 odom 시간표본·정지 상태 | 임계값을 임의 완화 |

개발자용 단위 테스트 `tests/test_smartdish_a_wsl2_l3.py`는 가짜 SUCCEEDED를 만들지 않고, 판정 함수에 불량 원본이 들어오면 차단하는 순수 계약과 셸 문법·기본 도움말·Linux CI 실행 차단을 검사합니다. **CI L0 PASS는 WSL2 L3 PASS가 아닙니다.**

## 6. 후속 인계 범위

본 A-07은 A 담당 로봇만 검증합니다. D의 10초 식기 수거 대기, 5초 반납 지연, UI `COMPLETED`, AI ON은 별도 통합 검증입니다. 유효한 L3 증거는 통합시에만 재사용하며, 기존 S7 main 병합은 하지 않습니다.

## 7. 실제 GitHub CI 검증 (출고 기준)

- [GitHub Actions #45127703923](https://github.com/silverbjin/samsung_AXI/actions/runs/45127703923), 실행 SHA `c394ce66ffeb9a51f11bfcfb05afb4e5f2dea247`.
- **L0 42 PASS**: `bash -n`, 실행기 `--help`, 비-WSL2 환경에서 실행 전 차단(실제 Goal 전송 0건), 실패 증거 판정, 로봇 3구간 계약, TTY 승인 회귀 포함.
- **L1 PASS**: `Finished <<< smartdish_robot`, `smartdish_robot navigation_adapter`, `SMARTDISH_A_L1_BUILD_NO_GOAL_PASS`.
- 기존 최종 [A 실제 Gazebo L2 #45125551884](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884) PASS(최종 운영 YAML)와 별도 구분합니다.
- **L3 WSL2 현장 실주행은 아직 수행하지 않았습니다.** A-07 신규 WSL2 실행기에 대해 현장 `SMARTDISH_A_WSL2_OWNER_L3_PASS` 및 첨부 ZIP/TAR 원본 확보 전까지 성공 판정 금지.

## 8. 후속 교육용 디버깅 보고 규칙

WSL2 인수 과정의 최초 실패가 발생하면 `smartdish_a_owner_evidence.tar.gz`에 든 `summary.json`의 `first_error`를 기준으로 가장 작은 실패 경계를 분리합니다. 기존 S7 주행 CI PASS를 신규 현장 PASS로 대체하지 않으며, 원인·최소수정·재검 SHA·성공/실패 결과를 `docs/reports/issues/`에 별도 신규 문서로 보존합니다.
