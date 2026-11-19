# HW-01 — SAMSUNGAXI PC 전용 CPU·RAM·GPU 진단기

- 날짜: 2026-11-19 KST
- 개발 요구: 다른 프로젝트 PC와 사양이 다르므로 기존 사양·권장값을 복사하지 않고 SAMSUNGAXI PC 실측값으로 최적화
- 상태: **정적·격리 실행 검증 PASS / 실제 SAMSUNGAXI Windows+WSL2 현장 진단 NOT_RUN**

## 배경과 문제 정의
기존 RTF 분석 문서에는 다른 PC의 RAM 32GB와 `memory=20GB` 예시가 포함되어 있었습니다. 해당 값은 SAMSUNGAXI PC의 실측 자료가 아니므로 잘못된 튜닝을 유도할 수 있습니다. 병목 진단 전에는 하드웨어를 가정할 수 없습니다.

## 재사용과 구현
기존 S1PERF-01 `wsl2_perf_doctor.sh`의 WSLg 점검 항목을 참고하되, Windows 호스트 `Get-CimInstance` CPU/RAM/GPU와 WSL2 실제 가용 자원, `/dev/dxg`, `glxinfo -B`, NVIDIA 확인, cgroup 제한을 수집하는 독립 SAMSUNGAXI 프로파일 진단기를 추가했습니다.

- `scripts/samsungaxi_hw_probe.sh`: 단일 실행, 읽기 전용, 시간 제한된 검사; 로그의 텍스트·JSON 출력
- `docs/HARDWARE_PROFILE_SAMSUNGAXI.md`: 수집·해석·튜닝 결정 기준
- `tests/test_samsungaxi_hw_probe.py`: Bash 구문, 자기진단, Windows 상호운용 불가 처리, Mock Windows CPU/GPU JSON 및 D3D12 파싱
- 기존 `docs/WSL2_PERFORMANCE.md`: RAM 32GB/20GB 전제 삭제, HW-01 프로파일을 기준으로 개별 검토

## 검증 증거와 한계
Bash `-n`, Python pytest 3개 PASS; Windows 연결이 없는 Linux 테스트 컨테이너에서 `windows_host.status=unavailable`와 JSON/텍스트 정상 출력 확인. Mock PowerShell에서 CPU/RAM/GPU 및 D3D12 렌더러 결과를 재현.

**SAMSUNGAXI 실제 PC 하드웨어 수치와 RTF 개선치의 증거는 아직 없습니다.** 테스트 컨테이너의 AMD EPYC 정보는 테스트 인프라 정보이므로 프로젝트 PC 하드웨어 프로파일에 포함하지 않습니다.

## 다음 확인
강사 WSL2에서 `bash scripts/samsungaxi_hw_probe.sh` 실행 → 해당 `samsungaxi_hardware.txt`/`json` 검토 → CPU/RAM/GPU 원인별 최소 최적화 → 동일 S1 장면 RTF 및 `/scan`·RGB-D 수신 확인 → S2 지도 생성. 원본 리포트 전체를 Git에 커밋하지 않으며 보고서에는 원인·판단·검수만 기록합니다.