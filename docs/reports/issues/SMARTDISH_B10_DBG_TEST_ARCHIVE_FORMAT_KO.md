# SmartDish B10-DBG-01 — 위협 입력 테스트가 원래 검증기로 진입하지 못한 사례

- 환경: 2026-11-25 로컬 Python 3.13 / pytest / `tarfile`.
- 실제 발생: 경로 이탈 `../escape`, `/absolute`를 테스트하기 위해 만들었던 fixture를 `tarfile.open(...,'w')`로 생성한 후, 운영 인수기는 `r:gz` 압축을 요구하여 최초 실패가 **`B10_ARCHIVE_MALFORMED`**가 됨.
- 원인: 공격자 경로 검증의 문제가 아니라 테스트 fixture가 실제 A-13 압축 TAR 형식과 다름. 예상 `B10_ARCHIVE_UNSAFE_PATH` 분기까지 도달하지 않았음.
- 수정: fixture를 `tarfile.open(...,'w:gz')`로 일치시킴. 실제 import 코드는 느슨하게 풀지 않음.
- 동일 경계 재검: 올바른 gzip 파일 안에 이탈 경로를 넣고 `B10_ARCHIVE_UNSAFE_PATH` 예외를 확인. 보안 검사는 여전히 fail-closed.
- 원본 파일 없음: 이 테스트는 **합성 해악 입력**만 다룸. 실제 A WSL2 데이터 검증 PASS와 혼동하면 안 됨.

교육 포인트: 실패했다는 결과만으로 원하는 보안 조건이 검증된 것은 아닙니다. **실패한 정확한 분기/예외 코드**를 확인해야 합니다.
