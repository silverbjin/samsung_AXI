# SmartDish 제품 복구 공통 계약 v1.1.1 (2026-11-27; wire schema 2 unchanged)

상태: 개발 명세 승인용 문서 / 구현 및 신규 CI NOT_RUN. 이 문서는 제품 AI ON 승인서가 아니다. 기존 7토픽 계약의 하위 호환 확장으로, 신규 기능은 명시적 product recovery integration profile에서만 활성화한다.

## 1. 기준선 및 보호 경계
- 문서 작성 기준 main: `a64f54145762c88fd83ce237f4d494f4f0bb33f5`. S7 초기 식기 배치 PR #35, AI OFF L3 PR #44 (merge cc66b66a16ffc8020498d973ebe31a5c4ca439e0), A11~13 PR #45, C17~19 PR #60, D 계약 PR #63 모두 이미 main에 있다. 중복 병합 금지.
- E Draft #64 head `753cbb24c5a3d684461793731ee27fc540abd086`, 기존 기능 검증 PIN `77a1ae256cf4a008c8cefc16a32c43bfc40c7d08`. [R4 CI 45939257386](https://github.com/silverbjin/samsung_AXI/actions/runs/45939257386) actual Nav2 3/3 + 독립 station + CI double PASS. 이는 robot-mounted tray 제품 PASS가 아니다. R1/R2 실제 private model load PIN 316639a0a5c47121f3026c76e180efde3cea12d4 보존.
- Owner 2026-11-27 실행 검토: 초기 식기 누락, 로봇 장착 트레이/카메라 미구현, 독립 station 영상 사용, 직원 승인 대기 후 사용자 중단. 실제 모델 호출 성공은 별도 증거로 보존, 제품 L3 FAIL/HOLD. 원본 TAR/이미지/가중치 공개 금지. 사용자 언급 PNG는 TAR에서 확인되지 않았으므로 이미지 자체의 판정은 사용자 관찰에 한정.
- S7 원본 지도/월드/공식 Waffle, CM, Nav2, 기존 AI OFF 실행기, C17 product deny, C20 독립 연구, Test4 봉인, B 사람 라벨 및 권리 승인 보존. A14~18/B QA 연구 브랜치 일괄 병합 금지. 제품 통합 실험은 Owner Gazebo integration only; 모델 정확도 승격 아님.

## 2. 단일 월드 목표 시나리오
T03만 활성, HOME (0,0) → T03 (5.25,0.38) → DISH_RETURN (-1.15,1.60) → HOME: map 좌표는 기존 table_poses.yaml에서 읽는다. S7 table_3 월드 (2.65,-3.20), 기존 fixture (2.65,-2.91)는 map 좌표와 혼용 금지. 
1. 시작 시 T03 위 식기 1 stack, 로봇 트레이 empty. 초기 배치는 world_file에 명시한 generated SDF. 독립 station 금지.
2. 실제 Nav2 Goal 성공, odom 정지 검증 후 WAIT_LOADING 10초 (steady clock). 이후 LOAD 요청, 실제 동일 stack_id 식기 트레이 이동, pose/존재/중복/정지 확인 후 LOAD_ACK. 가상 직원 이동이며 로봇팔 Pick&Place 아님.
3. CAPTURING에서 로봇 장착 top view의 적재 완료 이후 신규 frame 1개 선택, capture ACK. AI_CHECK 1회, 동일 RGB SHA로 실제 C predictor 호출. camera는 준비 단계부터 streaming 가능, 추론 횟수는 1회. 
4. 유효 추론 결과 (STABLE/UNSTABLE/정상 호출 후 threshold 미달 UNKNOWN) 표시 및 직원 명시적 승인. 성능 면제는 Owner 실험 한정. invalid frame/model failure/timeout은 승인으로 우회 금지. APPROVE 이전 TO_RETURN 0건. ABORT/timeout → 안전 종료.
5. 실제 반납점 도착/정지, WAIT_UNLOADING 5초 후 UNLOAD, 로봇 트레이 empty 및 반납 위치에 식기 인계(또는 제거 영수증) 확인. UNLOAD_ACK 이후에만 TO_HOME. 정상 완료 시 UI COMPLETED. 식기 수량/ID 보존; 제거 방식은 반납 receipt로 추적.
6. 제품 복구 profile AI OFF는 선택 검증 범위: 같은 물리 LOAD/UNLOAD 계약을 따르되 C/capture/AI/staff 불필요. 기존 legacy AI OFF는 변경 없이 보존. 두 profile 혼용 금지.

