# SmartDish C13 — P3 이전 체크포인트 원본 봉인(Read-only) 실행 가이드

## 목적

P2 Owner 보고서가 기록한 체크포인트 SHA256 `6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c`가 실제 WSL2 private `c_v1_frozen_head.pt` 바이트와 일치하는지 **사용자 머신에서 직접 확인**합니다.

P2 제출 TAR는 체크포인트의 바이트가 아닌 집계·로그만 포함하며, 이전 인수 `C_P2_EXECUTION_ACCEPTED_RESEARCH_ONLY`가 곧 실제 checkpoint를 이 검토자가 원격으로 재해시한 것이라고 주장하지 않습니다.

- `ai/train/p3_pretest_seal.py`는 P2 `summary.json` 전체 SHA `945f8f4aeb3b8a8e9cb1873f4353620dbd660765b3eb9688ab234a61f97a3864`, P1 plan 전체 SHA `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019`, 체크포인트 전체 SHA를 비교합니다.
- `torch.load(..., weights_only=True, map_location="cpu")`로 **훈련 없이** checkpoint architecture/labels/224 RGB/phase/frozen P1 plan/split/source+head shape 메타데이터만 읽습니다.
- 이미지·원본 물리 evidence·Test 파일은 **열지 않음**. `predict_pil`/모델 inference 없음, Test 평가 `NOT_RUN`, Test 승인·Lock 생성 없음.
- `scripts/smartdish_c_v1_p3_pretest_once.sh`: immutable SHA clean checkout, C 전용 venv 자동 활성화, B·P0·P1·P2 반복 없음. 결과 `pretest_report.json`/checkout/log/status를 TAR+SHA256 자동 포장하고 checkpoint/가중치는 private 보존.
- 공개 CI는 private weights 없는 synthetic negative tests와 `bash -n`만 수행, 실제 WSL2 pretest는 Owner 별도 인수입니다.

## 현행 수용 상태

| Gate | 판정 |
|---|---|
| P0 private Dataset v1 42/42 | PASS (기존 증거 재사용) |
| P1 pretrained cache / CPU venv | 기술 PASS |
| P2 최초 frozen 학습 실행 | `C_P2_EXECUTION_ACCEPTED_RESEARCH_ONLY` |
| P2 모델 성능 | **HOLD** (Val 1/3=33.3%, STABLE 다수 기준선 2/3=66.7%보다 낮음) |
| P3 이전 checkpoint SHA 원본 검수 | NOT_RUN / 사용자 WSL2 대기 |
| P3 Test4 개봉 | **NOT_AUTHORIZED, NOT_OPENED** |
| P4 연구모델 인수 / E 제품 AI ON | HOLD / HOLD |

pretest의 성공 판정 `P3_PRETEST_CHECKPOINT_SHA_PASS_PERFORMANCE_HOLD`는 기존 성능 HOLD를 자동으로 해제하거나 Test 승인 결정을 내리지 않습니다.

## 사용자 WSL2 실행

```bash
PIN=<최종_40자리_immutable_C_SHA>
curl -fsSLo "$HOME/smartdish_c_v1_p3_pretest_once.sh" \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_c_v1_p3_pretest_once.sh" \
  && SMARTDISH_C_PIN="$PIN" bash "$HOME/smartdish_c_v1_p3_pretest_once.sh"
```

Private checkpoint `$HOME/smartdish_c_v1_p2_private/c_v1_frozen_head.pt` 및 기존 summary `$HOME/smartdish_c_v1_p2_evidence/20261127T004925Z-p2-9db90e52da30/summary.json`가 원본 경로에 있어야 합니다. 다른 위치라면 `SMARTDISH_C_P2_SUMMARY`만 덮어쓸 수 있습니다.

실행 후 `$HOME/smartdish_c_v1_p3_pretest_evidence`의 TAR + 대응 SHA256만 공유하십시오. `.pt` 모델/원본 PNG·실물 물리 증거/사람 승인 JSON은 공유하지 않습니다.

## 후속 의사결정

**권고:** P3 Test 단일 평가를 바로 개봉하지 않고 먼저 기술적인 checkpoint 봉인을 완료하십시오. 모델 Validation이 다수 클래스 기준선보다 낮다는 제한을 검토한 뒤, Test를 *교육용 단일 연구 평가*로 소비할 것인지 별도의 명시적 결정이 필요합니다. 이 판단과 상관없이 Test 보고서를 재학습/임계값 조정/모델 선택으로 되먹임하는 것은 금지합니다.

Data Freeze A18_LAST, A19 NOT_AUTHORIZED, Production Contact HOLD, AI OFF PROTECTED, 제품 AI ON HOLD.
