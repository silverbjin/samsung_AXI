# A-13-DBG-02 — L0 Python 컴파일 SyntaxError와 빠른 실패 경계 교정

- 실제 CI: [Run #45306531902](https://github.com/silverbjin/samsung_AXI/actions/runs/45306531902), 소스 SHA `e4ac98179ed89061711554e6189daae132c7af84` 기준 **L0 FAIL**, L1/L2 실행 전에 차단됨.
- 최초 오류 `scripts/smartdish_a_tray_live.py:302 SyntaxError: invalid syntax`.
- 직전 수정에서 `all(result.get(s) == ... for s in (...) )`의 닫는 괄호 한 개가 누락되어 Python 구문 분석이 실패. 로봇/Gazebo/physics 문제 아님.
- 최소 변경: ST-01/02, UN-01/02 관측 결과 전체 검증식의 괄호만 정확히 닫습니다.
- 검증 순서: CI `python3 -m py_compile` 재실행 → L0 pytest → ROS L1 → 실제 Gazebo L2. 문법 검사 실패를 물리 검증 PASS로 위장할 수 없으므로 L2 상태는 실행 전 **NOT_RUN** 유지.
- 주니어 학습: 복잡한 조건식 변경 시 정적 `py_compile` 단계에서 한 번 더 확인하고, GitHub Actions에서 첫 오류 줄 번호가 나온 단계만 수정해야 함. 이미 검증된 S7 AI OFF/Map/Nav2 재검 금지.
