# C09 — P0 독립 Owner 증거 수령 및 P1 사전학습 가중치 검사기 개발 보고서 (2026-11-26)

- 기존 C01~C08 및 Dataset v1 P0~P6 코드 보존; 새 소스는 `ai/train/p1_pretrained_inspection.py`만 추가.
- WSL2 제출 TAR SHA `0aa3f44225df91a0bba606c842a9760131b5150070057fe48cefdb42ad758dda`, `p0_report.json` SHA `56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0`; `files_independently_hashed=42`, PIN `ea54959b66b1744fa7bc9f9500ae95cf11cedf57`, clean, `exit0`, train 미실행. 상세 [검토 보고서](../acceptance/SMARTDISH_C_DATASET_V1_OWNER_P0_EVIDENCE_REVIEW_20261126_KO.md).
- 검수 도구가 실행되었다는 **재현 가능한 근거**를 C가 수령했지만, private 42개 바이트 자체는 이번 C 런타임에 없음. SHA 고정·파일개수·원본 계약 충족을 P0 통과로 기록하고 P1 명시 승인까지 학습을 막습니다.

## 설계: 왜 P1 weight hash가 필요한가?

기존 `ResNet18_Weights.IMAGENET1K_V1`을 재활용하되, 미리 준비된 로컬 `torch.hub/checkpoints/` 파일만 **읽기 전용**으로 SHA256 계산합니다. 누락 시 다운로드하거나 무작위 초기 가중치로 넘어가지 않습니다. torchvision·torch·Pillow·Python 버전도 보고합니다. Owner의 P0 report는 **정확한 full SHA**로 일치 확인합니다. 실험 lock의 데이터/Family/분할/seed/비증강/1회 Test/no-A19/Contact HOLD 보장을 변경하지 않습니다.

- P1 preflight는 연구 승인서 작성·서명·학습 실행을 수행하지 않습니다.
- 성공 상태 `P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED`도 사람의 ImageNet pretrained 사용권·데이터 독립성·연구 범위 리뷰 전에는 `training_permitted=false`입니다.
- 실패는 `C_V1_*_MISSING` / `C_V1_P0_REPORT_SHA_MISMATCH` 등 명시적 이유로 `exit2` 처리합니다.
- 공개 GitHub CI에서는 **fixture-only 음성 테스트**로 승인 없이는 진행할 수 없는 조건을 검사합니다. WSL2 실제 pretrained 캐시 접근/학습/실 Test는 CI에서 실행하지 않습니다.

## WSL2 단일 사전검사 (학습 금지)

새 GitHub **immutable C pin**에서 detached/clean checkout 후:

```bash
python3 -m ai.train.p1_pretrained_inspection \
  --p0-report "$HOME/smartdish_c_dataset_v1_p0_evidence/20261126T084104Z_ea54959b66b1/p0_report.json" \
  --experiment-lock ai/docs/C_V1_EXPERIMENT_LOCK.json \
  --report "$HOME/smartdish_c_dataset_v1_p1_evidence/pretrained_review.json"
```

CLI 결과 `HOLD`는 모델 결함으로 단정할 수 없습니다. Cache/torch 설치가 부족하면 해당 결함만 해결하고 P1 인수서를 재검토합니다. 실제 학습을 단축 목적으로 Test를 열거나 A19를 실행하지 않습니다.

## 상태

- P0: **CONTRACT PASS / HUMAN REVIEW REQUIRED**.
- P1: **환경·가중치 SHA 확인 대기 / C Human GO 미발급**.
- P2 frozen train11/val3: **NOT_RUN**.
- P3 independent Test4: **NOT_OPENED**.
- P4 model artifact: **NO_CHECKPOINT**.
- P5: 이 SHA에 대한 공개 CI 확인 후 실행 근거 갱신.
- P6: D/E 코드·계약만 인계, AI ON **HOLD**. AI OFF 기본 유지.

교육 토론: P0의 SHA 42/42 검사 성공과 `training_permitted=false`가 동시에 참인 이유는 무엇인가요? P1 weight cache를 읽지 못했다고 합성 이미지로 학습하면 왜 다른 모델이 되나요? Test 평가 전에 threshold을 봉인해야 하는 이유는 무엇인가요?

## P1 Owner immutable 원샷 추가

`scripts/smartdish_c_v1_p1_pretrained_once.sh`는 WSL2에서 새 C SHA를 detached/clean checkout한 뒤, **기존 P0 보고서만 재사용**하여 pre-trained 캐시+환경을 확인합니다. B audit/출고/물리 Gazebo/P0 42해시 재실행/학습·Test는 전부 미수행. P1 결과 `p1_report.json`, checkout, stdout/stderr, 실행상태를 자동 TAR+SHA sidecar로 생성합니다. 비공개 archive는 GitHub에 게시하지 않습니다.

```bash
PIN=<새로운_40자리_C_immutable_SHA>
curl -fsSLo "$HOME/smartdish_c_v1_p1_pretrained_once.sh" \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_c_v1_p1_pretrained_once.sh"
SMARTDISH_C_PIN="$PIN" bash "$HOME/smartdish_c_v1_p1_pretrained_once.sh"
```

가중치가 캐시에 없다면 `exit2 HOLD`를 기록하며 자동 다운로드를 시도하지 않습니다. 성공해도 사용권과 C 독립 학습 승인 조건은 별개입니다.
