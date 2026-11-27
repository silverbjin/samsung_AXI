# SmartDish E — Owner 승인 C v1 AI ON 통합 인계 (2026-11-27)

## 권한·성능 경계
- Owner는 기존 C v1 Validation 33.3%를 이번 제한 내부 Gazebo 통합의 차단 조건에서 면제했습니다. 성능 PASS가 아니며 C20 연구는 독립 유지.
- B 데이터 v1/원본 checkpoint는 외부 공개·재배포 금지. 사용자 프로젝트 내부 사용은 허가되지만, 제3자 pretrained weights 상업적 사용·재배포 권리는 별도 검토.
- C17 기본 제품 SHA=None 유지. Owner Gazebo 통합 프로파일과 정확한 SHA로만 동작.
- STABLE/UNSTABLE/UNKNOWN 어느 결과라도 D는 직원 APPROVE_CONTINUE 또는 ABORT 전에는 TO_RETURN Goal 발행 금지.

## WSL2 사용자 사전 검수
- 독립 경로 ~/samsung_AXI_e_ai_on_v1를 사용하고 기존 ~/samsung_AXI 및 AI OFF/A/B/C 작업 공간을 보존합니다.
- 완료된 CI의 SHA와 private checkpoint 절대 경로를 지정해 아래 명령 사용. 실제 C 체크포인트 파일은 공개 GitHub에 업로드하지 않습니다.

```bash
export SMARTDISH_E_SOURCE_SHA=<최종-검증된-40자리-GitHub-HEAD>
export SMARTDISH_C_V1_CHECKPOINT=/absolute/private/path/to/c_v1_frozen_head.pt
curl -fsSLo "$HOME/smartdish_e_owner_aion.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$SMARTDISH_E_SOURCE_SHA/scripts/smartdish_e_owner_aion.sh"
bash -n "$HOME/smartdish_e_owner_aion.sh"
bash "$HOME/smartdish_e_owner_aion.sh" --preflight
bash "$HOME/smartdish_e_owner_aion.sh" --run-ui
```

## 실제 통합 순서
1. **별도 A 작업환경**에서 기존 Gazebo/Nav2/AMCL/scan/odom과 TTY 사용자 승인을 완료한 후 smartdish_navigation_adapter가 실제 Goal 구독자가 되었는지 확인. A 단독 3-leg 시연은 동시에 실행 금지.
2. E 스크립트 --preflight가 실제 checkpoint SHA를 계산해 고정 E SHA와 비교한 뒤, --run-ui에서 C+D만 빌드/실행.
3. C 로그의 C_MODEL_LOADED scope=OWNER_GAZEBO_INTEGRATION_ONLY 또는 C_MODEL_UNAVAILABLE를 구분. 모형이 없거나 SHA가 다르면 승인된 AI ON 실증으로 승격 금지.
4. UI에서 AI ON 체크, T03 선택 전 STABLE/UNSTABLE 각각의 confidence 최소값(0.50~1.00)을 변경하고 ROS Parameter ACK 확인. B GT label이나 C weights는 바뀌지 않습니다.
5. 동일 request_id/capture_id로 실제 C 결과·threshold·5초 timeout·직원 APPROVE_CONTINUE/ABORT, A Nav2 3 leg/odom·D 10초/5초·UI COMPLETED 수집.
6. STABLE도 직원 명시 승인 전 TO_RETURN 이동 금지. UNKNOWN/UNSTABLE/TIMEOUT에서도 승인 전 Goal 없음. ABORT 시 Goal 없음.
7. 실제 비공개 모델 및 Gazebo WSL2 Owner 인수 TAR+SHA256 증거가 있어야 E_OWNER_AION_L3_PASS 판정. CI만으로 승격 금지.

## 개발/CI 분리
- 공개 GitHub CI: synthetic predictor/모델 없는 실제 DDS dynamic ROS parameters, D manual confirmation, C17 기본 차단, 기존 D/E AI OFF 회귀. Nav2 실주행 없음.
- private WSL2 인수: exact model bytes SHA, torch.load 후 C 실제 이미지 추론, A+D/E 3 leg 및 Owner UI 시각 QA.
- 제3자 라이선스 및 실물 로봇 적용은 별도 권리·안전 평가 필요.
