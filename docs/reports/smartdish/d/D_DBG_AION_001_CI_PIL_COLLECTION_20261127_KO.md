# D-DBG-AION-001 — L0 최초 수집 실패 (도구 의존성)

- **첫 RED:** [Actions #45926299277](https://github.com/silverbjin/samsung_AXI/actions/runs/45926299277), SHA `1098e663117aca6cd20b60eab41aa33615dbd96d`.
- L0 pytest collection에서 `tests/test_c_stability.py`가 `PIL` import에 실패하여 **전체 기능 테스트 실행 이전** 종료.
- **원인:** D 단독 계약 CI와 달리 C의 기존 `test_c_stability.py`는 Pillow·NumPy를 사용합니다. 이것은 제품 모델 성능 실패도 아니고 D FSM의 RED 논리를 검증한 결과도 아닙니다.
- **조치:** 신규 D-AION 전용 CI의 L0 Python 패키지 설치에 `python3-pil python3-numpy`만 보완, C 소스 또는 실제 모델 파일은 수정/설치하지 않음. 최초 수집 실패 로그는 원본 Run URL로 보존합니다.
- **학습:** pytest가 *collection* 단계에서 죽으면 assertion RED가 아니므로, 먼저 필요한 mock/검증용 의존성을 확인하고 실제 기대 실패와 구분해야 합니다.
