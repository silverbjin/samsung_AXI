# SAMSUNGAXI S7 — 강사 WSL2 단일 최종 기능 인수 가이드

> 출고 상태: GitHub 실제 Gazebo L0/L1/L2 PASS, 강사 WSL2 L3 NOT_RUN. GUI 장면의 육안 품질은 사용자 담당이며 자동 기능 게이트에서 제외합니다. RTF 90%는 HOLD.

## 1. 유일한 SHA와 근거
- 실행기와 실제 ROS/Gazebo 코드 **동일 SHA**: 097e5aca022f59b18f289e7d383a3a6b85a5da1a
- [실제 Gazebo S7 양성·음성 CI #45112942260](https://github.com/silverbjin/samsung_AXI/actions/runs/45112942260) L0/L1/L2 PASS
- [S7 원본 이미지·안전 증거 Artifact #14790562351](https://github.com/silverbjin/samsung_AXI/actions/runs/45112942260/artifacts/14790562351)
- [강사·학생 자료 정적 CI #45113383076](https://github.com/silverbjin/samsung_AXI/actions/runs/45113383076) PASS
- 공식 엔트리 파일: scripts/samsungaxi_s7_wsl2_l3_once.sh
- 코어 안전 경계: NO_GOAL 사전검사, 실제 TTY 승인, LiDAR Collision Monitor STOP.

## 2. WSL2 Ubuntu 24.04에서 복사할 유일한 실행 블록

    (
      set -Eeuo pipefail

      PIN="097e5aca022f59b18f289e7d383a3a6b85a5da1a"
      SCRIPT="$(mktemp --suffix=.sh)"
      trap 'rm -f "$SCRIPT"' EXIT

      curl -fL --retry 3 --connect-timeout 10 --max-time 90 \
        "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/samsungaxi_s7_wsl2_l3_once.sh" \
        -o "$SCRIPT"

      bash -n "$SCRIPT"
      SAMSUNGAXI_S7_SOURCE_SHA="$PIN" bash "$SCRIPT" --self-test
      SAMSUNGAXI_S7_SOURCE_SHA="$PIN" bash "$SCRIPT"
    )

위 PIN 단 하나를 사용합니다. 실행기/내부 실제 소스가 같은 SHA에서 내려받아지므로 과거 G06/G09처럼 서로 다른 SHA를 조합하지 않습니다. 기존 S6 실행기를 섞지 마십시오.

## 3. 기대하는 필수 성공 로그
    S7_OWNER_SELF_TEST_PASS_NO_GOAL SOURCE_SHA=097e5aca022f59b18f289e7d383a3a6b85a5da1a
    S7_EXACT_RUNTIME_AND_ENTRY_SHA=097e5aca022f59b18f289e7d383a3a6b85a5da1a
    S7_OWNER_PREFLIGHT_PASS_NO_GOAL
    # 운영자가 실제 TTY에서 YES-S5-LIVE-GOALS 입력 후 주행 시작
    S7_STARTUP_WORLD_GENERATED_NO_GOAL=stacked ...
    S7_STARTUP_SCENARIO=stacked
    S7_STARTUP_WORLD_APPLIED=stacked
    S3_NAV02_GOAL_SUCCEEDED=TABLE_3 ...
    S6_VISION_REAL_RGB_STACKED_RETURN_AUTHORIZED
    S3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN ...
    S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS
    S6_VISION_REAL_GAZEBO_L2_INTEGRATED_PASS
    S7_STARTUP_STACKED_REAL_GAZEBO_L2_PASS
    SAMSUNGAXI_DIAGNOSTIC_ZIP=...

상기 출력 순서는 일부 런치 로그에 따라 달라질 수 있습니다. 그러나 NO_GOAL→TTY 승인→TABLE_3→Odom 정지→최신 RGB STACKED→복귀 Goal→STOP의 **기능 순서**는 반드시 지켜져야 합니다.

## 4. 강사 현장 인수 안내
- 주행 전 실제 TTY의 YES-S5-LIVE-GOALS 입력은 계속 필수입니다. 승인 문자열을 파이프로 자동 주입하지 마십시오.
- 접시는 S7 전용 Gazebo 월드가 시작할 때부터 존재합니다. TABLE_3 도착 뒤 중복 생성하지 않습니다.
- 운영자는 화면의 시각적 품질을 자체 확인합니다. 자동 기능 합격에는 장면 육안 판정이 필요하지 않지만 위험하게 보이면 승인하지 마십시오.
- TABLE_3와 PICKUP_RETURN Action 상태 4(SUCCEEDED), 실제 Odom 정지, RGB 3프레임·raw SHA256 일치, Vision STACKED, LiDAR STOP·filtered cmd_vel 0·Odom 정지가 필수입니다.
- 완전한 성공 증거가 출력된 다음 Ctrl+C로 종료해 자동 출력된 진단 ZIP을 보존하십시오. RUN_RC=130만으로 실패 또는 완전 정상 종료를 단정하지 마십시오.
- 사전검사 ZIP 1개와 라이브 ZIP 1개를 제출하십시오. PIN, 최초 실패 마커, 원본 s6_table_rgb.ppm의 raw RGB SHA를 재확인해야 합니다.
- 이전 S5/S6 기능/지도/Collision Monitor는 변경하지 않았으며, S7 인수 전 main 병합은 금지합니다.

## 5. 빈 테이블 음성 반례
실제 빈 테이블의 독립 Gazebo L2는 CI #45112942260에서 첫 TABLE_3 Action 성공, 진짜 RGB 3프레임, NOT_STACKED, 복귀 Goal 0건으로 PASS했습니다. 강사 S7 원샷은 안전한 양성 stacked 시나리오 하나만 실행합니다.

음성 증거는 generated/s7/empty_vision_evidence.json, generated/s7/s6_table_rgb.ppm, logs/s7_empty_console.log 입니다. 이미지 누락 또는 모델 불확실성의 UNKNOWN은 안전 HOLD이고 자동 복귀 금지입니다.

## 6. 최종 평가와 개발 보고서
최종 기능 L3 PASS는 동일 PIN + 사전검사 + TABLE_3/RETURN 실증 + 실제 RGB/AI + Collision Monitor STOP + FIRST_FAILED_MARKER=NONE을 모두 충족할 때만 선언합니다. L2 CI로 현장 L3를 대신하지 않습니다. GUI 육안 및 RTF 90%는 별도 비차단 과제입니다.

교육 산출물: docs/s7/INSTRUCTOR_DEMO_GUIDE_KO.md, docs/s7/STUDENT_LAB_GUIDE_KO.md, docs/s7/INSTRUCTOR_SOLUTIONS_KO.md, docs/reports/s7/ 개발 사이클별 교육 보고서.
