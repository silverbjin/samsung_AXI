# A14-07 WSL2 — 실제 Contact Sensor 양성 교정 원샷

## 목적과 범위

A14-P0 GT 후보가 `UNKNOWN/HOLD`로 남는 이유인 **Contact 미관측 채널**을 별도 작은 Gazebo 시뮬레이션에서 실제 양성 충돌로 시험합니다. 기존 A13 4/4와 A14 ST-02/UN-01을 다시 실행하지 않습니다. GT 사람 승인(0건) 및 기존 AI OFF 기능을 변경하지 않습니다.

## 한 번 복사·붙여넣기

Cloud 검증 완료 후 게시된 **정확한 immutable SHA**를 사용합니다.

```bash
PIN=<A14_CAL_CI_VERIFIED_40_HEX_SHA>
curl -fsSLo "$HOME/a14_contact_calibration_bootstrap.sh" \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/a14_contact_calibration_bootstrap.sh" \
  && SMARTDISH_A14_SOURCE_SHA="$PIN" \
  bash "$HOME/a14_contact_calibration_bootstrap.sh" --gui
```

- 기본 GUI: 실제 WSLg/Qt 컨텍스트 preflight만 수행한 후 Contact 교정 월드는 headless 진행. 사용자의 `GALLIUM_DRIVER=d3d12`, `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` 유지.
- 첫 검수 전에는 이 명령을 실행하지 말고 해당 SHA의 GitHub L0/L2 PASS를 먼저 확인하십시오.
- 인수 게이트의 사람 시각 검수는 운영자가 별도 수행하며 픽셀 QA는 자동 게이트에서 제외합니다.
- 교정 스크립트는 파일을 지우거나 기존 Gazebo 작업에 전역 종료를 보내지 않습니다.

## 증거 아카이브

성공·실패 모두:
`~/samsung_AXI_A14_PHYSICS/generated/smartdish_a14/contact_calibration_*/a14_contact_calibration_evidence.tar.gz`
`~/samsung_AXI_A14_PHYSICS/generated/smartdish_a14/contact_calibration_*/a14_contact_calibration_evidence.tar.gz.sha256`

`calibration_result.json`에 트레이와 바닥 센서의 실제 충돌 이름·ID, 양수 simulation stamp, /clock 진행, source SHA, 세션 프로세스 정리와 최초 실패를 기록합니다.

## 해석 가이드

`A14_CAL_REAL_GAZEBO_POSITIVE_CONTROL_PASS` 또는 `A14_CAL_POSITIVE_CONTROL_PASS_PRODUCTION_GT_STILL_HOLD`는 **독립 양성 교정 성공**만 의미합니다. 기존 ST-02/UN-01의 침묵 센서 채널이 건강한 상태였다는 증거나 전체 데이터셋 GT PASS는 아닙니다. 원본 `UNKNOWN/REVIEW_REQUIRED` 상태와 사람 승인 0건은 유지합니다.

오류 시 동일 시험을 15회 반복하지 말고 TAR + SHA256 sidecar 하나를 전달합니다.
