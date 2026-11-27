# E-AION-06 — private C v1 체크포인트 읽기 전용 SHA 검사기

- 목적: Owner WSL2에 비공개로 보관된 C P2 원본 파일을 GitHub에 업로드하지 않고 SHA/바이트 수만 검수.
- 입력: --checkpoint /private/path/to/c_v1_frozen_head.pt; 선택 --report /private/path/receipt.json.
- 코드에 고정된 Owner v1 E 승인 SHA만 허용. CLI나 환경변수로 승인값 교체 불가.
- torch import, checkpoint deserialization, 이미지 읽기, 데이터 학습/Test 개봉, ROS Goal 0건.
- 부정 시험: 모델 누락·심볼릭 링크·빈 바이트·해시 불일치 차단. 합성 fixture에 한해 pytest monkeypatch로 검사 알고리즘 자체를 검증하며 실제 model pass 주장 금지.
- 결과 마커 E_OWNER_MODEL_SHA_PASS 또는 E_OWNER_MODEL_PREFLIGHT_BLOCKED=<reason>.
- 파일 SHA가 일치하더라도 모델 입력/추론·성능·Gazebo Owner L3 인수는 별개의 검수.
- E 제품 승인 사용자 권한은 내부 Gazebo 통합 범위이며, 서드파티 pretrain 권리/외부 배포에 확장하지 않음.
