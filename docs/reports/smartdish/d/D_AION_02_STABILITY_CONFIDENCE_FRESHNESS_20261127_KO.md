# D-AION-02 — 위조 STABLE/ID·시간·confidence 계약 보호

- **RED:** D FSM은 상관관계 ID 및 STABLE + 숫자 confidence만 확인했고 `confidence=0.1`도 허용했습니다. `ClockType.STEADY_TIME` timer callback 이전에 도착한 5초 경과 STABLE도 허용될 수 있었습니다.
- **GREEN:** `on_stability`가 요청/캡처 ID, `clock() >= deadline` 자체 검사, finite confidence >=0.80, E 허가로 주입된 SHA를 바탕으로 `resnet18-<SHA[:12]>` 정확한 모델 버전을 검증합니다.
- 64자리 전체 모델 SHA는 D의 내부 승인 설정에만 있으며 7개 JSON 토픽에 새로운 필드를 추가하지 않습니다. ROS 메시지의 model_version 문자열만으로 승인될 수 없습니다.
- 정책 HOLD에서는 승인 SHA None이므로 `STABLE`은 무조건 추가 Goal 없음. UNKNOWN/UNSTABLE은 현행 `NEEDS_CONFIRMATION`, 5초 timeout은 `AI_TIMEOUT`.
- **fixture 한정 테스트:** `approved_model_sha256="a"*64`는 순수 Python FSM L0에서만 사용하며 실제 C 승인값/제품 증거가 아니고 운영 Manager에 주입되지 않습니다.
- 실제 제품 모델 인수·공급자 인증·ROS 2 신뢰 경계는 E 승인 별도 요구. 악의적 ROS publisher 진본성 검증이 코드상 완성됐다고 주장하지 않습니다.
- 미수행: 모델 다운로드/torch.load/학습/Test4/Gazebo/WSL2, 실물 접촉 검증.

## 실제 회귀 결과 및 신뢰 경계

- 구현 SHA: `774a42914be6123ab89f71cee759b224ab1b72aa`.
- [L0 92 PASS #45926489996](https://github.com/silverbjin/samsung_AXI/actions/runs/45926489996): 위조 model_version, confidence None/0/0.1/0.799999/NaN/Inf/bool, 다른 capture/request, deadline 5.1초 이후 STABLE 수신 차단.
- 같은 L0에서 **승인 SHA 대신 합성 64-hex 픽스처**를 명시적으로 전달할 때만 정상 0.80 STABLE의 상태 머신 전이 규칙을 검증. 해당 fixture는 실제 ROS Manager 경로에서 사용되지 않고 E 제품 승인을 뜻하지 않습니다.
- C 기존 `test_c_stability.py`로 영상 TTL 2초/중복/낮은 confidence→UNKNOWN 규칙 회귀. 실제 프레임·추론 가중치 사용하지 않음.
- 주의: `model_version` 문자열만 검사한다고 ROS Publisher가 암호학적으로 인증되지는 않습니다. 현재 제품 게이트가 닫혀 있으므로 물리 Goal을 유발할 수 없으며, 미래 실제 모델 출고 전에 E가 공급자 신뢰/릴리스 영수증을 별도 검증해야 합니다.
