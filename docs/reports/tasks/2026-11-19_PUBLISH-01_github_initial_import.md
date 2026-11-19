# PUBLISH-01 작업 경과 보고서 — 독립 MVP GitHub 원격 최초 게시

- 날짜: 2026-11-19 (KST)
- 작업: `silverbjin/samsung_AXI` 최초 Git 업로드 및 Actions 최초 실행 확인
- 판정: **소스 게시 PASS** · **GitHub L0 PASS** · **L1/L2는 별도 Run 결론에 따름** · **Owner WSL2 NOT_RUN**
- 원본 로컬 HEAD: `4105e0b93027ef7ea3a53c22d90e8e6e0aa86001`
- 원격 게시 후 기준선: [`a11951cc3dbe9e18c8b154d8e8787a09dd6f7dc2`](https://github.com/silverbjin/samsung_AXI/commit/a11951cc3dbe9e18c8b154d8e8787a09dd6f7dc2)
- Git Tree (로컬·원격 일치): `e9f535d70227abb6ccc5079b78bc0ce6a2cef722`
- 최초 Actions: [Run #44443691545](https://github.com/silverbjin/samsung_AXI/actions/runs/44443691545)
- 관련 디버깅: [INFRA-01 로컬 GitHub DNS 실패](../issues/2026-11-19_INFRA-01_container_github_dns.md)

## 1. 작업 배경 — 왜 Git 이력까지 보존하는가?

레스토랑 ROS 2 MVP 소스뿐 아니라 기능·CI·문서화 정책의 **개발 순서**를 훈련생이 추적할 수 있어야 합니다. 초기 로컬 파일을 한 번에 복사하면 어떤 변경이 왜 들어왔는지 확인하기 어렵습니다. 따라서 원격이 빈 저장소인지 먼저 확인하고, 기존 5개 로컬 커밋의 변경 집합과 커밋 메시지를 순서대로 GitHub Git 객체로 재구성했습니다. 브랜치를 강제 덮어쓰지 않았습니다.

## 2. 실제 작업 및 기술 판단

| 순서 | 관찰·선택 | 결과 |
|---|---|---|
| 1 | GitHub 연결로 공개 저장소 권한·비어 있는 `main` 확인 | 기존 이력 충돌 없음 |
| 2 | 파일 컨테이너에서 `git ls-remote` DNS 실패 재현 | 로컬 Git CLI 대신 연결된 GitHub API 사용 |
| 3 | 최초 `.gitignore` 초기화 커밋 생성 | 빈 원격 `main` 생성 |
| 4 | 원본 5개 로컬 커밋의 변경 파일·메시지 순서대로 Git Tree·Commit 생성 | 원본 SHA는 각 재구성 커밋 메시지에 기록 (SHA 자체는 새로 생성됨) |
| 5 | 안전한 fast-forward로 `main` HEAD 갱신 (`force=false`) | 원격 HEAD `a11951cc...` |
| 6 | 원격 Git Tree·파일 수·Actions 워크플로 확인 | 추적 파일 **50개**, 원본과 Git Tree SHA 완전 일치 |
| 7 | 첫 Actions Run 조회 | L0 정적 검사 SUCCESS; L1/L2 결과는 Run 링크 확인 필요 |

## 3. 핵심 증거 및 검증 범위

로컬 `git rev-parse HEAD^{tree}`와 원격 `/commits/main`의 Git Tree 값은 모두 `e9f535d70227abb6ccc5079b78bc0ce6a2cef722`입니다. Git은 파일 내용·파일 모드·경로의 트리 해시가 같을 때 동일 트리 SHA를 생성하므로, 최종 소스 스냅샷 전체가 일치한다는 근거입니다.

원격 Actions는 소스 업로드 직후 자동으로 시작했습니다. **CI 결과는 GitHub Run 상태로만 판단**하며, L0 통과를 ROS 빌드·Gazebo 센서·Nav2 실제 배달 성공으로 확장하지 않습니다. 본 보고서는 최초 업로드 작업이 실제로 끝났음을 기록합니다.

## 4. 미검증 및 다음 단계

- Actions L1/L2: [Run #44443691545](https://github.com/silverbjin/samsung_AXI/actions/runs/44443691545)의 최종 결과가 GREEN인지 확인하고 실패 시 같은 경계만 수정합니다.
- 실제 SLAM 지도 재사용·Nav2 `1→3→1` Goal·물리 장애물 제어: 아직 **NOT_RUN**.
- 강사 WSL2 GUI 통합 시연 및 `DEMO_PASS`: 아직 **NOT_RUN**.

## 5. 교육 포인트

**네트워크 실패 ≠ Git 권한 실패 ≠ ROS 소스 실패**입니다. 로컬 DNS 문제에 맞춰 소스 코드를 바꾸거나 무분별하게 네트워크를 수정하는 대신, 기존 권한이 확인된 GitHub 연결을 사용해 **증거가 보존되는 동일 Git 객체 구조**로 배포했습니다. `main`의 최종 SHA와 Tree SHA, 첫 CI Run을 연결하면 재현 가능한 개발 이력이 됩니다.
