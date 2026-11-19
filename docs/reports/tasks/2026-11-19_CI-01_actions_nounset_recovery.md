# CI-01 작업 경과 보고서 — 최초 Actions 실패의 최소 수정

- 날짜: 2026-11-19 (KST)
- 작업: 원격 게시 후 자동 실행된 첫 Actions L1 실패 재현과 수정
- 결과: **로컬 회귀 6 PASS / 원격 L0 1 PASS / 원격 L1·L2 재검 전**
- 원본 Run: [#44443691545](https://github.com/silverbjin/samsung_AXI/actions/runs/44443691545)
- 디버깅 원문: [CI-01 문제 해결](../issues/2026-11-19_CI-01_nounset_ros_setup.md)

## 왜 필요한가?

강사 WSL2는 최종 인수만 수행해야 하므로, 소스의 문법·빌드·헤드리스 Gazebo 실행 오류를 GitHub Actions가 먼저 찾아야 합니다. 최초 CI에서 ROS 환경 설정 시점에 실패해 L1 빌드와 L2 센서 검증이 실행되지 못했습니다.

## 무엇을 확인하고 어떻게 고쳤는가?

1. L0 Job 완료 `success`와 L1 Job 실패 `failure`를 분리했습니다.
2. 긴 apt 설치 로그가 아니라 **최초 실패 줄** `AMENT_TRACE_SETUP_FILES: unbound variable`을 확인했습니다.
3. ROS 의존성 문제라는 가설을 기각하고, Bash `set -u`와 setup 스크립트 사이의 충돌로 범위를 좁혔습니다.
4. 실제 실패 메커니즘을 재현하는 작은 테스트를 만들고 RED를 확인했습니다.
5. 2개 실행 파일의 ROS setup 구간에만 `set +u` / `set -u`를 추가하여 테스트 6개 GREEN을 확인했습니다.

## 어떤 부분이 아직 미검증인가?

GitHub Actions의 다음 L1·L2는 **실제 Run을 확인하기 전까지 NOT_RUN**입니다. Headless Gazebo L2가 성공해도 지도·Nav2 1→3→1 배달 및 강사 WSL2 GUI는 별도 검증 대상으로 남습니다.
