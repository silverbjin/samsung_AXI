# E-R3a DBG-01 — DDS 발견과 실제 수신은 다르다 (RED → 수정)

## 실제 실패 증거
- [Run 45935476236](https://github.com/silverbjin/samsung_AXI/actions/runs/45935476236), source fe69077ff05358ace738b7a6bdf4128b43cbe3f4, job 140297579449.
- Artifact 15170875623, ZIP SHA256 4e27f10c7d9a7f64a4bc3bad0bc8db87d9a0848aab54527f0b98f5d90a6fdb53 직접 재계산 일치. C build PASS, ST-01 실제 Gazebo camera/physics PASS: 51 image callbacks, 372 pose samples, 0.6s capture, 0.55s pose, 10.182s 관측, HELD_OBSERVED. 원본 PNG 1ee9c9a2b029adc5b7c581547fe1b42195b885ab2f5082835c91f7c1d6c57ab3.
- 첫 실패: capture_id=fresh, expected STABLE, actual UNKNOWN (confidence null, CI_ONLY_TEST_DOUBLE). missing 영상 UNKNOWN은 정상. C node log에는 predictor RGB match marker도 frame rejection도 없음. 종료 후 ExternalShutdownException/RCL shutdown 중복은 최초 실패 이후의 별도 이슈.
- 같은 SHA 기존 E/D/C17/Restaurant 등 PR CI 7개 success.

## 원인 분석
기존 replay probe는 BEST_EFFORT publisher에서 921600-byte Image 단 1회 전송 후 0.4초 sleep만 사용. DDS endpoint discovery는 callback 완료가 아님. 실제 이미지 유실/fragmentation 여부는 기존 로그만으로 확정 불가. 확인된 설계 결함은 C cache 수신 승인 증거 없이 요청을 발행한 것. 운영 C의 UNKNOWN 처리 기준은 유지한다.

## 최소 수정 및 검증
- Replay publisher만 RELIABLE로 변경 (기존 C BEST_EFFORT subscriber 호환). CI 전용 child에서 기존 InferenceCore.cache_rgb를 감싸 호출 성공, stamp, RGB SHA를 기록. 원래 함수 결과 그대로 반환. 요청은 실제 cache ACK 후에만 발행; 5초 timeout으로 실패 경계 명시. 재전송/무한 retry 없음.
- 기존 성공 A13 capture 재사용: actions/download-artifact, original source SHA와 PNG SHA 고정. 현재 검증 코드 SHA와 capture SHA 분리. A 물리 재실행 없음.
- 실패 응답과 C 로그를 CI 출력 및 artifact에 기록. 운영 코드/모델/승인 경계 변경 없음.
- 새 CI 완료 전 GREEN 미확정. 실제 v1 추론, 실시간 센서, Nav2 인수는 별도.
