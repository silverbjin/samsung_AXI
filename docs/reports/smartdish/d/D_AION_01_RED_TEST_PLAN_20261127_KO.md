# D-AION-01 RED 계약 명세 (2026-11-27)

- D00 기준 main `ed59fa22bb53d1590ba10eef8f7982fcf44e7d29`, 현 C17 `PRODUCT_APPROVED_CHECKPOINT_SHA256=None`.
- 새 `tests/test_smartdish_d_aion.py`는 실제 모델 없이 기존 D의 boolean-only Manager/UI, 미승인 STABLE 자동 전이, 0.80 confidence 및 AI_CHECK 기한 미검증을 실패 사례로 기록합니다.
- **RED 예상:** `product_admission` 부재, `approved_model_sha256` 미지원, forged STABLE 자동 진행. 정상 실패를 제품 AI ON 성공으로 해석하지 않습니다.
- 실물 Nav2/Gazebo Goal, B private 자료, C `.pt`, P3 Test, C20 연구, A19 신규 데이터는 일절 사용하지 않습니다.
- GREEN 목표: 승인된 E 제품 모델이 없으므로 D Manager/UI에서 AI 사용 불가. 순수 FSM의 synthetic fixture에만 유효 64-hex 모델 SHA를 주입해 STABLE 계약을 검증할 수 있고, 실제 ROS 제품 부팅 시 이 테스트 대역을 사용하지 않습니다.
- 변경은 D 코드/테스트/전용 CI에 국한. 다른 폴더 출고 승인 상태·AI OFF L3 불변.
- 교육 포인트: RED 실패는 '안전 정책을 먼저 명세하는 시험'이며 임의 테스트 성공이 아니라 현재 동작의 부족한 지점을 증거로 기록합니다.
