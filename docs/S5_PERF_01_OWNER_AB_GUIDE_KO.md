# S5-PERF-01 — 강사 WSL2/WSLg 실제 라이브 RTF A/B 인수 가이드

## 현재 판정과 범위

- 실제 **기존 S5 기능 L3 인수는 완료**: NORMAL 테이블3 배달, SOUP 복귀, 실제 LiDAR→Collision Monitor STOP.
- 사용자 제출 기존 라이브 ZIP(`samsungaxi_gui_20261120T062446Z-5175.zip`) RTF 중앙값 **0.8439**, 하위 10% **0.4030**, 100개 표본 중 44개가 0.90 이상.
- 신규 **주행 중 RTF 목표 0.90 이상은 아직 미검증**. ROS CI의 headless llvmpipe RTF를 강사 WSLg GPU 성능으로 대체하지 않습니다.
- S5의 **정상 5Hz RGB-D 기본값은 유지**. 후보는 S5 라이브의 `--perf-rgbd2`에서만 RGB-D 2Hz이며 공식 Waffle Pi LiDAR 10Hz, 모터, 월드, Nav2, 메뉴 속도, CM 안전정지는 바뀌지 않습니다.

## 고정 SHA GitHub 원샷 — 총 2회, 동일 경로 비교

다음 명령 블록의 `MODE`만 바꿔 **별도의 새 터미널 세션에서 각각 한 번씩** 실행합니다. 먼저 `baseline`, 정상 완료 후 `rgbd2`를 실행하십시오. 각 회차마다 사람이 Goal을 별도 승인해야 하며, 기존 성공한 LIVE를 무인으로 연달아 주행시키지 않습니다.

```bash
(
  set -Eeuo pipefail

  PIN="e72d2d04561494becac8ba597105bc9afc793b67"
  MODE="baseline"   # 1회차: baseline / 2회차: rgbd2
  SCRIPT="$(mktemp --suffix=.sh)"
  trap 'rm -f "$SCRIPT"' EXIT

  curl -fL --retry 3 --connect-timeout 10 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/samsungaxi_wsl2_gui_acceptance_once.sh" \
    -o "$SCRIPT"

  bash -n "$SCRIPT"
  SAMSUNG_AXI_GUI_PIN="$PIN" bash "$SCRIPT" --self-test
  SAMSUNG_AXI_GUI_PIN="$PIN" bash "$SCRIPT" --s5-live --preflight-only

  case "$MODE" in
    baseline)
      SAMSUNG_AXI_GUI_PIN="$PIN" \
        bash "$SCRIPT" --s5-live --approve-goals --perf-baseline ;;
    rgbd2)
      SAMSUNG_AXI_GUI_PIN="$PIN" \
        bash "$SCRIPT" --s5-live --approve-goals --perf-rgbd2 ;;
    *)
      echo 'S5_PERF_BLOCKED_INVALID_AB_MODE' >&2
      exit 2 ;;
  esac
)
```

### 사용 방법

1. 두 번 모두 **기존 Gazebo·RViz 세션을 종료**한 상태에서 시작하십시오. 기존 S2-MAP-03 지도·로봇 위치·동일한 NORMAL→SOUP 경로를 사용해야 비교가 유효합니다.
2. Gazebo/RViz와 경로를 확인하고, 각각의 실행 터미널에서 `YES-S5-LIVE-GOALS`를 직접 입력하십시오.
3. NORMAL 배달→SOUP 복귀→물리 CM STOP의 성공 메시지를 확인한 후, 화면 확인을 마치고 `Ctrl+C`로 종료하십시오.
4. 각 회차에서 터미널이 출력하는 **`SAMSUNGAXI_DIAGNOSTIC_ZIP=...`** 경로의 ZIP 하나씩을 보존하십시오. 두 ZIP을 비교해야 후보 성능을 판정할 수 있습니다.

## ZIP 추가 증거

