# S6 — 강사 WSL2 단일 최종 인수 가이드 (GitHub 고정 SHA)

> 2026-11-23 기준: 공개 CI L0/L1/L2 PASS, 강사 WSL2 L3 NOT_RUN, RTF 90% HOLD. 이 가이드는 로봇 코드를 다시 수정하지 않습니다.

## 1. 왜 이 시나리오인가?

- 기존 S5의 LiDAR `/scan` Costmap·Collision Monitor·속도 NORMAL/SOUP·두 Nav2 Goal은 검증된 채 보존합니다.
- 새 S6에서는 **TABLE_3 Action SUCCEEDED → 실제 Odom 정지 유지 → 그때만 RGB 임시 구독 → 식기 STACKED 판단 → PICKUP_RETURN**을 실행합니다.
- Vision은 `/cmd_vel`을 쓰지 않습니다. RGB 이미지 없음, 불확실, 정지 불충분이면 자동 복귀 Goal을 보내지 않습니다.
- 사용한 모델은 Gazebo 파란 식기 테두리 한 장면에 대한 3차원 색상·층 특징 프로토타입입니다. 다른 조명·식기에서의 AI 정확도는 NOT_VERIFIED입니다.

## 2. 사용자 실행 — WSL2 Ubuntu 24.04 한 블록

다음 릴리스 SHA는 실제로 게시된 **GitHub 원샷 스크립트의 불변 커밋**입니다. 내부 실행은 실제 Gazebo L2가 PASS한 별도의 고정 소스 SHA로 동작합니다.

```bash
(
  set -Eeuo pipefail
  RELEASE_PIN='105300463d0480f5f7283379808adb59bf5630e8'
  SCRIPT="$(mktemp --suffix=.sh)"
  trap 'rm -f "$SCRIPT"' EXIT
  curl -fL --retry 3 --connect-timeout 10 --max-time 90 \
    "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$RELEASE_PIN/scripts/samsungaxi_s6_wsl2_l3_once.sh" \
    -o "$SCRIPT"
  bash -n "$SCRIPT"
  bash "$SCRIPT" --self-test
  bash "$SCRIPT"
)
```

## 3. 실행 중 운영자 승인

1. `S6_L3_RELEASE_SELF_TEST_PASS_NO_GOAL`, `S6_L3_PREFLIGHT_PASS_NO_GOAL`이 출력되는지 확인하십시오.
2. Gazebo/RViz에서 로봇 시작 위치·테이블 접근 경로를 육안 점검하십시오.
3. 실제 TTY 프롬프트가 나타나면 **`YES-S5-LIVE-GOALS`를 직접 입력**해 Goal을 승인하십시오.
4. TABLE_3 → RGB 3프레임/STACKED → PICKUP_RETURN → 실제 Collision Monitor STOP의 결과를 확인하십시오.
5. 증거 출력이 완료되면 Ctrl+C로 종료합니다. 기존 실행기가 `SAMSUNGAXI_DIAGNOSTIC_ZIP=...` 경로를 출력합니다.

Ctrl+C 뒤 `RUN_RC=130` 자체는 주행 실패의 근거가 아닙니다. `s5_live_evidence.json`의 Goal·Vision·STOP 결과 및 `FIRST_FAILED_MARKER=NONE`을 함께 확인해야 합니다.

## 4. 검수에 필요한 실제 증거

- 가장 최신 진단 ZIP: `ls -lt ~/samsungaxi_gui_evidence/samsungaxi_gui_*.zip | head`
- 같은 런 ID의 RGB 원본: `find ~/samsung_AXI/generated/s5 -name s6_table_rgb.ppm -type f -print`
- 반드시 실제 런의 진단 ZIP 및 RGB PPM을 **함께 첨부**하십시오. 진단 ZIP에는 Vision JSON과 원본 이미지 해시가 있으나, 기본 S5 실행기는 PPM 이미지 자체를 ZIP에 넣지 않습니다.
- ROS Image의 원본 RGB 페이로드 SHA256을 JSON `s6_vision.image.image_sha256`와 비교합니다.
- GUI 육안 검수 여부는 사용자가 기록합니다. 자동 로그만으로 GUI PASS를 주장하지 않습니다.

## 5. 성공 판정 문자열

| 단계 | 필수 실제 문자열/증거 |
|---|---|
| NO_GOAL | `S5_OWNER_PREFLIGHT_PASS_NO_GOAL` |
| TABLE_3 | `S3_NAV02_GOAL_SUCCEEDED=TABLE_3` |
| Vision | `S6_VISION_REAL_RGB_STACKED_RETURN_AUTHORIZED` 및 RGB 원본 SHA |
| 복귀 | `S3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN` |
| 메뉴 속도 | `S4_MENU_NORMAL_SOUP_REAL_ODOM_SPEED_PASS` |
| STOP | `S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS`, 최종 출력/이동 임계 내 |
| 통합 | `S6_VISION_REAL_GAZEBO_L2_INTEGRATED_PASS` (현재 실행의 실제 출력) |

성공 마커가 하나라도 빠지거나 `S6_VISION_HOLD_NO_RETURN_GOAL` 등이 기록되면 S6 L3는 HOLD입니다. CI L2 PASS로 현장 L3를 대체하지 않습니다.

## 6. 주니어 교육 포인트

- Goal Action `SUCCEEDED`와 실제 모터의 정지는 다릅니다. CI 첫 RED에서는 약 0.11m/s의 실제 Odom 속도 때문에 복귀를 차단했습니다.
- 새 Odom 표본을 관측해 0.65초 정지·위치 드리프트까지 확인한 GREEN에서는 도착 후 사진 촬영이 진행됐습니다.
- `lazy:true` 영상 브리지와 Gazebo 렌더링 완전 OFF는 같은 뜻이 아닙니다. GPU 절감/RTF 개선은 현재 별도 실험입니다.
- 실제 L2 증거: https://github.com/silverbjin/samsung_AXI/actions/runs/45098202033
- 강사 WSL2 GUI 인수는 아직 미실행이며, 사용자 ZIP 검수 후에만 main 병합 조건을 판단합니다.
