# R02-3 — RGB(t0) 생산 수집기 통합 (교육용)

## 목표
R02-2의 metadata challenge를 실제 A13/A14 warmup → dish spawn → RGB t0 → 10 simulated seconds 경계에 통합한다. 기존 원본 파일을 수정하지 않고 별도 opt-in entry point가 process-local hook으로 runtime SDF에 observer만 추가한다. 기존 생산 SDF와 dish spawn 파일의 hash를 보존하고 runtime SDF hash/manifest만 갱신한다. A13/AI OFF와 기존 실행 경로를 변경하지 않는다.

## 데이터 계약
원본 Contact callback을 coalescing 전 별도 bounded JSONL에 보존하고, 같은 trial의 actual ECM per-step identity/time/metadata challenge와 비교한다. `(observation_start_ns, observation_end_ns]` grid, RGB t0 <= start, 10s 이상, overflow/invalid IDs/duplicate/missing/late control 금지. ROS positive pair match는 실제 exact stamp and IDs만 인정하고 silent/partial delivery는 GT 승격하지 않는다. 기존 A14 GT candidate는 UNKNOWN/HOLD, human_approved=false, 원본/sidecar SHA 보존. R02-3 PASS는 integrated evidence capture PASS이지 전체 production contact health PASS가 아니다. 

## 검증 계획
L0 fixture로 observer 이외 SDF 불변 및 same-stamp pair mismatch를 점검. 신규 계약의 상반된 silent channel ST-02/UN-01 각 1회만 검증한다. 기존 A14/P0·R02-1 실행을 수동 반복하지 않는다. 실제 L2와 원본 SHA 검증은 새 전용 CI 결과 전 NOT_RUN. R02-2 독립 negative control PASS 또한 출고 선행 조건이다. Owner release 전 둘 다 확인해야 한다.

## 제한
process-local adapter는 기존 함수 시그니처에 의존한다. upstream version 변경 시 다시 검증한다. 별도 geometry engine registration 및 ROS full transport는 증명하지 않으며 P0 GT 품질 HOLD 유지. 