기존 S5 성공/실패·GPU·ROS·RTF 증거는 보존하며, A/B 모드인 경우 다음 파일이 추가됩니다.

- `s5_perf_timeline.csv`: 같은 실제 Gazebo Stats 토픽을 약 1Hz로 관찰, `startup`, `normal_delivery`, `soup_return`, `safety_fixture` 등의 시각·단계와 RTF를 연결. 프로세스별 CPU 수치는 `ps`의 누적 평균이며 순간 최대 부하가 아닙니다.
- `s5_perf_summary.json`: `rtf.all` 및 `rtf.moving`의 표본 수·중앙값·하위 10%·90% 이상 표본 수. `rtf.phase_normal_delivery`, `rtf.phase_soup_return`도 분리 기록.
- `s5_perf_collector.log`: 기록기 자체의 오류 또는 정상 종료 상태.
- `gpu_util_pct`: `nvidia-smi` 지원 시만 관찰하며, WSLg D3D12 렌더링의 직접적인 GPU 부하 증명이 아닙니다. 값이 비어 있으면 추정으로 채우지 않습니다.
- `status.txt`에는 `S5_PERF_MODE`와 `S5_PERF_PROFILE_PRESENT`를 보존합니다.

### 성능 인수 기준

- 기존 S5 배달·복귀·속도·실제 STOP이 **두 실행에서 모두 PASS**해야 합니다.
- `rtf.all`의 표본 **50개 이상**, `rtf.moving`의 표본 **25개 이상**을 요구합니다. 표본이 부족하면 `INSUFFICIENT`로 처리합니다.
- 실제 **라이브 전체 RTF 중앙값 ≥0.90**, 실제 **이동 구간(NORMAL+SOUP) RTF 중앙값 ≥0.90**를 함께 요구합니다. `rtf.live_target_verified=true`가 아닌 한 S5-PERF-01 목표 PASS라고 주장하지 않습니다.
- `rgbd2`가 기본 5Hz보다 좋아졌다는 판단은 **같은 강사 WSL2 PC의 새 A/B 측정 결과**로만 합니다. 기본 5Hz에서 이미 목표가 달성되면 후보를 채택할 이유가 없습니다.
- RGBD 2Hz가 기능을 훼손하거나 목표에 미달하면 후보를 적용하지 않고 기존 **기능 L3 ACCEPTED**를 보존합니다.

## 공개 CI 증거와 한계

