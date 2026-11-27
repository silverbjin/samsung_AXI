# C12 — 명시 연구 승인부터 Frozen ResNet18 1회 Owner P2 인수 실행까지 (2026-11-27)

## 역할/진행 결과

- 코드 브랜치 `feat/smartdish-c-dataset-v1-pilot`, C 다른 팀 원본/브랜치/AI OFF 보호.
- 프로젝트 Owner가 연구 학습을 **명시적으로 승인**, 상업적 모델 출고·파생 weights 배포를 승인한 것은 아님.
- P0 42/42 출고 SHA independent PASS, P1 전용 venv/torch+torchvision+Pillow/ResNet18 V1 46,830,571바이트, SHA `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` 및 Experiment plan SHA `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019` PASS를 그대로 재사용. **P0/B Audit·P1 재실행 없음**.

## RED → GREEN 주요 변경

1. `ai/train/prepare_v1_research_approval.py`: 기존 P0/P1 전체 SHA 보고서·frozen plan pin·권리 제한·사용권 검토 출처·Scope attestation 확인 후 Owner PRIVATE `C_P0_RESEARCH_TRAIN_GO`를 한 번만 발급. `pretrained_license_reviewed=true`는 **보수적 비상업 연구 범위 검토 완료**를 의미하며 상업·재배포 권리를 의미하지 않음.
2. `ai/train/train_classifier.py`: 기존 Train/Val 로직 재사용, 승인된 epoch3/CPU/batch4/lr1e-4/seed42/frozen/checkpoint 없음 조건 강제. **Frozen backbone BatchNorm의 running statistics가 train mode에서 수정되던 위험**을 `model.eval()`+fc training mode로 제한해 해결. Validation 최소 CE에서 단일 best epoch 및 체크포인트 저장; 기록 `best_epoch_by_min_val_loss` 추가. Test 데이터는 `read_verified_split(...,training_only=True)`에서 필터 후 14장만 이미지/물리 근거 검사.
3. `scripts/smartdish_c_v1_p2_frozen_owner_once.sh`: pinned detached SHA/clean, `~/.venvs/smartdish-c-v1-py312-cpu` 자동 활성화, `TORCH_HOME` 전용 캐시, CPU2 thread 제한, 환경/P0/P1 SHA 검증, PRIVATE approval, O_EXCL one-shot reservation, Train/Val 1회, 결과 SHA 확인. 실패/성공에 대해 TAR/sidecar 자동 생성(실제 PNG, physical evidence, checkpoint, approval 원문 미포함).
4. `tests/test_c_p2_research_approval.py`: synthetic fixture-only 승인·실패 경로·권한 경계·실행 파라미터 Drift·중복실행/장치권리 제약 검사. CI는 실제 weight 다운로드, private dataset, training, Test를 실행하지 않음.

## Owner 사용법 (실행 최초 1회)

```bash
PIN=<신규_전체_40자리_Immutable_SHA>
curl -fsSLo "$HOME/smartdish_c_v1_p2_frozen_owner_once.sh" \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_c_v1_p2_frozen_owner_once.sh"
SMARTDISH_C_PIN="$PIN" \
SMARTDISH_C_USAGE_DECLARATION=NONCOMMERCIAL_INTERNAL_EDUCATIONAL_RESEARCH_NO_REDISTRIBUTION \
bash "$HOME/smartdish_c_v1_p2_frozen_owner_once.sh"
```

해당 선언에 동의하지 않는 상업·재배포 목적이라면 **실행하지 마십시오**. 한 번 출고된 `c_v1_p2_single_attempt_reserved.json`은 두 번째 실행을 차단합니다. 실패한 경우 별도 연구 변경 승인과 증거 진단 필요. 성공해도 P3 독립 Test 개봉/연구 모델 출고를 자동 수행하지 않음.

## 실제 Owner 인수 vs CI

- 공개 fixture-only Github CI의 test PASS는 CPU 실제 모델 훈련이 아니라 **코드 승인/Fail-Closed 계약 검증**.
- 현 시점 Owner의 새 P2 checkpoint/report **NOT_RUN**. 기존 P0·P1 실제 증거만 완료됨. CI PASS를 실제 성능 결과나 연구 모델 출시로 표기 금지.
- 원샷 P2 성공 시 제출할 것은 `$HOME/smartdish_c_v1_p2_evidence/*.tar.gz` 및 대응 `.sha256`. `$HOME/smartdish_c_v1_p2_private/c_v1_frozen_head.pt`·실 데이터는 업로드하거나 GitHub에 게시하지 않음.
- 후속 C 검토는 P2 train/val loss/accuracy와 checkpoint SHA/수렴 여부만. Checkpoint·threshold 0.8 별도 봉인 후 P3 Test4 **한 번** 평가 승인 여부 결정.

## 교육 중점

*동일한 108개 코드 테스트 PASS가 있어도 실제 Tiny Dataset의 성능을 예측하거나 Owner가 재현할 것을 보장하지는 않습니다.* P0/P1 파일·실행환경·권리 범위·학습 실험·Test·제품 AI ON은 모두 별도 게이트로 남겨야 합니다.

상세 사용권 검토: [승인 정책 원장](../acceptance/SMARTDISH_C_V1_RESEARCH_TRAINING_APPROVAL_POLICY_20261127_KO.md).

## 2026-11-27 Owner P2 실제 학습 결과 (이 문서의 이전 NOT_RUN 설명보다 최신)

- C source `9db90e52da3025f548faba28444d0dc777586138`, `exit0`, pretrained SHA/plan SHA 일치, private Train11/Val3 1회 성공, Test 사용/개봉 false.
- Epoch1→3 Validation loss `0.8243010→0.7778842→0.7452375`, 정확도 `1/3→0/3→1/3`. best epoch=3은 predeclared CE에 따라 맞으나 다수 클래스 기준선 Val2/3 대비 미달, 성능 HOLD.
- C13 [실제 원본 증거 인수](../acceptance/SMARTDISH_C_V1_P2_OWNER_ACCEPTANCE_20261127_KO.md) 참고. 연구 모델·제품 AI ON 미승인, P3 Test4 별도 판단 전 접근 금지.
