# A-13-DBG-07 — 실제 Gazebo ST-01 관측 뒤 Evidence API 키 이름 불일치

- 검증 원본: [Actions Run #45309401275](https://github.com/silverbjin/samsung_AXI/actions/runs/45309401275), 코드 SHA `6faaee4ae6b893d6fd3c8bbd028f13691fb636c9`.
- L0 24 PASS, ROS L1 PASS. **실제 Gazebo L2**: ST-01에서 `SMARTDISH_A_TRAY_CAMERA_LIVE_PASS stamp_ns=200000000`, `SMARTDISH_A_TRAY_RGB_CAPTURE_PASS` (B `save_unlabelled_frame` 호출), `SMARTDISH_A_TRAY_PHYSICS_OBSERVED outcome=HELD_OBSERVED`까지 실제 성공.
- 직후 첫 오류: `TypeError: verify_timing() got an unexpected keyword argument 'capture_stamp_ns'` at `scripts/smartdish_a_tray_live.py:262`.
- 원인: `verify_timing(capture_ns, observation_start_ns, observation_end_ns, captured_pose_ns, distinct_frame_stamps)` 함수 파라미터 이름과 `trial_summary.json` schema 필드 `capture_stamp_ns, pose_at_capture_ns, image_stamp_samples` 이름이 다름. JSON schema를 변경하여 B 사용자를 깨뜨리는 대신 **명시적 positional API 호출로 정렬**.
- 테스트: `tests/test_smartdish_tray_evidence.py`에 실제 valid time sequence 계약(0.2s RGB → 0.21s 관측 시작 → 10.31s 관측 끝) GREEN, `tests/test_smartdish_a_tray_runner.py`에서 잘못된 `**timing` 전달 회귀 방지.
- **판정 절차**: 이전 L2의 ST-01 RGB/PNG/물리 10초는 일부 원본 실증으로 인정. 하지만 trial_summary 검증 전 종료되어 전체 L2 및 ST-02/UN-01/UN-02는 PASS가 아님. 수정 뒤 네 시나리오 실제 Gazebo→SHA를 재확인해야 최종 L2 완료.
- 주니어 교육 포인트: 인터페이스와 파일 스키마를 분리하고, 첫 오류가 실제 물리 이후에 발생했는지 살펴 책임 범위를 좁힙니다. 이미 검증된 Nav2/Map/S7 제품을 반복 실행하지 않습니다.
