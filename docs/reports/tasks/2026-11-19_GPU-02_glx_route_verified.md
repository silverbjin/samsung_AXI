# GPU-02 — D3D12 하드웨어 GLX 경로 실기 확인 및 국소 Gazebo 실행기

- 날짜: 2026-11-19 KST
- 이전 기준: `f734ac6d53d4a9d676e1ebb48e39e6bbde696db4`
- 필요성: RTX 3060이 노출됐으나 기본 WSLg OpenGL이 llvmpipe였으며 S1 RTF 61.95%가 관찰됨.
- 실제 현장 관측: glxinfo 기본 llvmpipe (no), 명시적 D3D12는 NVIDIA RTX 3060 (yes), 모두 EXIT=0.
- 기술 판단: 드라이버 재설치나 .wslconfig 수정 대신 기존 GUI 세션에만 `GALLIUM_DRIVER=d3d12` 적용.
- 구현: `scripts/samsungaxi_d3d12_world_once.sh` (`doctor` / `world`, 실패 시 Goal 없이 사전 차단).
- 코드 검증: `bash -n` PASS, 모의 GLX 성공·실패·유효하지 않은 인자 3개 경로 PASS.
- 아직 확인하지 않은 항목: Gazebo Ogre2 D3D12 사용, 현장 RTF 개선, Scan/Depth 실제 데이터, S2 지도 생성.
- 교육용 연결: [GPU-01 원인과 분리](../issues/2026-11-19_GPU-01_wslg_llvmpipe.md).
## 배포 전 소스 무결성 검사

- 원격 최초 생성 버전의 Git Blob SHA가 로컬 검수 파일과 달라 전송 과정의 `\${` 문자열 4개를 발견했습니다.
- 4개 이스케이프 문자를 제거한 뒤 원격 Git Blob SHA가 로컬 `c5d73ea669582f489e257066a82d65dcd0608b2e`와 일치함을 확인했습니다.
- 이는 실제 WSL2 실행 전에 검출·수정한 **코드 전송 결함**입니다. [GPU-02-EXPORT 보고서](../issues/2026-11-19_GPU-02_transport_escaping.md).
