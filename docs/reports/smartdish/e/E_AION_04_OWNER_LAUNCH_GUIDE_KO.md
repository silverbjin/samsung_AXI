# E-AION-04 — C+D Owner 전용 런치·UI 조작 안내

## 기본 방침
- 기존 smartdish_service.launch.py의 AI OFF 단독 런치는 변경하지 않음.
- 신규 smartdish_e_owner_aion.launch.py는 기본 owner_gazebo_integration=false, ai_available=false, model_path 빈 값. A/Nav2 및 Gazebo를 자동으로 띄우거나 Goal을 발행하지 않음.
- Owner 승인 내부 WSL2/Gazebo 통합에서만 owner_gazebo_integration:=true ai_available:=true 및 **실제 SHA가 검증될 private checkpoint 절대 경로**를 명시. 모델 파일은 GitHub에 업로드하지 않음.
- D Manager+UI가 같은 Owner opt-in을 요구하고 C node도 owner_gazebo_integration parameter로 별도 opt-in. 한쪽만 활성화하지 않음.
- UI가 표기하는 STABLE/UNSTABLE “판정 기준”은 각 클래스 confidence 최소 기준(0.50~1.00)이며, B의 라벨/GT, 실제 Gazebo contact force 기준은 변경하지 않음.
- UI 팝업에서 현재 C 값을 get_parameters로 조회하고 “ROS 2 판정 기준 적용” → set_parameters_atomically 호출. ACK 성공 후에만 UI 표시값·로그 변경. 진행 중 임무라면 변경 거부. C 서비스가 없다면 오류 및 기본값 유지.
- C ROS 노드의 로그에 C_DYNAMIC_THRESHOLD_APPLIED stable/unstable를 표시. 실제 요청별 로그에도 stable_min/unstable_min을 기록하여 교육 보고서의 판정 임계값 추적 가능.
- AI ON 결과가 STABLE이어도 D Owner 프로파일은 직원 승인 전 TO_RETURN 자동 Goal을 발행하지 않음. Timeout/UNKNOWN/UNSTABLE 역시 직원 확인 경계.
- A의 실제 Nav2/odom 통합은 별도 Owner E L3. 이번 CI의 DDS fixture는 실제 A navigation PASS가 아님.

## WSL2 Owner 사용 예시 (향후 실물 인수 전용, 이번 CI에서 미실행)
```bash
ros2 launch smartdish_service smartdish_e_owner_aion.launch.py \
  owner_gazebo_integration:=true ai_available:=true \
  model_path:=/path/to/private/c_v1_frozen_head.pt
```

## ROS CLI에서도 동적 기준 설정 가능
```bash
ros2 param set /smartdish_stability_inference stable_confidence_min 0.65
ros2 param set /smartdish_stability_inference unstable_confidence_min 0.90
ros2 param get /smartdish_stability_inference stable_confidence_min
ros2 param get /smartdish_stability_inference unstable_confidence_min
```

**주의:** 위 CLI 2회 갱신은 원자적인 쌍 변경이 아님. UI에서는 두 값을 한 번에 원자적으로 업데이트하며, 운영 절차상 임무 시작 전 IDLE 상태에서 적용. C17 제품 모델 기본 미승인 보호와 별도입니다.

## 훈련생 실습
1. 0.65/0.90 입력 시 STABLE 0.7과 UNSTABLE 0.7 중 어느 쪽이 UNKNOWN이 되는지 적으세요.
2. C 파라미터가 변경돼도 모델 weights와 미개봉 Test4가 변하지 않는 이유는?
3. D가 C 응답을 받았다는 것과 실제 Nav2 SUCCEEDED는 다른 증거라는 것을 설명하세요.
4. 실제 AI ON로 STABLE이 나와도 E Owner 프로파일에서 직원 승인이 필요한 이유는?
