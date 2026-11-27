# E-R4 DBG-05 — 파라미터 서비스 ACK timeout과 초기화 부하 분리

## RED
- [CI 45938853752](https://github.com/silverbjin/samsung_AXI/actions/runs/45938853752), source `b23adebcfdd840e1b7da8bdcb4af4ac7339c98d0`, artifact 15171753190 SHA256 `7857b2ae3b1de38498de8f4a17138b54a5fd8feb742cb5b8b98ee82897d99814` 직접 재계산 일치.
- CM/BT ACTIVE 및 단독 CM 전체 속도 graph PASS. A TTY 승인 및 READY, C fixture model READY, D READY, 실제 RGB 수신 시작. C 로그: `C_DYNAMIC_THRESHOLD_APPLIED stable=0.650 unstable=0.900` 뒤 `failed to send response (timeout): client will not receive response`. observer 최초 오류 `E_R4_TIMEOUT_PARAMETER_ACK`. Goal/action/leg 모두 0건, owned process 6개 exit0.
- 파라미터 값의 적용과 서비스 응답 도착은 별개. 실제 부하/발견/transport 중 어느 것이 직접 원인인지는 이 증거로 확정할 수 없다. 두 Gazebo 및 대용량 image bridge 동시 시작을 분리하여 초기화 경쟁을 줄인다.

## 수정
- 이미 동일 source의 [L0/L1 CI 45938853689](https://github.com/silverbjin/samsung_AXI/actions/runs/45938853689) 150 PASS + 실제 dynamic set ACK/invalid rejection/entrypoint 증거를 재사용. R3a/b/c도 동일 source 회귀 SUCCESS. R4 CI 목적은 전체 실제 Nav2/직원 승인 연결이므로 fixture threshold 0.65/0.90을 ROS startup parameter로 명시한다.
- C/D 및 DDS 준비 후 **실제 get_parameters 응답**으로 양쪽 값을 검사하고 result.json에 기록. CI는 정확히 0.65/0.90만 인정. Owner는 실제 설치 C 기본값과 허용 범위 검증, GUI dynamic 설정 기능 유지. 응답 없는 경우 fail closed.
- 값 확인 후에만 독립 Gazebo station/bridge를 실행한다. 실제 RGB hash, 단독 /clock, 실제 Nav2 및 직원 승인 전 후속 Goal 0 조건 유지. 서비스 timeout을 단순 무시하거나 성공으로 승격하지 않는다.

## GREEN
새 SHA의 R4 CI 결과 및 artifact 검증 필요. 기존 model-free L1 및 R3은 보존. R4 full PASS / Owner L3 미판정.
