# SAMSUNGAXI 전용 하드웨어 기준선 (2026-11-19)
| 항목 | 이 프로젝트 PC |
|---|---|
| CPU | Intel Core i7-11700F (8C/16T) |
| Windows RAM | 15.86 GiB |
| GPU | NVIDIA RTX 3060 8 GiB |
| WSL2 | Ubuntu 24.04.5, 16 CPUs |
| WSL2 VM 메모리 상한 | memory=16GB, swap=8GB |
| WSLg OpenGL | llvmpipe (Accelerated no) |

다른 프로젝트의 32GB RAM·GPU 전제는 이 PC에 적용하지 않음. Windows 전체 WSL에 영향을 주는 .wslconfig는 자동 변경하지 않음. 실제 병목 조치 전 [GPU-01](reports/issues/2026-11-19_GPU-01_wslg_llvmpipe.md)의 GLX D3D12 검증 우선.
