# OWNER-RTF — WSLg GPU 가속 경로 + 실제 Gazebo RTF 계측 출고

- 기준: 사용자 Gazebo/RViz 동시 GUI에서 RTF 약 60~70%, 90% 이상 목표. 강사 WSL2에서 직접 측정 전까지 **RTF_90_PERCENT=NOT_VERIFIED**.
- 재사용: 기존 `scripts/samsungaxi_wsl2_gui_acceptance_once.sh` NO_GOAL, 개발 중복 금지. 지도 S2-MAP-03 81.33%와 자동 AMCL 초깃값의 기존 CI GREEN 보존.
- 확인된 선행 현장 근거: RTX 3060 환경의 기본 GLX `llvmpipe` / `Accelerated: no`, 별도 `GALLIUM_DRIVER=d3d12` GLX는 `D3D12 (NVIDIA RTX 3060)` / `Accelerated: yes` (이전 GPU-01 보고서).
- 변경: GUI 원샷 자식 프로세스 한정 `GALLIUM_DRIVER=d3d12`, `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA`, `LIBGL_ALWAYS_SOFTWARE` 해제. `glxinfo -B`에서 NVIDIA D3D12/Accelerated=yes일 때만 선택, 실패하면 현재 환경 유지 및 상태를 기록. OS/driver/.wslconfig 전역 변경 없음.
- 실제 세션 RTF: Gazebo Harmonic `/world/restaurant/stats`의 `real_time_factor` 최대 100개 실제 표본 수집, 중앙값/하위 10%/목표 0.90 충족 여부를 단일 ZIP에 보존. 표본 부족 시 `INSUFFICIENT_SAMPLES`. GUI 종료는 Ctrl+C.
- [전용 공개 CI #44668294037](https://github.com/silverbjin/samsung_AXI/actions/runs/44668294037): L0 Bash 문법·Self-test·계약 PASS. Xvfb/llvmpipe CI를 WSLg RTX GPU나 90% RTF 증거로 승격하지 않음.
- 공식 근거: https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg 및 https://gazebosim.org/docs/harmonic/sdf_worlds/.
- 최종 판정: `OWNER_RTF_SOURCE_L0_PASS`, `OWNER_RTF_WSL2_GUI_L3=NOT_RUN`, `RTF_GE_90_PERCENT=NOT_VERIFIED`.
- 다음 Owner 1회 실행에서 ZIP의 `gpu_probe.txt`, `rtf_report.txt`, `rtf_samples.txt`, `/scan`·`/odom` 및 ROS 진단을 교차 확인. GPU 사용과 RTF 목표가 동시 성립하는 경우에만 최종 승인.
