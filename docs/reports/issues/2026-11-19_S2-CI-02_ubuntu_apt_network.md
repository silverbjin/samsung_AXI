# S2-CI-02 — main 병합 후 GitHub runner APT 포트 80 네트워크 타임아웃

- 날짜: 2026-11-19 KST
- 기준 main 소스 병합 SHA: `344dacbd47760c32898dffdc6ad43ec21cb9f0c5`
- 초회 Run: https://github.com/silverbjin/samsung_AXI/actions/runs/44520735057
- 상태: **원인 경계 분류 완료 / 실패 Job 1회 재검 진행 중**

## 최초 현상과 증거
- L0 Static 계약 테스트 PASS; L1+L2 Job의 `Install official ROS 2 / Gazebo Harmonic runtime` 단계에서 apt-get 종료코드 100.
- `archive.ubuntu.com:80` 및 `security.ubuntu.com:80` 연결 타임아웃, Release Index 확보 실패.
- `E: Unable to locate package xvfb`, `xauth`, `mesa-utils`는 APT 인덱스 누락의 후속 현상.
- **Gazebo·SLAM·Map Saver·Map Server 테스트는 미시작**, 소스 기능 회귀로 판정하지 않음.

## 대조 및 원인 범위
- 동일 PR HEAD `0ed197d...`의 [Run #44488688236](https://github.com/silverbjin/samsung_AXI/actions/runs/44488688236)는 실제 Scan/Map/SaveMap/Reload 모두 GREEN.
- 본 main Run은 소스 병합 이후, `ros:jazzy-ros-base-noble` 컨테이너의 APT 저장소 연결 단계에서 발생.
- 실제 서비스 호스트·DNS·리포지토리의 근본 네트워크 원인은 확정할 수 없음. **APT HTTP 접근 실패**가 최초 실패 경계.

## 최소 조치 및 재검 원칙
- 이미 GREEN인 L0 및 원본 S2 실제 지도 아티팩트는 보존.
- 신규 코드·ROS·Gazebo 설정 변경 없이 **실패 L1/L2 Job 하나만 재실행**(Run #44520735057, attempt 2).
- 동일 APT 접근 장애가 재현되면 Container 내부의 Ubuntu APT Source를 HTTPS로 국소 전환하는 최소 수정과 해당 CI 재검을 검토. Windows WSL2 PC 설정은 변경하지 않음.
- 결과를 확인할 때까지 **main 병합 후 전체 재검 PASS**로 보고하지 않음.

## 교육 포인트
테스트 작업 흐름에서는 `L0 소스 계약 → L1 의존성 설치·빌드 → L2 Gazebo 실증`을 구분해야 합니다. 네트워크로 apt index를 읽지 못하는 실패를 SLAM 구현 결함이라고 오진하거나 테스트 스킵으로 덮지 않습니다.
