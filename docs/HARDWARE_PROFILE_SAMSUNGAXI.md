# SAMSUNGAXI 전용 PC 성능 프로파일 진단

**범위:** 이 프로젝트의 강사 Windows 호스트와 WSL2 Ubuntu 24.04에 한정합니다. 이전 AXIA·타 프로젝트 PC의 CPU/RAM/GPU 사양·튜닝값을 **절대 복사 적용하지 않습니다**.

## 실행 (강사 WSL2 Ubuntu, sudo 불필요)

```bash
cd ~/samsung_AXI
bash scripts/samsungaxi_hw_probe.sh
# WSLg GPU 어댑터별 OpenGL 후보를 *별도 프로세스*로 비교하려면:
bash scripts/samsungaxi_hw_probe.sh --compare-gpu
# 실제 Gazebo 실행 중 추가 정보(선택):
bash scripts/samsungaxi_hw_probe.sh --gazebo-stats
```

출력 예: `logs/hardware/<UTC timestamp>/samsungaxi_hardware.txt` 및 `samsungaxi_hardware.json`. 이 폴더는 Git 관리 대상이 아닙니다. 로그에 CPU/GPU 모델명이 포함되므로 외부 공개 전 확인하십시오. 지정 경로: `--output-dir /tmp/samsungaxi-hardware`.

**진단 범위:** Windows CIM의 호스트 CPU 모델·물리 코어/논리 프로세서 수·RAM·GPU 모델/드라이버, WSL2가 실제로 사용할 수 있는 논리 CPU·메모리 가용량/Swap/cgroup, WSLg `/dev/dxg`·OpenGL 렌더러, NVIDIA 관리 도구 유무, `.wslconfig`의 일부 성능 관련 설정입니다. 계정·IP·시리얼·호스트 이름은 수집하지 않습니다. Windows PowerShell 상호운용이 꺼져 있으면 Windows 값은 `UNKNOWN`으로 남습니다.

**해석:** `glxinfo -B`의 `D3D12 (GPU 이름)`은 *그 검사 프로세스*의 OpenGL 경로를 알려 주며 Gazebo Ogre2가 반드시 같은 GPU를 사용한다는 뜻은 아닙니다. `llvmpipe`/`softpipe`는 소프트웨어 렌더링 징후, `nvidia-smi` 성공은 GPU 노출 증거입니다. 실제 Gazebo 로그의 Ogre2/OpenGL 렌더러와 비교해야 합니다.

## 최적화 의사결정 계약

1. **CPU:** Windows CPU 모델/논리 수 vs WSL 가용 코어 수 및 Gazebo 프로세스 CPU 이용률을 비교한 뒤 병목 여부를 판단합니다. `processors=` 임의 제한 금지.
2. **RAM:** Windows 물리 메모리와 WSL 실제 `MemTotal/MemAvailable`, Swap, cgroup 제한을 비교합니다. *이 PC의 RAM 크기가 아직 미측정이므로* `memory=20GB` 등 기존 PC 수치를 사용하지 않습니다. 메모리 여유가 있으면 RTF 저하를 무조건 RAM 부족으로 돌리지 않습니다.
3. **GPU:** Windows GPU 목록, `/dev/dxg`, 실제 `glxinfo -B` 렌더러, Gazebo Ogre2 렌더링 로그를 확인합니다. 선택적 `--compare-gpu`는 검사 명령에만 어댑터 문자열을 적용하며 영구 GPU 설정을 바꾸지 않습니다.
4. **RTF:** 같은 장면·같은 카메라·같은 센서 구성에서 최적화 전후 RTF를 **한 번 비교**하고, LiDAR·Depth·Odom 실제 토픽이 유지되는지 확인합니다. 숫자 목표를 MVP 완료 기준으로 추가하지 않습니다.

Windows WSL2 `.wslconfig` 변경이 필요할 때는 실측 결과를 검토한 후 Windows PowerShell에서 해당 **SAMSUNGAXI PC**만 백업·수정합니다. 진단 도구는 `.wslconfig`·GPU 드라이버·ROS·Gazebo 설정을 수정하거나 `wsl --shutdown`을 실행하지 않습니다.

참고: [Microsoft WSL 구성](https://learn.microsoft.com/en-us/windows/wsl/wsl-config) · [WSLg GPU 선택](https://github.com/microsoft/wslg/wiki/GPU-selection-in-WSLg).