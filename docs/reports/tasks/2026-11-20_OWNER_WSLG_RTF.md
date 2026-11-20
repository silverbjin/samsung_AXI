# OWNER-RTF — WSLg D3D12 GPU 경로 및 RTF 실측 준비
- 목적: 강사 WSL2에서 관찰된 Gazebo RTF 60–70% (첨부 화면은 약 76.78%)를 90% 이상 목표로 개선.
- 과거 진단: 삼성 AXI 현장 `llvmpipe / Accelerated: no`, 국소 `GALLIUM_DRIVER=d3d12` 비교에서 `D3D12 (NVIDIA GeForce RTX 3060) / Accelerated: yes` 확인. 단 이것은 GLX 경로의 증거이며 Gazebo Ogre2 FPS/RTF 보장은 아님.
- 재사용: 기존 `scripts/samsungaxi_wsl2_gui_acceptance_once.sh`는 해당 환경에서 GPU 경로를 GPU 실제 프로브가 PASS일 때에만 **그 프로세스와 자식**에 적용. 시스템 .wslconfig/메사/드라이버 변경 없음, 로봇/SLAM/Nav2/지도 정책도 변경 없음.
- 원샷이 동일한 실제 Gazebo 세션에서 `gz topic -e -t /world/restaurant/stats`로 real_time_factor를 관찰하여 표본 수/중앙값/10퍼센타일/90% 기준 결과를 **기존 단일 진단 ZIP**에 보존.
- 안전 경계: glxinfo 미설치 또는 GPU 속성 미확인이면 강제 적용하지 않음. 표본 5개 미만이면 `INSUFFICIENT_SAMPLES`. GPU 가속 PASS와 RTF >=90% PASS를 혼동하지 않음.
- 공개 CI 정적: [Run #44668294037](https://github.com/silverbjin/samsung_AXI/actions/runs/44668294037) L0 PASS (원샷 Bash -n, --self-test, pytest).
- **실제 강사 WSL2/WSLg 최종 RTF >=90% 및 GUI 시각 인수: NOT_RUN**. CI에 WSLg RTX3060 실제 측정 환경이 없으므로 과도한 완료 주장 금지.
- 실행: 최신 main의 원샷 파일을 commit SHA 고정으로 다운로드, `SAMSUNG_AXI_GUI_PIN`을 같은 SHA로 지정해 실행. 종료 Ctrl+C 뒤 `~/samsungaxi_gui_evidence/samsungaxi_gui_*.zip` 하나를 전송. ZIP 내부 `gpu_probe.txt`, `rtf_report.txt`, `rtf_samples.txt`, `run.log`, `environment.txt`로 판정.
- 해설: GPU 경로가 실제 원인이라면 개선할 수 있으나, Gazebo 센서/CPU/GUI/WSLg 복합 요인이 남으면 목표 달성 전 추가 원인 분리가 필요. 실측 없는 물리 성능 PASS 승격 금지.
