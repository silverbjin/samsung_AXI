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

## 2026-11-27 실제 GREEN CI·재검증 근거

- **기능 구현 SHA**: `774a42914be6123ab89f71cee759b224ab1b72aa`.
- **DDS Probe/CI SHA**: `6f13810c1e9337bde37fc34414baf1544c393008`.
- **[Actions #45926489996](https://github.com/silverbjin/samsung_AXI/actions/runs/45926489996) — SUCCESS**.
- Ubuntu L0: 기존 D FSM/UI, E AI OFF witness 계약, C17 제품 차단, C inference freshness/중복, 신규 D-AION 테스트 포함 **92 PASSED**.
- ROS Jazzy L1: **3 packages finished** (`smartdish_service`, `smartdish_ai`, `smartdish_robot`); 설치 엔트리포인트 확인 완료.
- ROS DDS 실제 노드 검사: `D_AION_L1_D_MANAGER_CLI_TRUE_DENIED_NO_GOAL`, `D_AION_L1_C_MODEL_LESS_UNKNOWN_DUPLICATE_PASS_NO_GOAL`, `D_AION_L1_MODEL_LESS_DDS_PASS_NO_GOAL`.
- C는 이미지나 승인 모델 없이 실제 DDS로 `UNKNOWN/none`만 출력. D의 `--ai-available true`는 거부돼 `/collection/nav_goal` 0건.
- A 패키지는 **빌드만** 수행. Nav2/Collision Monitor/Gazebo/실제 T03 이동/WSL2 인수 **NOT_RUN**.
- 개발용 정적/ROS 계약 GREEN은 **`D_AI_ON_CONTRACT_ONLY_READY`**로 기록. 실제 AI ON 제품 적용은 **NOT_AUTHORIZED**.
- CI push `paths`로 이후 보고서만 갱신할 때 중복 L0/L1 실행을 줄입니다. 모델 성능·제품 인수는 CI 범위에서 제외됩니다.

## 위험 리뷰

현재 승인 모델 SHA와 E 제품 릴리스 승인 상수는 모두 `None`입니다. 따라서 C 모델 외부 공급자가 `STABLE` JSON을 보내도 ROS Manager에서 AI ON 미션을 시작할 수 없습니다. 향후 두 상수를 채우는 단순 코드 변경만으로 실제 안전·권리/성능 제품 승인이 성립하지 않습니다. E/PM은 릴리스 영수증 신뢰근원, 실 모델 SHA 검증 및 DDS 송신자 신뢰 경계를 **별도 승인/구현/인수**해야 합니다.
