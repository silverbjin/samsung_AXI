> **최신 인계:** [E 최종 Owner station 인계](SMARTDISH_E_OWNER_STATION_FINAL_HANDOFF_20261127_KO.md) — R4 실제 3-leg CI PASS, 사용자 최종 실행 PIN/명령은 최신 문서만 사용. 아래는 R1/R2 개발 이력이며 과거 상태와 명령을 보존한 기록입니다.

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
export SMARTDISH_E_SOURCE_SHA=316639a0a5c47121f3026c76e180efde3cea12d4
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

## 검증된 PIN 및 CI

- E Owner 통합 검증 코드 PIN: `4dbdeca6a0a8f8120cb42a44bd589d356726eb5d` (문서 후속 커밋과 별개로 기능 코드는 이 SHA에서 L0/L1 확인됨).
- [최종 Actions #45929414512](https://github.com/silverbjin/samsung_AXI/actions/runs/45929414512): L0 131 PASS, L1 실제 DDS·C/D/A 3패키지·런치 인자 PASS.
- 필요한 비공개 모델 경로는 `SMARTDISH_C_V1_CHECKPOINT`로 사용자가 WSL2에서 직접 설정. **해당 파일 바이트 및 WSLg GUI, Nav2 3-leg AI ON L3는 이번 코드 CI에서 확인하지 않았으므로 미인수**.

## E-DBG-003 — 기존 C 실행환경 재사용 수정 (최신 권고)

- [E-DBG-003 교육 보고서](../reports/smartdish/e/E_DBG_003_C_RUNTIME_CONTRACT_HANDOFF_20261127_KO.md). C가 이미 구축한 `~/.venvs/smartdish-c-v1-py312-cpu`를 재사용하도록 실행기 수정. **신규 pip 설치/새 가상환경 구성 금지**.
- **새 실행 PIN: `316639a0a5c47121f3026c76e180efde3cea12d4`**, [Actions #45932168384](https://github.com/silverbjin/samsung_AXI/actions/runs/45932168384) **L0 146 PASS / Jazzy L1 3pkgs+DDS+fail-fast PASS**.
- `--preflight`에 C 가상환경 메타데이터·버전·C Python 및 ROS Python 양쪽 import 검증 추가. 실패 시 `E_OWNER_C_RUNTIME_BLOCKED=...`/exit2, GUI 실행 금지.
- 성공 시 `E_OWNER_C_RUNTIME_REUSED_VERIFIED`, `E_OWNER_AION_PREFLIGHT_PASS_OWNER_SCOPE_NO_GOAL`. 실제 C 로딩 시 `C_MODEL_LOADED version=resnet18-6afdcfe526e6 scope=OWNER_GAZEBO_INTEGRATION_ONLY` 확인 필요.
- 기존 `~/samsung_AXI_e_ai_on_v1`가 이전 인정 SHA `4dbdeca6...`이고 **clean**이면, 새 실행기는 명시된 신규 PIN이 원래 커밋의 자손인지 확인하고 Fast-forward 형태의 detach checkout만 허용합니다. 기존 작업에 수정 파일이 있거나 다른 SHA면 **안전 차단**합니다.
- C CPU venv가 없다면 E가 무단으로 재설치하지 않습니다. C 전용 설치기의 이전 인수 근거·기존 승인 범위를 확인한 후 C 담당 정책으로만 복구합니다.
- **현재 미완료:** 사용자 WSL2 실제 C runtime import / 모델 재로딩 / C 추론 / A+E L3. 기존 AI OFF L3는 PASS 재사용.
