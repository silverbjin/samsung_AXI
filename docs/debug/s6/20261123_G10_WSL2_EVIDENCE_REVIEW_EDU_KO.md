# S6 G10 — 강사 WSL2 원본 ZIP 현장 인수 분석 및 main 병합 게이트 리뷰

- 검토일: 2026-11-23
- 리뷰 대상: S6 Vision AI 요청형 RGB + Nav2 배달/복귀 + LiDAR Collision Monitor
- 검수 원칙: 오류 없는 사실만 PASS; 최종 릴리스 **정확한 런타임 SHA**의 WSL2 GUI/기능 실증 전에는 main 병합 금지
- 관련 PR: [#30](https://github.com/silverbjin/samsung_AXI/pull/30), [#31](https://github.com/silverbjin/samsung_AXI/pull/31)
- 릴리스 실행기 원본 고정 SHA: `6fc1ac685858cb075e56514e03f72ad3a504fd87`
- 해당 실행기 내부의 검증 런타임 SHA: `9d402a991d1ee0a1c46027abe91a55266b69d9bd`
- 비교 기준: [Gazebo L2 #45106929216](https://github.com/silverbjin/samsung_AXI/actions/runs/45106929216) 기능 PASS
- 최종 현장 제출본의 **실행 SHA는 별도의 이전 버전** `611ac7b9edf5aa275dc4dbbde86530a573165a77`임.

## 1. 원본 무결성과 판정

| 자료 | ZIP SHA256 | 압축 내용 | 판정 |
|---|---|---|---|
| `samsungaxi_gui_20261123T034803Z-453.zip` | `dcc2dad477f2233e13a377998fa5beb272e46a3b3946ae8a00742688b001f4e7` | NO_GOAL status, run log | `PREFLIGHT_PASS_NO_GOAL` |
| `samsungaxi_gui_20261123T034804Z-490.zip` | `9a9cd75a2fa2c1e716c35d24ad78453b3bfcb2272db3b6dec7bc2c583c162485` | 실제 Goal, Vision JSON, 원본 PPM, GUI lifecycle, RTF | **기능 PASS / 최종 L3 HOLD** |

두 ZIP의 CRC 검사 `testzip()==None`. 비공개 현장 로그 ZIP은 공개 GitHub에 게시하지 않고 SHA256/요약 지표만 보존.

### NO_GOAL 사전검사

```text
PIN=611ac7b9edf5aa275dc4dbbde86530a573165a77
RUN_RC=0
GOAL_AUTHORIZED=FALSE
GOAL_SENT=FALSE
FIRST_FAILED_MARKER=NONE
VERDICT=PREFLIGHT_PASS_NO_GOAL
```

### 실제 라이브 결과

```text
PIN=611ac7b9edf5aa275dc4dbbde86530a573165a77
RUN_RC=130             # 성공 로그 출력 후 운영자가 Ctrl+C 종료
GOAL_AUTHORIZED=TRUE
GOAL_SENT=TRUE
FIRST_FAILED_MARKER=NONE
VERDICT=GUI_VISUAL_REVIEW_REQUIRED
WSL2_GUI_ACCEPTED=NOT_RUN_UNTIL_HUMAN_VISUAL_CHECK
```

## 2. 실제 기능 GREEN 검증

| 게이트 | 원본 근거 | 결과 |
|---|---|---|
| 원본 map | SHA256 `aedaed8f89e703f33ef22f9cf0c9d8f77b11763157d6e3a61c839a58fe871f00` | PASS |
| TABLE_3 | Action `status=4` / 실제 odom `5.112m` / AMCL 오차 `0.214m` | PASS |
| 도착 후 물리 정지 | Odom 속도 표본이 0까지 감속 후 최신 영상 요청 | PASS |
| Vision AI | 실제 RGB 3프레임, 320×240, `STACKED`, confidence `0.6652` | PASS (고정 fixture) |
| Vision 이미지 원본 무결성 | PPM의 **230400-byte raw RGB payload** SHA256 `a9c986358f25ab59a45c382c278e190135f92edcd42aa0e4b123445f2b498da0` = JSON 예측 이미지 해시 | PASS |
| PICKUP_RETURN | Action `status=4` / odom `5.025m` / AMCL 오차 `0.199m` | PASS |
| NORMAL / SOUP | 실제 p75 `0.23m/s` / `0.11m/s` | PASS |
| LiDAR 실제 STOP | Forward STOP polygon 29점, upstream positive 0.08m/s 관측, CM STOP, downstream 50표본 최대 `0`, 실제 정지 Odom 이동 `0m` | PASS |
| S6 통합 마커 | `S6_VISION_REAL_GAZEBO_L2_INTEGRATED_PASS` | PASS (이번 구버전 SHA 현장 기능) |

기술 참고: 중첩된 `s6_vision.return_goal_sent=false`는 **Vision 시점의 snapshot**입니다. 원본 런타임은 이후 `goto(PICKUP_RETURN)`에서 바깥쪽 `s6_return_goal_sent=true`를 기록하고 Action 성공/통합 마커를 출력합니다. 이 상태 필드 차이를 곧바로 미발행 오류로 오진하지 않습니다.

## 3. RED/HOLD — 왜 최종 `main` 병합 조건이 불충족인가?

1. **정확한 SHA 불일치**. 사용자가 현장 검수한 것은 `611ac7...`, 최종 배포 목표는 G09 Nav2 초기화 및 FollowPath 응답 개선이 포함된 `9d402a...`입니다. `9d402a...`은 CI에서 L0/L1/L2 PASS지만 강사 NVIDIA WSLg L3 현장 증거는 없습니다.
2. **GUI 육안 검증 미기록**. ZIP의 자동 상태는 `WSL2_GUI_ACCEPTED=NOT_RUN_UNTIL_HUMAN_VISUAL_CHECK`입니다. Gazebo 프로세스가 정상 실행되고 RViz OpenGL 4.5 초기화 로그가 있어도 실제 화면에 로봇/지도/경로가 보였는지까지 증명하지 못합니다.
3. **GUI / 종료 과정의 유의 로그**. `gui_process_lifecycle.txt`에는 RViz GLSL 지도 셰이더 연결 오류(`active samplers with a different type refer to the same texture image unit`)가 있고 Ctrl+C 정리 중 `[rviz2-21] terminate called without an active exception`이 기록됩니다. Gazebo GUI의 이전 `Failed to create OpenGL context`는 이번 압축된 실행 로그에서는 재발하지 않았으나, **RViz GUI/종료의 오류 없음**을 판정할 수 없습니다.
4. **RTF 목표 HOLD**. `s5_perf_summary.json`의 moving median `0.5372`(n=131), all median `0.4752`(n=643). RTF≥0.90 목표는 사용자 지시에 따라 별도 HOLD이며 이번 병합을 차단하는 항목은 아닙니다.
5. **RUN_RC=130 오해 금지**. 이는 성공 이후 사용자 SIGINT 종료와 일치하지만 자동으로 graceful shutdown PASS를 뜻하지 않습니다.

따라서 이 세션의 **S6 배달·Vision·복귀·STOP 기능은 PASS**로 보존하고, **GUI 육안·종료 안전·최종 SHA 일치 인수는 HOLD**입니다. `main` 병합은 실행하지 않습니다.

## 4. 주니어 교육용 RED→GREEN 체크포인트

- **문제 정의**: 동일 기능 성공이 곧 동일 배포 버전 성공인가? → 아닙니다. 정확한 SHA를 추적해야 합니다.
- **데이터 파이프라인**: ROS 2 Action Goal → Odom 정지 → ROS Image payload → 모델 STACKED → 새 Action Goal → LiDAR STOP → cmd_vel zero.
- **실습 A**: ZIP `status.txt`의 `PIN`과 GitHub 실행기의 `SOURCE_SHA`를 비교하는 검증기를 작성해 보십시오.
- **실습 B**: PPM의 헤더가 아닌 raw RGB payload의 SHA256을 JSON과 비교하십시오.
- **실습 C**: `RUN_RC=130`과 `FIRST_FAILED_MARKER=NONE`이 함께 있을 때 실제 Action/STOP 증거를 읽어 최종 판정 근거를 설명하십시오.
- **실습 D**: RViz shader-link 오류가 전체 Nav2 주행 실패인지, GUI 표시만의 잠재적 문제인지를 분리하십시오.
- **평가 기준**: RED(최종 SHA와 현장 불일치) → GREEN(같은 SHA G09 새 WSL2 1회 실증 + 실제 GUI 육안 확인 + ZIP/Payload SHA) → REVIEW → final main merge.

## 5. 다음 1회 인수 및 완료 게이트

- 고정 공개 실행기: [`scripts/samsungaxi_s6_wslg_reaccept_once.sh` at `6fc1ac68...`](https://github.com/silverbjin/samsung_AXI/blob/6fc1ac685858cb075e56514e03f72ad3a504fd87/scripts/samsungaxi_s6_wslg_reaccept_once.sh)
- 내부 고정 소스 SHA: `9d402a991d1ee0a1c46027abe91a55266b69d9bd`.
- 실행: `bash --self-test` → `PREFLIGHT_PASS_NO_GOAL` → Gazebo/RViz 실제 화면 확인 → TTY `YES-S5-LIVE-GOALS` → TABLE_3/실제 RGB `STACKED`/PICKUP_RETURN/STOP → 최신 ZIP 보존.
- GUI 오류·RTF는 분리: 실제 CGI/GPU 전반 렌더링 및 GUI 육안 확인을 수행하되 RTF 목표는 HOLD.
- 고정 G09 현장 ZIP과 GUI 확인이 PASS이고 중대한 오류가 없을 때에만 PR #31 → PR #30 순서로 main 병합.
