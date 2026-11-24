# SmartDish MVP — A/B/C/D 통합 인수 및 교육용 개발 보고서

작성: 2026-11-24 / 책임: E 통합 / **결론: AI OFF 실제 WSL2 L3 PASS / PR #44 main 배포 승인 (AI ON 별도 HOLD)**

## 1. 출처와 검증 대상
- 기준: S7 main SHA **2dd7f968dd3d24e2afb48e0917ef8c9d054ac894**, PR [#35](https://github.com/silverbjin/samsung_AXI/pull/35).
- 계약: 첨부 SmartDish MVP Interface Contract v1.0, S7 Baseline and Gap, Interface Adoption, Timeline Handoff QA, 4 Developer Integration Diagram Guide.
- GitHub 각 브랜치의 docs/handoff/A_HANDOFF.md, B_HANDOFF.md, C_HANDOFF.md, D_HANDOFF.md 원문과 PR 변경 목록/독립 CI 작업 로그를 조회했습니다.
- 원격 main은 E 시작 시 동일 S7 SHA; A/B/C/D 네 브랜치 모두 이 SHA를 조상으로 포함하고 base 대비 behind=0입니다.

| 순서 | 담당·원본 Draft PR | 정확한 병합 소스 HEAD | 실제 확인된 테스트 | 최종 한계 |
|---|---|---|---|---|
| 1 | A [#36](https://github.com/silverbjin/samsung_AXI/pull/36) | ac4658995178e75c04d357ccc09f9b5373dfb61b | [A L0/L1 #45132684464](https://github.com/silverbjin/samsung_AXI/actions/runs/45132684464); [실 Gazebo L2 #45125551884](https://github.com/silverbjin/samsung_AXI/actions/runs/45125551884); A-09 실제 WSL2 GUI 3-leg | ROBOT_ONLY; D 연계 NOT_RUN |
| 2 | D [#38](https://github.com/silverbjin/samsung_AXI/pull/38) | fc8cca152ca669376294c840bec014c0b14fba3d | [D L0/L1 #45132582965](https://github.com/silverbjin/samsung_AXI/actions/runs/45132582965); 사용자 IDLE GUI 화면 시각 검수 | 실제 D→A→UI NOT_RUN |
| 3 | B [#37](https://github.com/silverbjin/samsung_AXI/pull/37) | 7650911e1fe798765c6b7ebab7583d420192fef6 | [B L0 #45127237026](https://github.com/silverbjin/samsung_AXI/actions/runs/45127237026), 30 PASS | 실제 데이터 0건, 6 mock fixtures |
| 4 | C [#39](https://github.com/silverbjin/samsung_AXI/pull/39) | 271e4017e18ff2c74819ea173ae41e816ec6e480 | [C L0/L1 #45126686463](https://github.com/silverbjin/samsung_AXI/actions/runs/45126686463): 40 PASS 및 ROS DDS UNKNOWN 2건·중복 0건 | 실제 모델/영상 NOT_RUN; 검증 후 HEAD 변경은 문서 3개뿐 |

## 2. 통합 작업 이력

독립 브랜치 **integration/smartdish-mvp-20261209**를 지정된 S7 베이스에서 생성했습니다.

| 단계 | GitHub 통합 | Merge commit | 설명 |
|---|---|---|---|
| A | [E01 PR #40](https://github.com/silverbjin/samsung_AXI/pull/40) | b1e01434d30548d63225d31801aab14bfcf7f594 | 정상 GitHub merge |
| D | [E02 PR #41](https://github.com/silverbjin/samsung_AXI/pull/41) | 3713839ca04297f6176182825b6fd9d017f59b7b | 정상 GitHub merge |
| B | [E06 PR #42](https://github.com/silverbjin/samsung_AXI/pull/42) | 1c79869f29fe53fd68fee6a2058271122966751c | 충돌 교육 로그 보존, B를 2번째 부모로 정상 Git merge |
| C | [E07 PR #43](https://github.com/silverbjin/samsung_AXI/pull/43) | 88356b8d93cf65df7944ec6668c128deac20c46f | 충돌 교육 로그 보존, C를 2번째 부모로 정상 Git merge |

**E-DBG-01 — 교육 로그 충돌**: B/C PR의 자동 병합은 docs/DEVELOPMENT_LOG.md의 병렬 추가 부분이 충돌하여 거부되었습니다. 비교 API에서 나머지 변경이 추가 파일임을 확인한 뒤, 공통 S7 접두부를 보존하고 A 기록 뒤 B/C 추가분을 각각 이어 붙인 새 트리를 만들었습니다. 양 부모 merge commit과 기대 HEAD non-force ref 갱신을 사용했으며 원본 학습 이력은 버리지 않았습니다. PR #42/#43은 실제 GitHub에서 merged=true를 확인했습니다.

## 3. 수정 파일과 단일 책임
- A: src/smartdish_robot 및 config/table_poses.yaml; HOME(0,0,0), T03(5.25,0.38,-1.57079632679), DISH_RETURN(-1.15,1.60,-1.57079632679), 좌표계 map.
- D: src/smartdish_service (UI 픽셀 도면과 실 NAV 좌표 분리). E가 UI 실제 클릭·적용 콜백의 증거 로그만 2줄 추가했습니다.
- B: ai/data/manifest.csv, ai/data/split_manifest.csv, Dataset Card, collect/prepare pipeline. 실데이터 0건.
- C: src/smartdish_ai 및 ai/train, ai/evaluation. 배포 가능한 안정성 가중치 없음. AI OFF 기본 유지.
- E 신규: scripts/smartdish_e_live_witness.py (ROS 읽기 전용 인수 감사), scripts/smartdish_e_wsl2_one_shot.sh (실행·PID 정리), scripts/smartdish_e_wsl2_bootstrap.sh (고정 SHA), tests/test_smartdish_e_contract.py, .github/workflows/smartdish-e-integration-ci.yml.

**S7 원본 보호**: 실제 GitHub compare에서 scripts/s7_scene.py, scripts/s6_vision_ai.py, scripts/samsungaxi_s7_wsl2_l3_once.sh, tests/test_s7* 및 원본 restaurant world의 변경은 **0건**입니다. Nav2/AMCL/Collision Monitor/최종 cmd_vel 기존 경로, 수동 TTY 보호를 제거하지 않았습니다.

**계약**: 프로젝트 JSON 7토픽(/collection/request, /collection/nav_goal, /collection/nav_result, /collection/status, /collection/ai_check_request, /collection/stability, /collection/staff_confirm)은 std_msgs/String, QoS RELIABLE/VOLATILE/KEEP_LAST(10). 좌표는 A만, 상태·시간은 D만, 추론은 C만 소유합니다. 새 Planner/Supervisor/custom msg/cmd_vel 발행은 없습니다.

## 4. AI OFF 실제 E 인수 시퀀스

    E witness 구독 시작 (NO_GOAL)
      → 기존 S7 restaurant_bringup Nav2/Gazebo/AMCL Map
      → A Adapter: /scan·/odom + Nav2 ACTIVE → 운영자 /dev/tty 승인 → SMARTDISH_A_READY
      → D UI + Manager AI OFF, WSLg GUI
      → 운영자 직접 T03 클릭(요청 ID 1개, 10초/5초)
      → TO_TABLE/T03: 실제 SUCCEEDED+odom → WAIT_LOADING (성공 후 10초)
      → TO_RETURN/DISH_RETURN: 실제 SUCCEEDED+odom → WAIT_UNLOADING (성공 후 5초)
      → TO_HOME/HOME: 실제 SUCCEEDED+odom → /collection/status COMPLETED
      → UI on_status() 적용 로그 SMARTDISH_D_UI_APPLIED state=COMPLETED
      → E witness 결과와 화면 콜백 교차 점검 → ZIP 출고

E 관측기는 goal/result를 발행하거나 성공을 합성하지 않습니다. 최종 PASS 직전 A Adapter 원본 로그의 NAV_GOAL_SENT·NAV_RESULT와 D Manager 원본 로그의 /collection/nav_goal 3건을 동일 request_id로 대조하고 A의 odom 변위도 확인합니다. 실패 발생 시 first_error를 기록하고, UI↔D, D↔A, A↔Nav2, Gazebo·TF 중 **최초 문제 한 경계**만 수정하도록 로그를 분리합니다. 종료는 자기 실행기가 실행한 PID/프로세스 그룹에만 신호를 보냅니다.

### 사용자 WSL2 GUI 원샷 절차

최종 검증 통합 HEAD를 PIN으로 고정하고 WSL2 Ubuntu 대화형 터미널에서 아래 명령을 실행합니다. 최종 SHA는 이 보고서 생성 이후 통합 PR 최신 HEAD를 확인하여 발행합니다.

    PIN=<E_FINAL_SHA>
    curl -fsSLo "$HOME/smartdish_e_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_e_wsl2_bootstrap.sh" &&
    SMARTDISH_E_SOURCE_SHA="$PIN" bash "$HOME/smartdish_e_bootstrap.sh"

전용 ~/samsung_AXI_E가 이미 있으나 PIN이 다르면 **기존 로컬 코드를 reset하지 않고 즉시 차단**합니다. 새 쉘에서 기존 디렉터리를 안전하게 확인하거나 별도 작업 폴더에 설치하십시오. 현장에서는 TTY에 **YES-SMARTDISH-A-GOALS**를 직접 입력하고 UI T03 버튼을 직접 클릭합니다. GUI 기본, AI OFF, 10초/5초입니다.

성공 표식은 **SMARTDISH_E_AI_OFF_WSL2_L3_PASS**. 그렇지 않으면 HOLD입니다. ZIP: ~/samsung_AXI_E/generated/smartdish_e/<run_id>/smartdish_e_owner_evidence.tar.gz. summary.json, live_evidence.json, adapter/service/observer/nav2/build 로그를 제공합니다. 반드시 동일 request_id, NAV_RESULT SUCCEEDED 세 건, odom 이동, 10/5초 구분, UI COMPLETED 적용을 대조하십시오.

**초기 출고 당시 E WSL2 L3 결과: NOT_RUN (아래 8절에서 현장 PASS로 갱신)**. A 단독 실증과 E 합성 테스트를 E 실제 인수 PASS로 대체하지 않습니다.

## 5. AI ON 선택 기능 상태
- B의 label_map: STABLE=0, UNSTABLE=1. UNKNOWN은 판정 실패 상태로 학습 클래스가 아닙니다.
- 기존 S7 STACKED/NOT_STACKED는 식기 존재 여부이며 안정성 라벨과 다릅니다.
- A 트레이 지향 RGB /smartdish/tray/image_raw 실제 센서 미검증. 기본 전방 카메라가 트레이를 본다고 가정 금지.
- C 실물 학습/weight/model SHA/정확도/F1: NOT_RUN. 모델 없는 ROS DDS UNKNOWN 경로만 독립 검증.
- D ai_available=false 기본, UI AI 토글 비활성화. 향후 UNSTABLE/UNKNOWN/timeout은 NEEDS_CONFIRMATION, 직원 APPROVE_CONTINUE 또는 ABORT.
- DACON ZIP 다운로드 및 사용/재배포 약관 확인 NOT_RUN. 무단 원본 공개 금지; 합성 fixture는 MOCK_ONLY.

## 6. 테스트·릴리스 판정

- A robot-only 실제 3-leg: 기존 CI/현장 범위에서 PASS.
- D L0/L1 및 사용자 IDLE 화면: 원래 범위에서 PASS.
- B/C 독립 계약 테스트와 C 모델 없는 DDS: 원래 범위에서 PASS.
- E 신규 CI: [통합 E workflow](https://github.com/silverbjin/samsung_AXI/actions/workflows/smartdish-e-integration-ci.yml) — Python A/B/C/D 관련 계약과 ROS Jazzy 3패키지 빌드, NO_GOAL; 반드시 최종 커밋의 결과를 검사.
- E 실제 AI OFF UI 3구간: **WSL2_L3=PASS** (8절 현장 원본 검수).
- main 릴리스: PR #44의 현장 승인 조건 충족. 실제 병합 커밋과 상태는 [PR #44](https://github.com/silverbjin/samsung_AXI/pull/44) 참조.
- 기능 동결 2026-12-07, 리허설 12-08, 발표 12-09. RTF 90%, UI 셰이더, 3회 반복, 모든 테이블, 모델 고도화, HW E-stop은 MVP 필수에서 제외합니다. SW STOP은 인증 HW E-stop이 아닙니다.

## 7. 주니어 개발자 학습 핵심

1. 독립 CI PASS와 End-to-End 실제 PASS는 서로 다릅니다. A Gazebo+odom 성공과 D 합성 상태머신 성공을 단순히 더해 실제 UI 완료라고 보고해서는 안 됩니다.
2. ROS2 pub/sub QoS/토픽과 request_id/leg/capture_id는 팀 경계에서 계약입니다. D는 Nav2 SUCCEEDED를 만들지 않습니다.
3. 브랜치 충돌은 역사 손실 없이 merge commit의 양 부모와 공통 접두부 보존으로 해결해야 합니다.
4. CI 첫 실패는 코드/환경 경계를 확인한 뒤 좁은 범위에서 조치합니다. 실제 Gazebo 반복이나 테스트 비활성화로 녹색을 만들지 않습니다.
5. 현장에서는 첫 오류, SHA, 실제 Nav 결과, 이동, UI applied를 남겨 후속 인수가 문서만으로 추적 가능해야 합니다.

**최종 현장 판정: SMARTDISH_MVP_AI_OFF=PASS, AI_OFF_WSL2_L3=PASS, AI_ON=NOT_READY. main 배포는 PR #44에서 추적.**


## 8. 2026-11-24 — E 실제 WSL2 L3 인수 완료

- 원본: smartdish_e_owner_evidence.tar.gz, SHA256 9cb248c55331c0cf6b526dff2d1990053329e2d4a67f6c75f1c429fc3873af16. 사용자 원본 보관; 공개 저장소에는 개인 환경 로그 대신 비식별 검수 요약만 기록.
- 실행 SHA: efedaf38aca421bcdd3056584483b9a85f00ba8b. UTC 완료: 2026-11-24 00:59:48. request_id REQ-0a470b5448f4. 실제 UI 클릭 1건, AI=false, 대기 10/5초, EXPLICIT_TTY 및 Nav2/scan/odom readiness 확인.
- A Adapter 원본 goal/result 3건과 D Manager goal 3건, 독립 observer, UI APPLIED COMPLETED가 동일 ID로 일치. Nav2 lifecycle collision_monitor 활성화 기록 존재. 새 CM STOP fault 실험은 수행하지 않음.

| leg | 실제 Nav2 | 이동 시간(s) | 최대 odom 변위(m) | odom 샘플 | scan 샘플 |
|---|---|---:|---:|---:|---:|
| TO_TABLE/T03 | SUCCEEDED | 22.464 | 5.256 | 672 | 135 |
| TO_RETURN/DISH_RETURN | SUCCEEDED | 30.166 | 6.529 | 933 | 187 |
| TO_HOME/HOME | SUCCEEDED | 19.248 | 1.950 | 550 | 110 |

- 실제 결과 수신 → 다음 Goal 관측: 10.020s 및 5.037s. 첫 Goal → 최종 COMPLETED: 86.934s. 대기 카운트다운 및 UI applied 확인. 원본 summary exit_code=0, live verdict AI_OFF_REAL_RUN_PASS.
- 요약 first_error=UNVERIFIED는 live_evidence.first_error=null 및 exit_code=0과 불일치. 성공 시 빈 오류를 UNVERIFIED로 채우는 요약 출력 결함으로 분리. 종료 SIGINT 이후 ROS context wait set 및 UI/Manager traceback은 종료 백로그. 성공 이전에 실패한 주행 증거 없음. 사용자 시각 QA 정책 유지. 정지 속도 별도 정량화/스크린샷은 이번 첨부에 없음.
- 동일 실행 SHA의 실제 CI: [E PR #45298546837](https://github.com/silverbjin/samsung_AXI/actions/runs/45298546837) L0 117 PASS/L1 SUCCESS, [E Push #45298541121](https://github.com/silverbjin/samsung_AXI/actions/runs/45298541121) SUCCESS; [기존 Restaurant CI #45298546824](https://github.com/silverbjin/samsung_AXI/actions/runs/45298546824) SUCCESS; A #45298546676, B #45298546555, C #45298546764, D #45298546714 모두 SUCCESS.
- 이번 기록은 문서만 변경; 위 실행 SHA의 런타임 파일은 그대로 유지. PR #44에서 main merge SHA 추적. 기존 S7 보호 자산 회귀 변경 없음. 사용자 main 배포 승인 확인.

## 9. AI ON 후속 통합 (새 main 기준선에서 별도 작업)

A+B: 트레이 전용 RGB 카메라와 물리적으로 관측 가능한 적재 fixture (기존 S7 world/센서 경로 보존) → B 실 프레임/독립 물리 기록 수집 → 사람 라벨·사용권 검토 → stack_id 그룹별 train/val/test 분할 (클래스별 독립 그룹 최소 3개는 파이프라인 하한이지 성능 기준 아님) → B 데이터 버전, 품질 보고서, manifest SHA 인계. 원본 파일은 승인된 비공개 저장소에 보관. B 현재 manifest 0행, split 0행; B08R/B09까지 계약 구현과 CI 30 PASS. B 코드는 이미 병합 대상이며 원래 브랜치 전체를 다시 병합할 필요 없음.

C: B 최신 버전 read-only readiness → 운영자 실제 라벨/권리 승인 → ResNet18 frozen baseline → layer4+fc fine-tuning → validation 기준 모델/threshold 선정 → untouched test Accuracy/Macro-F1/confusion matrix 및 오류 샘플 → PHYSICS_OBSERVED checkpoint/SHA/Model Card → A 실제 RGB로 DDS 추론. C08 40 PASS 및 no-model UNKNOWN 2건/중복 0건 보존. model_path 현재 빈 문자열; mock checkpoint 운영 금지.

D+E: 실제 트레이 RGB+모델+동일 request_id/capture_id 계약 검증 → STABLE 진행, UNSTABLE/UNKNOWN/timeout 직원 승인/중단 분기(승인 전 추가 Goal 금지) → 선택 AI ON 실제 시나리오 1회 및 AI OFF 회귀 → 새 통합 PR. 준비 미완료 시 12/07 동결은 AI OFF baseline으로 유지. 12/08 리허설, 12/09 발표. 안전 인증 주장 금지.
