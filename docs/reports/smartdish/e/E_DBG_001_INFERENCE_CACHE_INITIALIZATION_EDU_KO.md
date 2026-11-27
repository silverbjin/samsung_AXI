# E-DBG-001 — 동적 Threshold 개발 중 InferenceCore 초기화 위치 오류

- 최초 RED: https://github.com/silverbjin/samsung_AXI/actions/runs/45928798798 ; 107 PASS / 19 FAIL, L1 SKIPPED.
- 최초 오류: AttributeError: InferenceCore.frame_seq/seen_requests/last_stamp_ns does not exist.
- 원인: C 임계값 헬퍼 추가 과정에서 기존 self.frame, frame_seq, last_used_seq, seen_requests, last_stamp_ns가 decision_thresholds()의 return 다음 줄로 잘못 이동. Python return 다음 줄은 실행되지 않습니다.
- 최소 수정: 다섯 필드를 __init__의 max_image_age_s 다음 줄로 되돌리고, decision_thresholds 함수는 두 threshold 반환만 수행.
- 이전 C/ C17/ D-AION 테스트가 기존 회귀를 발견했습니다. compile PASS만으로 상태 초기화가 입증되지 않는다는 교육 사례입니다.
- 레거시 기능 및 5초 timeout, C20, 비공개 모델 성능, A/Nav2/CM/AI OFF 변경 없음.
- GREEN 근거는 후속 GitHub Actions L0·L1 결과에서 판정하며 기존 RED 링크는 삭제하지 않습니다.