- [공개 CI #44692959074](https://github.com/silverbjin/samsung_AXI/actions/runs/44692959074), 정확히 검증된 SHA `666da599e0af1ef866c9d29bec073a1462ca5756`: **L0 30/30 PASS**, 실제 Gazebo L2 RGBD 2Hz, 승인 12.02초 지연, NORMAL TABLE_3 Odom **5.115m**, SOUP PICKUP_RETURN **5.072m**, p75 0.23/0.11m/s, 실제 LiDAR 29점→CM STOP PASS.
- [Compact Artifact #14609536772](https://github.com/silverbjin/samsung_AXI/actions/runs/44692959074/artifacts/14609536772) (ZIP 7,046 bytes, SHA256 `aae8bf7cbfe483102285a5b5312d40d5c5cd3d69ace7d04e837268509ef736a1`).
- 이 L2는 **후보의 기능 안전성 검증**입니다. WSL2 D3D12 GUI 성능 90% 달성의 증거가 아니므로 강사 현장 A/B ZIP 2개가 필요합니다.

참고: [Gazebo Harmonic 센서 설정](https://gazebosim.org/docs/harmonic/sensors/), [Gazebo Harmonic GUI RTF 표시](https://gazebosim.org/docs/harmonic/gui/).

## 2026-11-20 16:31 KST 현장 Goal ABORT 오류 수정 출고

- 이전 SHA `666da599e0af1ef866c9d29bec073a1462ca5756`의 5Hz baseline 현장 ZIP `samsungaxi_gui_20261120T073155Z-7990.zip`에서 **첫 TABLE_3 Goal 수락 후 ABORTED(status 6)**. 실제 `NAV_GOAL_NOT_SUCCEEDED_TABLE_3:6`; 성공으로 판정하지 마십시오. NO_GOAL Preflight ZIP `samsungaxi_gui_20261120T073154Z-7950.zip`은 PASS.
- 실패 시 주행 RTF median **0.6403**(26 표본), 전체 median 0.9737(50 표본)으로, **이동 구간 RTF 성능 목표 0.90 미달**. ROS/Nav2 오류의 구체적인 원인은 기존 종료 요약에서 빠져 있으므로 단정하지 않습니다.
- 새 SHA `e72d2d04561494becac8ba597105bc9afc793b67`: Nav2 ABORT에서 실제 `NavigateToPose.Result.error_code/error_msg`, Action feedback(남은 거리·복구 횟수), 물리 Odom·AMCL·센서 age를 `s5_live_evidence.json > nav2_goal_failure`에 기록. Goal 수락 후 실패해도 최종 `goal_sent=true`를 정확히 보존합니다.
- Compact ZIP의 `ci-s3-summary.txt`에 `NAV2_ACTIVE_GOAL_ERRORS_AND_CONTEXT_LAST_120` 블록을 추가하고, `status.txt`는 `FIRST_FAILED_PHASE=NAV2_ACTIVE_GOAL`, `FIRST_FAILED_MARKER=NAV_GOAL_NOT_SUCCEEDED_TABLE_3:6` 등을 확인할 수 있습니다. ZIP의 `owner_tails.txt`에는 **이번 실행에서 출력한 로그 경로만** 포함하며 이전 실패를 섞지 않습니다.
- 부하 영향을 배제하기 위해 기본 RTF A/B 실행에서는 주기적인 `ps`·`nvidia-smi` 외부 프로세스 샘플링을 중단합니다. RTF 자체는 실제 Gazebo Stats로 계속 계측합니다. 심층 리소스 연구는 기록기 독립 옵션 `--resource-probes`를 명시해야 하며 기본 라이브에는 포함되지 않습니다.
- **공개 실제 Gazebo 필드 동등성 CI GREEN**: [Run #44697440947](https://github.com/silverbjin/samsung_AXI/actions/runs/44697440947), 검증 소스 `e72d2d04561494becac8ba597105bc9afc793b67`; L0 34/34 PASS, 기본 RGB-D **5Hz**, LiDAR 10Hz, GUI Xvfb, 실제 RTF 기록기 동시 실행, 12초 TTY 승인, 테이블3 5.153m·픽업 복귀 5.097m, 메뉴 속도 0.23/0.11m/s, 물리 CM STOP PASS, 타임라인·요약 생성 PASS.
- [증거 Artifact #14611542017](https://github.com/silverbjin/samsung_AXI/actions/runs/44697440947/artifacts/14611542017), ZIP 12,310 bytes, SHA256 `32e8077a2ddcc484ff531abddc5e9b34b1d547b8bac147024f2de73aa5879863`.
- **권장 재검 순서:** 지금은 `MODE="baseline"`을 **단 한 번** 수행하십시오. 성공 로그에 `S3_NAV02_GOAL_SUCCEEDED=TABLE_3`, `PICKUP_RETURN`, `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS`가 모두 있다면 그다음 `MODE="rgbd2"`를 단 한 번 수행합니다. baseline이 다시 ABORT되면 임의 재시도·Nav2 파라미터 완화 없이 **새로운 ZIP 한 파일만 첨부**하십시오.
- 증거 ZIP의 CPU/GPU 시계열이 비어 있는 것은 경량 계측 의도입니다. `rtf.moving.sample_count`와 `rtf.moving.median`를 함께 보십시오. **WSL2 실제 RTF 90% 인수는 여전히 HOLD**입니다.
