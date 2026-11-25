# SmartDish B10-DBG-02 — B 원본 읽기 전용 보존과 손상 주입 테스트의 충돌

- 최초 실패: [GitHub CI Run #45551662771](https://github.com/silverbjin/samsung_AXI/actions/runs/45551662771), 기준 commit `4b946a068fad7534b9c0873cd24f0e30a2edc6c0`, Python 3.12, ubuntu-24.04.
- 실패 경계: 데이터 계약 테스트 중 5개에서 `PermissionError: [Errno 13] Permission denied`로 실제 테스트의 `write_text`·`write_bytes` 호출 실패. Runner 결과 50 PASS / 5 FAIL.
- 근본 원인: B-10 `import_archive()`는 검증된 TAR의 내부 원본 파일을 `0444`로 보존한다. 기존 손상 주입 테스트의 fixture helper가 **인수 결과물**을 그대로 변경하는 구조라, GitHub의 일반 사용자 권한에서 수정이 거부되었다. 로컬 root에서는 쓰기 권한이 우회되어 발견하지 못했다.
- 수정: 운영 코드·원본 보호 정책 그대로 유지. `tests/test_b_a13_real_data.py`의 **합성 fixture 전용 `imported()` helper**에서만 `chmod(0600)`으로 변조 가능한 테스트 복제본을 만든다. 별도 `test_b10_real_import_preserves_readonly_verified_bytes`에서 운영 인수기 결과가 실제 `0444`인지 확인한다.
- RED→GREEN: 최초 Run ID와 오류를 본 문서에 보존. 후속 CI의 동일 테스트 + 기존 B 30개 결과를 PR #46에서 확인하여 판정 보강.
- 테스트 결과는 원본을 직접 검증한 **실제 A-13 데이터**가 아니라 인공 계약 fixture임. 실제 원본 TAR `NOT_RUN`, 실제 승인 0건.

교육용 핵심 교훈: 읽기 전용 운영 기능이 옳아도 손상 주입 테스트의 준비 단계에서 실패할 수 있습니다. **검증하려던 오류 코드까지 실제로 도달했는지** 확인해야 하며, 테스트 편의를 위해 운영 보안 규칙을 해제해서는 안 됩니다.
