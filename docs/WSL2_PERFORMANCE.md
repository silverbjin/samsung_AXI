# SAMSUNGAXI 전용 WSL2 GPU·메모리 운영
실제 이 PC: Intel i7-11700F 8C/16T, Windows RAM 15.86GiB, RTX3060 8GiB.
WSL2 초기 Memory 7.7GiB, 이후 .wslconfig memory=16GB swap=8GB; VM 상한과 실제 점유량 구별.
기본 OpenGL llvmpipe (no), GALLIUM_DRIVER=d3d12 환경의 OpenGL D3D12 NVIDIA (yes) 실측.
동일 WSL2 Gazebo S1 GUI 화면 RTF 61.95% 및 D3D12 적용 후 99.89% 각 단일 시점. 지속 평균으로 판정하지 않음.

시연: cd ~/samsung_AXI && bash scripts/samsungaxi_d3d12_evidence_once.sh world
진단: bash scripts/samsungaxi_hw_probe.sh ; bash scripts/wsl2_perf_doctor.sh
최적화: 생성 Waffle Pi SDF 사본에서만 기존 RGB 30Hz 센서 제거, RGB-D 5Hz 유지, LiDAR 광선 표시만 off (/scan 10Hz 유지).
GLX 장치 인식만으로 Gazebo Ogre2 사용이 확인되지는 않으므로 Gazebo 로그/센서/RTF를 별도로 확인.
다른 PC의 memory=20GB 권장치를 이 16GB Windows 호스트에 적용하지 않음. 사용자 확인 없이 .wslconfig/드라이버 변경 금지.
