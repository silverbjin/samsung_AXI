# SmartDish S5-LIVE-01 — 강사 WSL2 TTY 승인 후 센서 신선도 오류·최소 수정·실제 Gazebo CI

## A. 최초 현장 증거 및 실패 경계

- 저장소: `silverbjin/samsung_AXI`; 기준 main `0021c9425233118e30b398fac752ecc0050b7123`.
- 현장 원샷 소스: `340527bf81c3ad23fdef0279fbaf07314d242a0b`.
- **Preflight ZIP** `samsungaxi_gui_20261120T053904Z-4147.zip`, SHA256 `0b1e33bd41ab573c7f0ac2572a4a0b35edb13080b08738aeaec499115c9eb5c6`, `VERDICT=PREFLIGHT_PASS_NO_GOAL`.
- **Live ZIP** `samsungaxi_gui_20261120T053905Z-4185.zip`, SHA256 `e4ddcbdb87853692100c6bfa5a1402e9614914b53f5ff64ef50a92d646a6475a`. 지도 SHA와 공식 AMCL·Nav2/CM Lifecycle ACTIVE. `S5_OWNER_GOALS_AUTHORIZED` 이후 첫 오류 `NAV_PREGOAL_SENSOR_STALE_TABLE_3`, `RUN_RC=1`, S5 JSON `goal_sent=false`.
- 원본 ZIP은 강사의 환경/경로 정보가 포함돼 공개 GitHub에 올리지 않음. SHA256·필수 사실만 보존.
- 시뮬레이션 종료 시 추가 Gazebo/RViz 비정상 종료 메시지가 존재할 수 있으나 **첫 실패는 Goal 발행 이전 센서 신선도**. 후속 종료 안정성과 분리.

## B. 코드 근본 원인

- `scripts/ci_s3_amcl_smoke.py`의 single-threaded ROS Executor는 `rclpy.spin_once(node,...)`에 의존해 `/scan`/`/odom` 콜백에서 monotonic arrival 시각을 갱신.
- 사용자 승인에 `input()` 사용: 이 대기 동안 Executor 콜백 미실행. 강사가 GUI를 8초 넘게 관찰한 뒤 YES를 입력하면, Goal 전 안전 검사 `time.monotonic()-scan_t > 8 or ...-odom_t >8`에서 stale 판정.
- 기존 S5 CI는 `--live-owner` 없이 자동 진행했고 **실제 사람의 입력 대기**를 검증하지 않아 배포 실행 경로와 검증이 불일치.
- 본 수정은 **센서 stale 차단이 정상적으로 작동했다는 점은 보존**하며, 그 전에 관찰 콜백을 부당하게 정체시키는 원인을 제거.

## C. RED→GREEN 및 변경 파일

1. [RED CI #44685116880](https://github.com/silverbjin/samsung_AXI/actions/runs/44685116880): `answer=input(`이 Executor 콜백을 굶기는 문제를 검출, 1 failed / 1 passed.
2. `scripts/s5_owner_approval.py` 신설: 기존 ROS Executor를 `spin_once`하면서 `select.select`로 TTY 승인 읽기. 잘못된 승인/EOF/시간 초과는 차단. 별도 ROS 노드 또는 센서 가공 없음.
3. 승인 후 신규 Scan·Odom **둘 다**의 callback count와 arrival monotonic 시각을 확인하는 fail-closed 8초 gate 추가. 원래 Goal 전 8초 검사 **불변**.
4. `scripts/ci_s3_amcl_smoke.py` 수정: TTY 승인 대기시간/승인 후 센서 freshness·count를 실제 JSON에 기록. `--ci-owner-exit-on-success`는 CI 실제 Gazebo 성공 후에만 정상 반환하는 옵션, 사용자 GUI는 기존 Ctrl+C 보존.
5. `tests/test_s5_owner_approval.py`: 실제 pseudo-TTY 지연 승인, 잘못된 입력/EOF, 새 Scan·Odom 양쪽 확인, Scan 또는 Odom 중단 시 NO_GOAL 차단. 기존 정적 계약 테스트는 구현 위치 이전만 반영.
6. `scripts/s5_ci_delayed_tty.py`: GitHub CI에서만 동작. 실제 Gazebo Python 실행기를 pseudo-TTY로 시작하고 프롬프트를 관측한 뒤 12초 후 YES 입력. ROS·Gazebo·Scan/Odom은 **실제** 사용. 주행/CM 로직 재개발 없음.
7. `.github/workflows/restaurant-s5-approval-ci.yml`: 전용 L0 + 공식 Jazzy/Nav2/Harmonic 모델 빌드 + 동일 실제 Gazebo L2.

## D. 실제 통합 CI 성공과 출고 범위

- **[최종 GREEN #44686196254](https://github.com/silverbjin/samsung_AXI/actions/runs/44686196254)**, 정확히 검증된 실행 소스 `c59dd030b2f70351b06eae39e3b3bfeb7ed4b128`.
- L0 GREEN; 실제 Gazebo L2에서 `S5_CI_OWNER_TTY_PROMPT_OBSERVED`→`S5_CI_DELAYED_TTY_YES_SENT DELAY_SEC=12.0`→`S5_OWNER_GOALS_AUTHORIZED WAIT_SEC=12.026`→`S5_OWNER_FRESH_SCAN_ODOM_AFTER_APPROVAL_PASS SCAN_AGE_SEC=0.004 ODOM_AGE_SEC=0.0`.
- 실제 Nav2 Action TABLE_3 SUCCEEDED, 물리 Odom **5.109m**, AMCL error **0.195m**; PICKUP_RETURN SUCCEEDED, Odom **4.985m**, AMCL error **0.218m**.
- 실제 Odom p75 NORMAL 0.23m/s / SOUP 0.11m/s; Gazebo 물리 원통 LiDAR STOP 구역 29점, Collision Monitor STOP, 필터 출력 0과 물리 정지 성공.
- `S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS` 및 `S5_OWNER_DELAYED_TTY_REAL_GAZEBO_L2_PASS`.
- Compact Artifact [#14606188931](https://github.com/silverbjin/samsung_AXI/actions/runs/44686196254/artifacts/14606188931), ZIP 4,768 bytes, SHA256 `5fdc9dd07a974e11adb31de5fc26fbed04de856d2055bd995dd16744c3cf583c`.
- S2 지도, S3 배달/복귀 기반 코드, S4 Nav2 속도·Collision Monitor 정책 **변경 없음**. 새 Planner/SLAM/Supervisor/YOLO/모터제어 없음.

## E. Owner WSL2 인수와 HOLD 경계

- 출고 PIN: `c59dd030b2f70351b06eae39e3b3bfeb7ed4b128`.
- `docs/S5_LIVE_GUIDE_KO.md`의 GitHub RAW 원샷: `bash -n` → `--self-test` → `--s5-live --preflight-only` → `--s5-live --approve-goals`; 최종 YES는 **강사 본인**이 TTY에서 입력.
- 승인 후 실 Scan/Odom 갱신 PASS 표식이 있어야 Goal 진행. 실제 주행·정지 후 Ctrl+C로 GUI 종료하고 Compact ZIP 생성, 현장 로그를 별도 검수.
- **`S5_OWNER_CI_L2=PASS`, `S5_LIVE_WSL2_L3=NOT_RUN`**. 공개 GitHub Xvfb/llvmpipe는 강사 WSL2 D3D12 GPU/RTF L3를 대체하지 않음.
