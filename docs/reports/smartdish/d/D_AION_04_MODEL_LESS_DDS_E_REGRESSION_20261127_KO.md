# D-AION-04 — 실제 ROS Jazzy DDS model-less UNKNOWN 및 기존 AI OFF 회귀

- 환경: GitHub Actions Ubuntu 24.04 L0, `ros:jazzy-ros-base-noble` L1.
- 테스트: `tests/test_smartdish_d_aion.py`, 기존 `test_smartdish_d_service.py`, `test_smartdish_d_ui.py`, `test_smartdish_e_contract.py`, `test_c17_product_model_admission.py`, `test_c_stability.py`. **실제 E L3 재실행 금지**, 이전 PASS 재사용.
- L1: `smartdish_service`, `smartdish_ai`, `smartdish_robot` 기존 패키지를 새 도구로 재작성하지 않고 colcon build. `scripts/smartdish_d_aion_ros_probe.py`는 **두 실제 ROS 2 노드**(D Manager와 C model-less Inference)와 안전 관측자만 띄웁니다.
- D Manager는 `--ai-available true`라도 E 모델 승인 없음 → `AI_NOT_AVAILABLE`, Nav Goal 0개.
- C는 모델·트레이 RGB 없이 합성 `ai_check_request`를 받아 `UNKNOWN/confidence:null/model_version:none` 1건을 반환, 동일 ID 재요청 중복 억제.
- ROS 2 QoS: 7토픽 String(RELIABLE/VOLATILE/KEEP_LAST_10), 영상 계약(sensor_data QoS) 수정 없음. DDS 관측에서 Nav2 Action 및 Gazebo/WSL2를 절대 구동하지 않음.
- **D-AION-GATE:** `D_AI_ON_CONTRACT_ONLY_READY`. C 모델 Val33.3% 및 B 연구 데이터 18건으로 제품 AI ON 승격 금지.
- 인수 근거: 최종 CI Run/소스 HEAD 확인 후 본 보고서/PR 갱신. L0 synthetic과 L1 DDS UNKNOWN의 실제 인수 경계 구분.
- 조치 정책: 첫 실패→로그 원본→원인 격리→필요 최소 CI/코드 수정→L0/L1 재검. 반복 사용자 WSL2 실행은 요청하지 않음.