## 3. 메시지 계약 (설계 명세)
기존 std_msgs/msg/String JSON reliable/volatile/keep-last10. 새 control 토픽도 동일. A/E bridge RGB는 sensor_msgs/msg/Image 640x480 rgb8/bgr8, 5Hz, reliable/volatile/depth10 (Owner 통합 A13 검증 방식); frame_id=smartdish_tray_optical, 유일한 로봇 장착 publisher, Gazebo→ROS only. 단일 /clock. D만 nav_goal과 transfer/capture/AI 요청 발행, A만 실제 nav_result/transfer_result/capture_result, C만 stability, UI만 staff_confirm/request, E/B 읽기 전용 witness. CI fixture는 격리 domain에서만.
모든 ID nonempty string <=128, schema_version=2 및 profile="OWNER_PRODUCT_RECOVERY"는 신규/확장 메시지 필수. 기존 legacy payload는 그대로 유지. request_id 임무 전체, stack_id 논리 식기 묶음, transfer_id 단계별 유일, capture_id 프레임별 유일. world_id=restaurant, run_id와 source_sha는 런타임 receipt에 고정. 실제 entity IDs와 stack_id 매핑 기록. 추가 JSON 필드는 legacy parser 호환 여부 L0에서 확인, 명시적 버전 선택 없이는 신규 경로 거부.

| topic | publisher → subscriber | payload 필수 필드 |
|---|---|---|
| /collection/request | UI→D | request_id,table_id,table_wait_s,dropoff_wait_s,ai_enabled (기존) |
| /collection/nav_goal | D→A | request_id,leg,destination_id (기존) |
| /collection/nav_result | A→D | request_id,leg,result,reason (기존), 신규 profile에는 goal_uuid, terminal_status, stop_verified 근거 추가 또는 동일 ID stop receipt |
| /collection/status | D→UI/E | request_id,state,table_id,remaining_s,reason; 추가 profile, stack_id,capture_id, action_allowed, ai_status,confidence,thresholds |
| /collection/dish_transfer_request | D→A | schema_version,profile,request_id,stack_id,transfer_id,operation=LOAD/UNLOAD,destination_id |
| /collection/dish_transfer_result | A→D | 공통 ID/operation, status=ACK/FAILED,reason,entity_ids,location=TABLE/ON_ROBOT/RETURNED/UNKNOWN,tray_count,table_count,receipt_sha256,event_sim_ns |
| /collection/capture_request | D→A | schema_version,profile,request_id,stack_id,transfer_id,capture_id,min_sim_stamp_ns |
| /collection/capture_result | A→D/C | 공통 ID,status=ACK/FAILED,reason,image_stamp_ns,frame_id,rgb_sha256,width,height,encoding,receipt_sha256 |
| /collection/ai_check_request | D→C | 기존 request_id,capture_id + 신규 profile/schema_version,stack_id,transfer_id,image_stamp_ns,frame_id,rgb_sha256 |
| /collection/stability | C→D/UI | 기존 request_id,capture_id,status,confidence,model_version + 신규 profile/schema_version,stack_id,transfer_id,image_stamp_ns,rgb_sha256,inference_ok,raw_status,raw_confidence,reason,stable_confidence_min,unstable_confidence_min |
| /collection/staff_confirm | UI→D | request_id,action=APPROVE_CONTINUE/ABORT; 신규 profile에는 capture_id,stack_id 및 schema_version/profile |
| /collection/nav_cancel_request (신규) | D→A | schema_version,profile,request_id,leg,goal_uuid,reason |
| /collection/nav_cancel_result (신규) | A→D | 같은 ID, status=ACK/FAILED, terminal_status,stop_verified,reason |

Capture는 A가 실제 RGB에서 선택한 frame을 지정; C는 stamp/frame_id/hash가 일치하는 canonical packed RGB를 bounded cache에서 찾아 사용. 새 frame으로 몰래 대체 금지. capture ACK 뒤 DDS 순서 경쟁 대비 C는 제한 시간 내 해당 frame을 기다릴 수 있으나 predictor 호출은 최대 1회. image stamp는 같은 Gazebo sim clock epoch만 비교; freshness=수신 monotonic <=2s, timeout=steady monotonic. sim reset/backward stamp는 invalid. bytes hash는 stride 제거 및 bgr→rgb 후 canonical RGB, PNG 파일 SHA와 별개. 모든 숫자는 finite; confidence null은 failure/threshold UNKNOWN의 기존 표현 허용, raw confidence는 정상 호출이면 보존. receipt는 canonical UTF-8 JSON sorted keys 및 실제 파일 SHA256, 외부 경로/개인 파일 금지. 동일 ID 동일 payload 재전송은 idempotent: 물리/추론 재실행 없음; 충돌 ID는 거부. ACK는 엔티티/pose/픽셀 실증 전 금지. ROS graph/ID만으로 암호학적 신뢰를 주장하지 않는다.

