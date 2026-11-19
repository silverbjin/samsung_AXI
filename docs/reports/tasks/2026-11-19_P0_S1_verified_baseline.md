# P0-S1 — 실제 S1 성공·GPU·센서·증거 기준선 병합
- 2026-11-19 KST, 기준 main e424b2971b79bd77d4de3312b27152201bb0ea9e
- 강사 WSL2 화면: 레스토랑 World와 Waffle Pi Spawn/GUI 정상, RTF 이전 61.95% 이후 99.89% (각 한 시점).
- GPU-01: llvmpipe → GALLIUM_DRIVER=d3d12 D3D12 NVIDIA RTX3060 GLX 가속, 재설치 불필요.
- PR #3 EVD-01: L0/L1/L2 Gazebo NO_GOAL GREEN Run #44483609465, main 병합 e424b297.
- PR #2: 카메라 중복 제거 + LiDAR 광선 시각화 OFF + 브리지 축소 + 하드웨어 진단. 최신 L2 취소돼 통합 HEAD CI 재검 필수.
- CI pytest는 EVD+PERF+HW 모든 계약 포함, S1 actual Gazebo Scan/Odom/TF/RGB/Depth/Points 보존 확인 후 P0 GREEN.
- 미검증: 변경 후 WSLg RTF 장기 평균, S2 실제 지도 저장/재로딩, S3 배달, S4 안전.
- 다음: S2-MAP-01 SLAM Toolbox 공식 구성 재사용; 실제 지도·이동·저장·재로딩 L2 검증.

## P0 최종 검증 판정
- PR #4 L0/L1/L2 실제 Gazebo **GREEN**: [Run #44486003784](https://github.com/silverbjin/samsung_AXI/actions/runs/44486003784).
- `main` P0 병합: `c124d3d83f323c56a0cc14497314a0e3e5af437d`. S1 기준선 확정.
- S1 GUI RTF 99.89%는 강사 캡처의 한 시점이며 반복·지속 성능 합격 게이트는 아님.
- 이어지는 S2는 PR #5 [Run #44488688236](https://github.com/silverbjin/samsung_AXI/actions/runs/44488688236) 실제 SLAM·저장·재로딩 GREEN. S1 결과와 S2 Map 기능을 혼합 판정하지 않음.
