# SmartDish A → E — WSL2 GUI 현장 인수 이후 MVP 통합 실행 계획 (2026-11-23)

## 0. 기준선과 성공을 재사용하는 원칙

- S7 `main`의 검증 기준 SHA: `2dd7f968dd3d24e2afb48e0917ef8c9d054ac894`. **현 단계 main 직접 병합 금지**.
- A Draft PR #36: `feat/smartdish-a-robot`, A-09 운영자 WSL2 GUI real Gazebo 3 leg **PASS**. 현장 실행 SHA `2ec54a0ea91566a1bd100aab569f25589dff3f05`.
- A-10의 GUI 기본값 변경은 `7d110ece67096151daff7bf351420952b18a9a66`부터 적용; Nav2/CM/지도/Goal 변경 없음.
- D Draft PR #38: `feat/smartdish-d-service`, 현재 헤드 확인 시 `4cc64bbc05f769c06d93ba055f03a12e75a601de`; MissionManager·Tk UI·7토픽과 L0/L1. **A+D 실주행 NOT_RUN**.
- B Draft PR #37 / C Draft PR #39: AI ON 선택 기능, 실제 승인된 식기 안정성 이미지·라벨·학습 모델이 현재 준비되지 않음. 우선순위에서 A+D AI OFF보다 뒤에 둡니다.
- 기존 A의 단독 3-leg 실주행과 기존 S7의 지도 생성/저장·CM을 재실행하지 말고 증거를 인계합니다. 통합에 새 물리 제어 변경이 생긴 경우에만 해당 경계를 좁혀 재검합니다.

## 1. MVP AI OFF 단일 사용자 시나리오

```text
[WSL2 GUI] Gazebo + Nav2/AMCL + A Adapter
    ├─ 실물 /scan + /odom + map/TF 준비
    └─ 운영자 /dev/tty 직접 승인 → /collection/nav_goal 구독 READY
                                │
                           D Manager + Tk UI
                                │
                     [T03 선택 + Start 버튼]
                                │
         /collection/request (request_id, ai_enabled=false,
                table_wait_s=10, dropoff_wait_s=5)
                                │
                  D Manager 상태 머신
                                │
     TO_TABLE / T03 → A Nav2 SUCCESS + odom 검증
                                │
              WAIT_LOADING (steady 10초)
                                │
     TO_RETURN / DISH_RETURN → SUCCESS + odom
                                │
             WAIT_UNLOADING (steady 5초)
                                │
          TO_HOME / HOME → SUCCESS + odom
                                │
          /collection/status COMPLETED + Tk UI 반영
```

A는 실제 `/collection/nav_result`를 발행합니다. D가 가상 Result를 만들거나 테스트 fixture를 운영 경로에 혼용해선 안 됩니다. 한 요청에는 같은 `request_id`를 사용하고 구간별 결과를 3개 검증합니다. `AI OFF`에서는 C 구독·실모델이 필수가 아닙니다.

## 2. 단계별 독립 작업·차단 조건

| 순서 | 담당 | 구현/검증 | 완료 근거 | 성격 |
|---|---|---|---|---|
| E-00 | 통합 담당 | S7 main으로 별도 E 작업 브랜치 생성, A/D Draft HEAD 고정 및 소유 경계 비교 | 통합 SHA·충돌 기록·기존 성공 CI 목록 | 개발 시작 |
| E-01 | E+D | D 인계의 오래된 `DISH_RETURN=null` 또는 `A 3-leg BLOCKED` 단락을 A-09의 운영 YAML와 실 L3 근거로 정정 | 같은 실제 좌표와 토픽·QoS 계약 확인 | 문서/계약 |
| E-02 | E | A 및 D 소유 파일을 통합 브랜치로 합치되 S7 ROS World/Nav2/Collision Monitor 소스는 보존 | `colcon` A+D 2패키지 discovery, L0 계약/실패 테스트 | 정적+ROS |
| E-03 | E+D | 실제 A READY 및 D Goal 구독 준비 순서, `VOLATILE` 전송 전 subscriber 검사 | `ADAPTER_NOT_READY_NO_GOAL` 차단과 READY 성공 로그 | 안전 가드 |
| E-04 | E+D | Tk UI T03 주문 1건, `AI OFF`, 10초/5초 steady, 3 leg 같은 ID, 최종 `COMPLETED` | 원본 요청/상태/result/odom 시간표본/최종 화면 상태 | **A+D 통합 현장 L3 한 번** |
| E-05 | E+D | Tk UI 좌측 도면·오른쪽 타이머 잘림(D07) 사용자 시각 확인 | 사용자 육안 판정 (자동 게이트 불포함) | 선택 QA |
| E-06 | E | 최초 실패가 있으면 해당 경계 최소 수정→L0/L1→필요한 경우 E-04 단일 재검 | RED/GREEN 원본과 SHA·교육용 디버깅 보고서 | 회귀 |
| E-07 | E | A+D AI OFF MVP 인수 보고, 충돌 및 역할 인계, 통합 PR Draft 검수 | `AI_OFF_REAL_RUN_PASS` **증거 기반** | 전체 통합 |

독립 A Gazebo 3-leg PASS와 새 E-04 실제 D 시연 PASS를 합치면 `A+D` 실제 서비스 흐름이 성립합니다. A-09 단독 성공만으로 UI 완료를 주장하지 않습니다.

## 3. 병렬로 진행 가능한 작업

- **D**: 사용자 지적 UI 잘림의 수정본 D07 WSLg 재확인, 불필요한 신규 UI 기능 추가 금지. FSM 10초/5초 steady clock, request_id/중복/이탈 처리의 기존 51개 L0 성과 재사용.
- **B**: 실 데이터 0건 해소를 위한 트레이 이미지 사용권/물리 증거/라벨 확보, raw/manifest/split/quality 보전. A+D AI OFF 완료를 기다릴 필요 없음.
- **C**: 실제 모델 부재 시 `UNKNOWN` fail-closed DDS 계약 검증 성과 유지, B 실제 승인 데이터 준비 후에만 frozen→fine-tune→독립 test 평가.
- **A**: World/Nav2/CM/Goal은 변경하지 않음. 트레이 카메라가 필요해질 때만 신규 A 담당 단위로 별도 범위 한정.

## 4. 일정 (D PM의 기존 일정과 조율)

| 목표 | 마감 기준 | 현재 판단 |
|---|---|---|
| A↔D T03 실제 연동 | 11/25 목표 | **이제 A 좌표 차단 해소**, E 착수 가능 |
| AI OFF 전체 3-leg UI 성공 1회 | 12/02 | 최우선 인수 |
| 기능 동결 | 12/07 | B/C 지연 시 AI OFF로 고정 |
| 강사 리허설 | 12/08 | 동일 SHA/동일 원샷, 영상 백업 |
| 발표 | 12/09 | 실증 가능한 증거만 제시 |

## 5. 인수 증거 체계와 과장 방지

- `A_ROBOT_ONLY_WSL2_L3_PASS`: **이미 완료**, A-09 원본 tar 검수/ SHA 있음.
- `AI_OFF_REAL_RUN_PASS`: **NOT_RUN**, D Manager의 실제 request_id/시간 대기/COMPLETED 결합 필요.
- `AI_ON_OPTIONAL_PASS`: **NOT_RUN**, B 실 데이터·C 실모델·A tray RGB·D 직원 승인 조건 충족 필요.
- UI 시각 품질: **사용자 검수**, CI 자동 안전 게이트 아님.
- 데이터/모델 지표와 물리 이동을 서로 섞어 PASS 판정하지 않습니다.