## 4. 안전·오류 처리
제안 초기 설정(실제 CI 실측 후 E 승인): 구간 이동 120s, 정지 확인 3s (|v|<=0.01m/s, |w|<=0.02rad/s 1s 연속), 초기 식기 확인 3s, LOAD/UNLOAD 각 20s (A 실제 9.79/7.20, 8.43/6.13, 8.374/7.097s 및 이후 10.640/7.734s 측정; E 승인), CAPTURE 5s, AI 5s, STAFF 60s. 10/5s wait는 최소값; wait 끝이 물리 ACK를 대체하지 않음. 각 상태 deadline은 메시지 수신 및 timer에서 검사. 늦은 ACK/승인 무효. no retry 기본; 수동 재시작은 초기 상태/식기 위치 확인 후 새 request_id. 
- EMPTY_TABLE, ROBOT_NOT_STOPPED, LOAD_FAILED, CAMERA_TIMEOUT, FRAME_INVALID, MODEL_UNAVAILABLE, INFERENCE_FAILED, AI_TIMEOUT, STAFF_CONFIRM_TIMEOUT, UNLOAD_FAILED, NODE_EXIT, NAV_FAILED/CANCEL_TIMEOUT 등 reason 코드. SAFE_HOLD는 진행 불가, action_allowed=false, no next goal. ABORTED/ERROR/CANCELED terminal 및 증거 보존. 기존 유효 상태와 reason 호환은 D가 문서화. 
- 활성 Goal이 있는 실패/사용자 중단: A만 실제 해당 UUID 취소, terminal 확인 후 odom zero. CM 경로 우회 금지. 취소/정지 불확실 시 SAFE_HOLD_UNVERIFIED, 신규 요청 금지, 명시적 운영자 조치 필요. 정지 단계 실패를 성공 종료로 포장하지 않음. 
- 직원 승인 60s countdown, UI 버튼 노출·활성 조건, ABORT 항상 가능한 안전 상태; 자동 진행 금지. 유효 추론 threshold UNKNOWN만 수동 판단 가능. hard failure의 승인/임계값 0 우회 금지. 
- thresholds Owner recovery 0.00~1.00, 기본 0.00/0.00 실험 권장; 기존 일반 모드/제품 floor 0.80 및 C17 deny 유지. 실제 C atomic set/get ACK, D가 해당 capture의 실제 threshold snapshot 검증; D 별도 고정 0.50 제거는 Owner profile만. NaN/Inf/bool/범위 밖 거부, 임무 중 설정 변경은 금지 또는 다음 임무부터 적용(본 명세는 잠금 선택).

## 5. 정량 검수 공통
L0 schema, SDF/world/map 보호, state transitions, exact once, failure/deadline, threshold boundary. L1 ROS Jazzy build + actual DDS/QoS/parameter ACK + installed origin. L2 실제 단일 Gazebo: 초기 엔티티/카메라, LOAD/UNLOAD 단독, 실제 3 Nav2 UUID SUCCEEDED/odom displacement>0.25m/scan+odom >=3 per leg/AMCL error<=0.8m, 실제 10/5s wait (관측 허용 0.3s), stop dwell, actual tray pose follows robot 이동 중 상대좌표 및 수량 검증, 실제 camera frame hash/1 inference, no goal before approval/after failure, CM ACTIVE 및 sole /cmd_vel publisher 시작/종료, /clock 1, UI 상태 및 clean exit. L2 CI double은 별도 모델 ID, private weight 없음. L3 WSL2 실제 v1 모델 + 실제 TTY/UI + 동일 single-world scenario, 시각 품질 owner 판단(자동 gate 아님). 
증거: source SHA, run ID, upstream SHA, generated world/robot/bridge/launch SHA, map, model receipt(가중치 제외), stack/entity lifecycle, world+relative pose, odom/scan/UUID, load/unload/capture receipts, PNG/hash+raw RGB hash, DDS events, actual predictor provenance, UI/staff causal log, process exit, first_error, tar+sha256. CI artifact expiry 고려해 요약/해시/Run ID를 MD로 보존. raw private checkpoint, dataset, Test4, 개인 경로 로그는 공개 커밋 금지.

## v1.1.1 E 승인 보완
- D의 CANCELING 15s (A 취소 10s + 정지 3s + transport margin 2s). 10/5s 대기는 물리 deadline 20/20s와 별개; D의 먼저 시작된 제한이 우선한다. 늦은 ACK는 무효.
- READY는 실제 A entity/정지/카메라/CM 관측과 receipt bytes/hash/source/run/stack 확인 후 D arm. 실제 accepted handle UUID만 D owning executor에 binding; pre-UUID ABORT/늦은 handle은 정확히 취소하고 terminal/stop 확인. 불확실하면 SAFE_HOLD_UNVERIFIED. ABORT의 capture_id 명시 null은 capture 전/AI OFF에만 허용. 실패 transfer unknown counts/IDs는 ACK 아님.
- B-QA-06: 동일 세션의 StopMonitor 입력 모든 odom callback, steady time, sim stamp, 실제 accepted/terminal/stop UUID, 10/5 wait와 20/20 deadline을 원본으로 출고. Decimated pose/receipt만으로 independent dwell PASS 금지.
