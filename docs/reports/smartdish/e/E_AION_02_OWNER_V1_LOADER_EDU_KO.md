# E-AION-02 — Owner 승인 C v1 Frozen 모델 제한 로더·교육용 개발 보고서

- **문제:** C Trainer는 research_release_status=UNREVIEWED_NOT_FOR_PRODUCT를 저장합니다. C17 제품 경로는 별도 E 모델 승인이 없는 경우 이를 정상 차단합니다. 성능 33.3%는 이번 제한 통합 게이트에서 면제하되 사실 그대로 기록합니다.
- **수정:** 기본 load_predictor(path)는 C17 제품 SHA=None에 따라 계속 차단. owner_gazebo_integration=True를 명시한 경우에만 P2 체크포인트 SHA 6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c를 실제 바이트에서 계산하고 torch import/역직렬화 전에 비교합니다.
- **메타데이터:** frozen/PHYSICS_OBSERVED/UNREVIEWED_NOT_FOR_PRODUCT, B Dataset v1 SHA, split manifest SHA, P1 plan SHA, ResNet18 label/normalization, state_dict 필수. 원본 metadata를 억지로 C_RESEARCH_PILOT_ACCEPTED로 바꾸지 않습니다.
- **ROS:** C 노드 owner_gazebo_integration ROS parameter는 기본 false. 원본 모델 바이트가 없을 때 실제 추론 결과를 만들어내지 않습니다.
- **교육·QA:** 가짜 파일 바이트를 사용한 SHA 검증 실패는 mock-only. 원본 C17 우회 여부와의 차이를 설명하고 기존 C17 제품 기본 deny 테스트 유지.
- **권리 범위:** Owner 내부 WSL2/Gazebo 제한 통합만, 무단 체크포인트/이미지 공개나 외부 배포 권한은 주장하지 않습니다.
- **인수:** GitHub L0/L1은 합성 메타데이터·무모델 통신 확인까지. 실제 private checkpoint 해시·로딩·추론은 사용자 WSL2 독립 인수 때에만 PASS로 승격합니다.
