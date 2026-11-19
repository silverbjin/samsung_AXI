# GPU-01 — SAMSUNGAXI 전용 WSLg GPU 경로 장애 진단
- 작성: 2026-11-19 KST
- 상태: **OPEN**. D3D12 실기 검증 및 Gazebo RTF 개선 결과는 NOT_RUN
- 범위: 이 프로젝트 PC 한 대만. 다른 AXIA 프로젝트 하드웨어 수치 사용 금지.

## 최초 관찰
현장 Gazebo GUI에서 레스토랑 World/로봇 렌더링 성공, RTF 61.95%. Windows Intel Core i7-11700F 8코어 16스레드, RAM 15.86GiB, RTX 3060 8GiB. WSL2 Ubuntu 24.04.5 LTS, /dev/dxg 존재, nvidia-smi GPU 조회 성공. 그러나 glxinfo -B 기본 OpenGL renderer는 llvmpipe, Accelerated no. MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA 단독 비교도 llvmpipe. Gazebo 프로세스 두 개 CPU 점유 343%와 238%로 높음.

## 시점 비교
첫 검사(15:42 KST): WSL MemTotal 7.7GiB, available 5.7GiB, swap 2GiB (미사용), .wslconfig 검출 안 됨. 둘째 검사(16:07 KST): MemTotal 15.48GiB, available 14.86GiB, swap 8GiB, memory=16GB. 둘째 시점에는 Gazebo 프로세스 미포착. **서로 다른 부하이므로 메모리 변경이 RTF를 개선했다고 볼 수 없음**. memory=16GB는 VM 상한이며 항상 전체 점유를 뜻하지 않음.

## 가설과 단일 검증
1순위 가설: Mesa Gallium d3d12 기본 드라이버 선택 실패로 CPU llvmpipe로 fallback. 공식 Gazebo Issue #2670과 Microsoft WSLg Issue #1332에 동일 현상 및 GALLIUM_DRIVER=d3d12 우회 사례가 있음. 다만 현재 PC에서는 근본 원인 확정 전.

독립 GLX 비교: 기본 / GALLIUM_DRIVER=d3d12 / GALLIUM_DRIVER=d3d12+MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA. 별도 프로세스 진단기 scripts/samsungaxi_gpu_route_probe.sh. **실제 결과 필요.** 성공 시에도 Gazebo Ogre2 호환과 Scan/RGB-D, 동일 장면 RTF를 따로 검증.

RAM 16GB PC에 기존 문서의 32GB/20GB RAM 권장을 적용하지 않음. Windows/WSL 경합을 피하기 위한 memory=10GB/swap=4GB는 추후 **수동 검토 후보**일 뿐; 자동 수정 금지. PPA 추가, 드라이버/ROS 재설치 금지.

## 판정과 교육 포인트
S1 렌더링 PASS(사용자 제공), WSLg GLX GPU 가속 실패 확인, 실기 d3d12·RTF 개선·SLAM 지도 NOT_RUN. GPU가 nvidia-smi로 보이는 사실은 Gazebo의 GPU 렌더링 근거가 아니므로 렌더러와 센서/RTF 각각 따로 측정.

## 참고
- https://github.com/gazebosim/gz-sim/issues/2670
- https://github.com/microsoft/wslg/issues/1332
- https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg
- https://learn.microsoft.com/en-us/windows/wsl/wsl-config
