# Samsung AXI — WSL2/WSLg 성능·GPU 점검 (강사 PC)

**근거:** 2026-11-19 강사 GUI 사진에서 RTF 61.95%와 World/모델 렌더링 성공. 등록 RGB-D/LiDAR 브리지는 생성됐으나, 이 로그만으로 WSL2 GPU/메모리 병목을 확정할 수는 없음.

## 진단 먼저 (Gazebo 실행 중 Ubuntu 터미널 두 번째 창)
```bash
cd ~/samsung_AXI
bash scripts/wsl2_perf_doctor.sh
RESTAURANT_COMPARE_NVIDIA=1 bash scripts/wsl2_perf_doctor.sh  # NVIDIA 장착 시만
```
출력은 `logs/wsl2_perf_*.txt`. 이 스크립트는 WSL/Windows 설정을 바꾸지 않음.

- `DXG_DEVICE=present`와 `OpenGL renderer string: D3D12 (...)`: WSLg GPU 그래픽 경로의 좋은 징후. **NVIDIA GPU를 쓴다는 단정은 금지.**
- `llvmpipe` / `softpipe`: 소프트웨어 렌더링 의심. 그래픽 드라이버·WSL 버전 및 `LIBGL_ALWAYS_SOFTWARE` 환경 검사.
- `nvidia-smi`가 성공해도 Gazebo Ogre2가 NVIDIA로 렌더링한다는 증거는 아님. `glxinfo -B`의 실제 renderer 확인 필요.
- `free -h`의 `available`이 여유 있으면 메모리 상한만 늘려도 RTF가 개선된다고 말할 수 없음.
- 엔터프라이즈 보호/다중 WSL 인스턴스가 있을 수 있으므로 `.wslconfig` 원본 덮어쓰기·`wsl --shutdown` 자동 실행 금지.

## RAM 32 GB인 Windows 호스트 권장 검토
Microsoft WSL2 기본 VM 메모리 제한은 Windows RAM의 50%(별도 설정 없으면 약 16 GB). WSL에서 실제 제한과 메모리 사용량부터 확인한 뒤 필요할 때만 Windows PowerShell에서 **백업 후** `$env:USERPROFILE\.wslconfig`를 편집.

```ini
[wsl2]
memory=20GB
swap=8GB
guiApplications=true
```
*이미 존재하는 파일의 다른 항목은 보존*. 적용하려면 모든 WSL 세션 종료 후 **Windows PowerShell**의 `wsl --shutdown` (실행 중 프로세스 전부 종료됨), 이후 WSL Ubuntu 재시작. CPU `processors`는 현장 CPU 코어 수·부하 확인 전 설정하지 않음.

## GPU 선택 확인 (옵션)
WSLg Mesa D3D12는 `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA`를 사용하여 특정 어댑터를 선택할 수 있음. 실제 `glxinfo -B` 출력에 D3D12(NVIDIA)가 보인 경우에만 **새 터미널/새 Gazebo 세션에 한정**해 비교:
```bash
MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA glxinfo -B
# 유효한 D3D12 NVIDIA 렌더러인지 확인한 후에만:
MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA bash scripts/restaurant_demo.sh world
```
`llvmpipe`로 떨어지면 적용하지 말 것. `LIBGL_ALWAYS_SOFTWARE=1`이나 `GALLIUM_DRIVER=llvmpipe`를 강사 GUI에 설정하지 말 것. CI 헤드리스의 Mesa 설정과 WSLg GUI는 별도 환경임.

## S1 최소 성능 변경
원본 Waffle Pi SDF는 불변. 생성된 사본에서 (1) 별도 기본 RGB 30Hz 센서를 제외하고 (2) LiDAR 광선 표시만 끄고, (3) 등록 RGB-D 5Hz / LiDAR 10Hz / DiffDrive / Bridge를 유지. 기존 `/camera/image_raw`는 더 이상 기본 출력을 요구하지 않음; RGB는 `/restaurant/rgbd/image`로 관찰.

**후속 확인:** 최종 RTF를 같은 화면 조건으로 한 번 관찰하고 `/scan`, `/restaurant/rgbd/image`, `/restaurant/rgbd/depth_image`, `/odom`의 실제 수신을 확인. RTF 상승 수치가 없으면 최적화 성공률을 주장하지 않음.

## S2로 진행 — 지도 생성은 NO_GOAL 별도 단계
```bash
cd ~/samsung_AXI
bash scripts/restaurant_demo.sh mapping
```
SLAM Toolbox가 실행되고 `/map`가 수신되는지 두 번째 터미널에서 확인. 등록 RGB-D와 Gazebo 안전 측정은 유지. 수동 키보드 주행은 로봇/가구 충돌을 피하며 운영자가 감독. 실제 탐색 지도 저장:
```bash
source /opt/ros/jazzy/setup.bash
source ~/samsung_AXI/install/setup.bash
export ROS_DOMAIN_ID=58 GZ_PARTITION=restaurant_mvp
ros2 topic echo /map --once --field info
mkdir -p ~/samsung_AXI/maps
ros2 run nav2_map_server map_saver_cli -f ~/samsung_AXI/maps/restaurant_map
ls -l ~/samsung_AXI/maps/restaurant_map.yaml ~/samsung_AXI/maps/restaurant_map.pgm
```
**저장 파일이 있다는 사실만으로 유효한 전체 레스토랑 지도·AMCL 인수를 승인하지 않음.**
