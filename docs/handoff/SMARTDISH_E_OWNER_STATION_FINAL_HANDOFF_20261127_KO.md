# SmartDish E — 최종 Owner WSL2 AI ON 독립 station 인계 (2026-11-27)

**상태: READY_FOR_OWNER_STATION_L3 / Owner 실제 L3 NOT_RUN / main 미병합.**

## 1. 고정 출고 기준
- 검증 코드 PIN: `77a1ae256cf4a008c8cefc16a32c43bfc40c7d08`
- 실행기 git blob: `aeee56cafc2d6867132e4155e807bf0fa43b153e`
- [R4 실제 Nav2 3-leg CI](https://github.com/silverbjin/samsung_AXI/actions/runs/45939257386) PASS, [L0/L1](https://github.com/silverbjin/samsung_AXI/actions/runs/45939257362) PASS.
- [실제 통합 검증 보고서](../reports/smartdish/e/E_R4_R5_FINAL_CI_ACCEPTANCE_EDU_KO.md).
- 기존 Owner R1/R2 실제 C CPU venv 및 checkpoint 로딩은 PIN 316639a0... 증거 재사용. 실제 station L3는 이 코드로 처음 실행.
- PR #64는 Draft. 기존 Restaurant survey 별도 CI가 남아 있다면 merge 전 결과 확인. 
- 범위는 로봇 주행 Gazebo + 독립 실제 tray station, 별도 Gazebo partition, 동일 DDS domain RGB-only. 로봇 장착 카메라·물리 안정성 검증 아님. C v1 성능 33.3% 면제는 내부 시뮬레이션 한정. 사용자 private weights와 Test4 공개/재평가 금지.

## 2. 사용자 1회 원샷 (새 WSL2 Ubuntu 24.04 터미널)
기존 SmartDish 실험과 C/D UI를 해당 실행 터미널에서 정상 종료합니다. 다른 사용자 프로세스 강제 종료 금지. 기존 ~/samsung_AXI 및 C 작업공간/venv는 유지합니다. GUI 기본; 기존 ROS/Gazebo/Nav2 의존성을 사용합니다. 실행기는 clean old Owner PIN 316639a0... 또는 4dbdeca6...에서 새 후손 SHA로만 안전하게 이동합니다. 수정된 작업 트리가 있으면 차단되며 reset/clean 금지.

```bash
(
  set -e
  export SMARTDISH_E_SOURCE_SHA=77a1ae256cf4a008c8cefc16a32c43bfc40c7d08
  export SMARTDISH_C_V1_CHECKPOINT="$HOME/smartdish_c_v1_p2_private/c_v1_frozen_head.pt"
  RUNNER="$HOME/smartdish_e_owner_station_77a1ae25.sh"
  curl -fsSLo "$RUNNER" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$SMARTDISH_E_SOURCE_SHA/scripts/smartdish_e_owner_aion.sh"
  test "$(git hash-object --no-filters "$RUNNER")" = aeee56cafc2d6867132e4155e807bf0fa43b153e
  bash -n "$RUNNER"
  bash "$RUNNER" --run-station
)
```

실행기 내부에서 모델 SHA(6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c), 크기 44786668 bytes, 기존 ~/.venvs/smartdish-c-v1-py312-cpu 및 ROS Python import 검증, per-PIN build/install, 설치 모듈 바이트, E-only CM launch graph 확인. 신규 pip/torch/venv 설치 없음. 기존 S7과 시스템 Nav2 원본 수정 없음.

## 3. 사용자 직접 조작
1. Gazebo/주행 환경이 준비되고 E_OWNER_CHECK_GAZEBO_AND_ENTER_A_TTY_APPROVAL_NO_GOAL가 출력되면 실제 화면 확인 후 A TTY 안내에 따라 `YES-SMARTDISH-A-GOALS` 입력. 자동 입력 금지.
2. E_OWNER_UI_READY_CLICK_T03_ENABLE_AI_10S_5S_THEN_STAFF_CONFIRM 출력 후 UI에서 T03, AI 검사 체크, 적재 10초/반납 5초를 선택하고 회수 시작. 임계값은 기본 사용 가능; 필요 시 UI에서 실제 ACK 확인. 기존 C17 제품 차단은 유지된다.
3. 실제 T03 도착, 적재 대기 후 실제 C v1 RGB 추론. STABLE/UNSTABLE/UNKNOWN 모두 직원 승인 이전 TO_RETURN 없음. 판정이 UNKNOWN이어도 raw predictor 정상 실행 여부와 이미지 해시가 증거에 있어야 한다. 실제 장면과 안전 확인 후에만 UI 직원 APPROVE_CONTINUE 클릭. 불확실하면 ABORT로 종료(성공 승격 금지).
4. DISH_RETURN 도착 → 5초 대기 → HOME 도착 → UI COMPLETED. witness가 완료를 감지해 소유 프로세스를 정리한다. 실행 중 기존 UI를 별도로 클릭하거나 새 요청을 중복 발행하지 않는다.
5. 최종 성공 후보 마커 E_OWNER_WSL2_AI_ON_STATION_L3_PASS, E_OWNER_STATION_EVIDENCE_VERIFIED_SCOPE_ONLY 및 rc0 확인. 화면 QA는 Owner 판단.

## 4. 제출 증거
터미널에 표시되는 E_OWNER_STATION_EVIDENCE=... 의 .tar.gz와 .tar.gz.sha256 두 파일을 제출합니다. 위치 ~/samsung_AXI_e_ai_on_v1/generated/smartdish_e_owner_station/<run>.tar.gz(.sha256). private checkpoint 자체는 포함되지 않는다. 
필수: result.json source_sha 일치, private_model_loaded=true, C real version resnet18-6afdcfe526e6/동일 request/capture/RGB SHA, UI 클릭 및 직원 승인 causal order, 3 actual UUID terminal SUCCEEDED, odom/scan/AMCL, 10/5 waits, 단독 CM 시작/종료, UI COMPLETED, rc. test4_opened=false, robot_mounted_tray_verified=false. 실패 시 원본 TAR/로그 그대로 제출, 즉시 강제 reset/clean 또는 무한 재시도하지 않는다. 
**실제 증거 검토 완료 전에는 Owner L3 PASS나 main merge를 선언하지 않는다.**
