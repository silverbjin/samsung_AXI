# EVD-01 — RTF 99.89% 현장 관찰 및 Gazebo 경량 증거 ZIP 설계·검수

- 날짜: 2026-11-19 KST
- 프로젝트: SAMSUNGAXI 전용 (다른 PC·AXIA 프로젝트 별도 운영)
- 기준: 검수된 D3D12 GPU S1 world 실행기를 그대로 보존
- 상태: **정적·모의 테스트 PASS / 현장 ZIP 수집 NOT_RUN**

## 요구사항과 증거

강사 GUI 스크린샷에서 레스토랑 월드/로봇 렌더링 및 RTF 99.89% 관찰(이전 화면 61.95%). 단일 화면 값이며 장기 성능/센서/자율주행 인수는 별도입니다. 대량 Gazebo·ROS 로그를 분석 가능한 크기로 수집해 교육용 오류 추적에 활용하려는 것이 이번 변경의 목적입니다.

## 선택한 최소 구현

1. 성공 원본 D3D12 world 실행기/로봇 물리/센서 설정을 수정하지 않음. 새로운 `samsungaxi_d3d12_evidence_once.sh` 래퍼에서 기존 실행기를 호출하고 종료 시 증거 압축.
2. Python 표준 `zipfile` 사용, 별도 ROS 의존성 불필요. 원본 보존/다른 세션 무관한 ROS 로그 제외.
3. 원본 파일별 시작·최초 오류/경고·마지막 구간 우선 300KB 이내 추출, 크기와 누락 내용을 JSON에 기록.
4. 비밀정보 패턴 마스킹. 추가 검사는 `gz topic`의 실제 RTF 통계를 **실행 중 별도 명령**으로 저장.

## 검증과 판정

- `bash -n` 신규 Bash 2개 PASS, Python 컴파일 PASS.
- `pytest` 5개 PASS: 큰 로그를 작은 ZIP으로 추출, 오류 및 토큰 비식별, ROS 세션 스코프 및 덮어쓰기 방지, 정상 종료, 실패 시 종료 코드/ZIP 유지.
- GitHub Actions L0/L1/L2와 현장 자동 ZIP 수집은 해당 Run 결과 확인 전 성공 주장 금지.
- ZIP 생성 자체는 Gazebo/ROS/Nav2/안전 통합 인수 PASS가 아닙니다.

## 다음 단계

이번 압축 수집기를 강사 WSL2 D3D12 world에서 한 번 사용하여 생성 ZIP에 원본 세션, RTF(선택), 실제 Scan/Depth 진단 로그가 포함됐는지 확인합니다. 이후 S2 SLAM/지도 저장 문제 발생 시 같은 도구를 재사용합니다.

사용법: [EVIDENCE_BUNDLES.md](../../EVIDENCE_BUNDLES.md).
