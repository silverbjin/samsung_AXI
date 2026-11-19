# INFRA-01 문제 해결 보고서 — 작업 컨테이너의 GitHub DNS 접근 실패

- 발생일: 2026-11-19 (KST)
- 위치: 이 대화의 소스 파일 생성 컨테이너 (`/mnt/data/restaurant_robot_mvp`)
- 상태: **HOLD** (로컬 컨테이너 네트워크 제약, GitHub 리포지토리 문제로 단정하지 않음)
- 연관 작업 보고서: [DOC-01](../tasks/2026-11-19_DOC-01_reporting_policy_setup.md)
- 최초 확인 로컬 HEAD: `70287b74e1d6cc73b37a03b849dc0b2414a2204b`

## 1. 현상과 영향

- 기대: `git ls-remote`로 `silverbjin/samsung_AXI`의 원격 `main`을 확인하고 안전한 업로드 여부를 판단
- 실제: 로컬 `git ls-remote` 실행 시 GitHub 호스트 이름을 해석하지 못함
- 영향: 이번 실행 환경의 Git CLI로 원격 Git Push를 수행할 수 없음. 문서·코드의 로컬 커밋은 정상

## 2. 재현 증거와 첫 실패

```bash
timeout 12 git ls-remote https://github.com/silverbjin/samsung_AXI.git refs/heads/main
```

```text
fatal: unable to access 'https://github.com/silverbjin/samsung_AXI.git/': Could not resolve host: github.com
```

이전 별도 GitHub 연결에서는 원격 저장소가 존재하고 `size=0`이며 Public임을 조회했습니다. **따라서 원격 저장소가 존재하지 않는다거나 권한이 없다는 결론은 내려서는 안 됩니다.**

## 3. 진단과 원인 판단

- 확정 사실: 현재 파일 작업 컨테이너의 Git CLI는 `github.com` DNS 이름 해석에 실패
- 미확정: 컨테이너의 DNS 구성, 아웃바운드 네트워크 차단, 임시 환경 제한 중 정확한 하위 원인
- 무관한 범위: ROS2·Gazebo 소스의 빌드/런타임 오류와는 무관

## 4. 최소 조치와 재검

- 로컬 소스를 무리하게 수정하지 않고 GitHub 커넥터의 저장소 상태 조회를 사용
- 별도의 네트워크가 정상인 Git 클라이언트에서 `scripts/first_publish_samsung_axi.sh`를 사용하도록 설계
- **원격 게시 성공은 아직 확인하지 못했으므로 이슈 상태는 HOLD**, 업로드 성공 주장 금지
- GitHub 브랜치를 강제로 재작성하거나 토큰을 문서에 기록하지 않음

## 5. 교육 포인트

클라이언트의 DNS 실패는 저장소 권한·소스 코드 오류와 다릅니다. 첫 실패 지점에서 **네트워크 계층과 저장소/빌드 계층을 분리**하면 불필요한 ROS 패키지 수정이나 권한 변경을 피할 수 있습니다. 다음 환경에서 원격 HEAD 재조회 및 안전한 최초 게시가 검증되면 본 보고서에 결과를 추가하고 `RESOLVED`로 변경하십시오.
