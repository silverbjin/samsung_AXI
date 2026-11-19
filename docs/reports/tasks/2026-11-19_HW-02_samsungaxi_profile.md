# HW-02 — SAMSUNGAXI PC 실제 사양에 기반한 최적화 진단
- 날짜: 2026-11-19, 코드 기준 main 8968fd212e9fe50413d3f509abe6b08ef6f104bb
- 작업 전: 다른 AXIA PC의 RAM/GPU 가정이 섞일 위험.
- 산출물: [GPU-01 문제 보고서](../issues/2026-11-19_GPU-01_wslg_llvmpipe.md), 변경 없는 3종 D3D12 GLX 진단기.
- 실측: i7-11700F, Windows RAM 15.86GiB, RTX 3060 8GB. WSL OpenGL llvmpipe.
- 판단: 메모리 부족보다 OpenGL 소프트웨어 렌더링이 우선 확인할 문제.
- 검증: Bash 구문 + 모의 GLX 분기 검사 PASS; 해당 PC 실기·Gazebo 개선 NOT_RUN.
- 원칙: 시스템 자동 변경·기존 PR #2 수정·CI 재실행 없음. 결과 확인 후 최소 수정을 별도 검수.
