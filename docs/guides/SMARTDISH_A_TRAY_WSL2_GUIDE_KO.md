# SmartDish A-11~A-13 — WSL2 GUI 기본 원샷 실습 가이드

> 이 가이드는 새 트레이 물리 데이터 생산 경로만 다룹니다. 기존 AI OFF S7/Nav2/E 전체 인수 경로는 실행·변경하지 않습니다.

## 1. 환경

Ubuntu 24.04 WSL2 + WSLg, ROS 2 Jazzy, Gazebo Harmonic, `ros_gz_bridge`, `colcon`, Pillow·PyYAML. GPU/WSLg 환경은 실 Gazebo 영상으로 확인합니다. 설치 불완전 시 기존 개발 환경을 강제로 수정하거나 GUI 실패를 가짜 이미지로 대체하지 않습니다.

- 새 작업 디렉터리: `~/samsung_AXI_A_TRAY` — 기존 `~/samsung_AXI_E`, `~/samsung_AXI_A` 보존
- 신규 브랜치: `feat/smartdish-a-tray-camera` (S7 보호 `main@cc66b66a`에서 분기)
- 소스 PIN을 지정하지 않거나 SHA가 달라진 경우 **No-GOAL FAIL_FAST**입니다.
- 출고 원샷: `scripts/smartdish_a_tray_bootstrap.sh` 및 `scripts/smartdish_a_tray_one_shot.sh`, 모두 GUI 기본.

## 2. 사용법

GitHub Draft PR #미지정의 최신 검증 SHA를 **정확히** 확인해 적용합니다. 실제 사용자 실행 안내의 PIN은 A-13 최종 CI가 확인된 후 별도로 제공됩니다.

```bash
PIN=<FINAL_VERIFIED_SHA>
curl -fsSLo "$HOME/smartdish_a_tray_bootstrap.sh" \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_a_tray_bootstrap.sh" \
  && SMARTDISH_A_TRAY_SOURCE_SHA="$PIN" \
    bash "$HOME/smartdish_a_tray_bootstrap.sh"
```

위 명령은 **문서 설계 형태**입니다. 현재 미지정 PIN을 문자 그대로 실행할 수 없습니다. 실제 출고 시 반드시 커밋 SHA를 채운 완성 명령을 안내합니다.

기본: `batch --gui` (4개). 후속 선택:
```bash
# 기존 전용 Git 클론이 있으면서 PIN이 정확할 때
SMARTDISH_A_TRAY_SOURCE_SHA="$PIN" bash scripts/smartdish_a_tray_one_shot.sh demo --gui
SMARTDISH_A_TRAY_SOURCE_SHA="$PIN" bash scripts/smartdish_a_tray_one_shot.sh single --headless
SMARTDISH_A_TRAY_SOURCE_SHA="$PIN" bash scripts/smartdish_a_tray_one_shot.sh batch --headless
```

## 3. 시각적으로 기대할 내용

독립 `smartdish_tray` world의 사각 플랫폼·각 Scenario의 2~3개 색상별 원통형 식기, overhead RGB 카메라. `ST-01`/ `ST-02`는 정렬 적재 후보, `UN-01`/ `UN-02`는 지지면 이탈·기울기 후보. **실제 결과는 물리 로그로만 판단**하며 시나리오 명칭이 정답은 아닙니다. `--headless`를 사용해도 이미지 렌더링 증거가 없으면 PASS 금지합니다.

카메라 신호 확인:
```bash
source /opt/ros/jazzy/setup.bash
ros2 topic info -v /smartdish/tray/image_raw
ros2 topic hz /smartdish/tray/image_raw
ros2 topic info -v /smartdish/tray/poses
```

## 4. 결과 파일 읽는 순서

```text
generated/smartdish_tray/run_<UTC>_<PID>/
    source_manifest.json, summary.json, SHA256SUMS
    trial_0001..0004/
       scenario.sdf, scenario.scenario.json
       tray_rgb.png, capture_metadata.json
       initial_state.json
       physics_observations.jsonl
       final_state.json, trial_summary.json
    logs/<trial>_gazebo.log, <trial>_bridge.log, <trial>_gui.log
    smartdish_a_tray_evidence.tar.gz
```

`tray_rgb.png`는 모델용 입력 후보, `physics_observations.jsonl`는 **서로 다른 실제 Gazebo 물리 근거**입니다. `capture_stamp_ns <= observation_start_ns < observation_end_ns`, 프레임 3개 이상 새 타임스탬프, Pose 연속 계측 및 두 SHA 검증이 모두 충족되어야 합니다.

## 5. 예상 완료 메시지(실제 조건 충족 후만)

```text
SMARTDISH_A_TRAY_SOURCE_PIN_OK
SMARTDISH_A_TRAY_CAMERA_LIVE_PASS trial=...
SMARTDISH_A_TRAY_RGB_CAPTURE_PASS trial=...
SMARTDISH_A_TRAY_PHYSICS_OBSERVATION_PASS
SMARTDISH_A_TRAY_EVIDENCE_EXPORT_PASS
SMARTDISH_A_TRAY_WSL2_L3_PASS
```

첫 오류 `SMARTDISH_A_TRAY_FIRST_FAILURE` 또는 `...BOOTSTRAP_BLOCKED`이면 원본을 보존하고 FAIL로 인계합니다. 실제 사용자 WSL2에서 4개 시험이 성공한 증거가 오기 전까지 L3는 **NOT_RUN**입니다.

## 6. 중복 실패·청소 원칙

동일 trial ID, 기존 checkout 변경, 불량 PNG/physics SHA, t1 사후 영상 또는 누락 Pose를 자동 고치거나 덮어쓰지 않습니다. 새 run_id로 재시험합니다. 실행기가 만든 Gazebo/bridge/gui PID만 종료하며 모든 시스템의 `gz sim`에 대해 `pkill`을 하지 않습니다.

## 7. B/C 실제 수집 연결

[A Tray B/C 인계서](../handoff/A_TRAY_BC_HANDOFF_KO.md)를 따르십시오. `ST-01`을 바로 `STABLE`로 등록하지 않습니다. B 사람이 실제 동적 Pose와 RGB 상태를 검토한 뒤 기존 `collect_tableware.py`를 사용합니다. 그 후 C는 B 승인된 분할 데이터로 학습하고 ROS 입력을 구독합니다.
