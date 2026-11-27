# SmartDish C11 — P1 WSL2 격리 CPU·ImageNet V1 가중치 기술 인수 (2026-11-27)

> **검수 결론:** `C_P1_WEIGHT_TECHNICAL_PASS_C_RESEARCH_APPROVAL_PENDING`. 단일 RGB·고정 외란 연구 파일럿 범위로만 판단합니다. **학습 승인 아님**, P2/P3/P4 `NOT_RUN`, AI OFF 유지.

## 1. 실제 사용자 제출 증거

- 아카이브: `20261127T003050Z-p1-23e5dcd49361.tar.gz`; 실제 SHA256 `c346ddae3764198b1aadb878747a2ca4c097535aa54b9c15b504dee3bc1db38a`; 첨부 `.sha256` 첫 필드와 정확 일치.
- 멤버: `checkout.log`, `environment.log`, `execution_status.json`, `p1_report.json`, `preflight_stdout.log`, `preflight_stderr.log` 6개 일반 파일(+ root directory). 증거는 테스트·학습 이미지, checkpoint/weights 바이트를 포함하지 않음.
- `p1_report.json` SHA256: `8143ecc11a5b1a81cbbc6ca65d714eccd66b617e05467768478d7b16b59b1582`.
- Owner 원샷 `source_sha=23e5dcd49361405d2ee53fa379ed7a28ff3ce3c8`, clean `1`, `exit_code=0`; 종료 2026-11-27T00:30:54.792548+00:00. `stderr` 빈 파일, 표준출력 상태와 JSON 일치.
- `training_executed=false`, `test_opened=false`, `B_AUDIT_REEXECUTED=false`, `P0_REEXECUTED=false`. Owner 자체 진단의 메타데이터로 인정하며, 이번 리뷰어가 WSL2 CPU 환경을 직접 원격 실행한 것은 아님.

## 2. 독립 판정한 P1 계약 값

| 항목 | Owner 결과 | 판정 |
|---|---|---|
| 실행 Python | 3.12.3 / Linux | PASS |
| 격리 pip | `~/.venvs/smartdish-c-v1-py312-cpu/lib/python3.12/site-packages/pip` | PASS |
| torch | `2.5.1+cpu` import 가능 | PASS |
| torchvision | `0.20.1+cpu` import 가능 | PASS |
| Pillow | `10.2.0` import 가능 | PASS |
| pretrained enum | `ResNet18_Weights.IMAGENET1K_V1` | PASS |
| 공식 참조 URL | `https://download.pytorch.org/models/resnet18-f37072fd.pth` | PASS |
| cached weight bytes | `46,830,571` | PASS |
| 전체 SHA256 | `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` | Owner 보고서에 기록됨 |
| P0 report SHA256 | `56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0` | 이전 P0 pin 일치 |
| P1 experiment lock SHA256 | `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019` | 사전 고정 계획 일치 |
| Dataset v1 | `c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606` | 일치 |
| Split SHA256 | `8a530b6a34788300bb507ea10aafd10a7ab5616a0c0ffc0f87b7ccf79d0db6d5` | 일치 |
| P1 technical verdict | `P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED` | 기술 검사 성공, 승인 대기 |
| license review/ C research approval | `false` / `false` | **HOLD** |
| training permitted | `false` | **P2 금지** |

`torchvision` 코드의 BSD-3-Clause 라이선스와 ImageNet 기반 가중치의 별도 재배포·사용 조건이 자동으로 동일하지는 않습니다. C 인수는 공식 torchvision ResNet18 원본 링크·중량 SHA를 기록한 상태일 뿐, **프로젝트 연구용 모델 아티팩트 재배포 권리나 사용권을 확정하지 않음**. 근거 문서: https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.resnet18 , https://github.com/pytorch/vision/blob/main/LICENSE . 사람 검토 결과와 사용 범위는 private 승인 원장에 별도 기록해야 합니다.

## 3. P1 실험 적합성 및 위험: 기술 승인 vs 학습 승인

기존 `ai/docs/C_V1_EXPERIMENT_LOCK.json`은 변경하지 않음. 실제 데이터는 approved18/5 Family, train11(F3/F4:8S3U), val3(F1:2S1U), test4(F2/F5:3S1U). P2 1회 frozen ResNet18 (seed42 / CPU / epochs3 / batch4 / lr1e-4 / no augmentation / min validation cross-entropy), inference threshold0.80을 **Test 개봉 전** 봉인. Fine-tune 자동 착수·Test 기반 모델 변경·가상 샘플 그룹 확대 금지.

- 제한 조건: 정적 원통형 식기 적재, t0=2.0 s RGB 단일 시점, 월드 +Y 고정 0.12 N·m 명령 토크 0.5 s, 12.3 s까지 관찰. **실제 이동/측정 wrench/로봇 안전 인증이 아님**.
- 의사 결정: 기술적으로 P2 실행을 준비할 수 있는 환경은 마련됨. 그러나 `pretrained_license_reviewed=false`, `C_research_approval_issued=false`이므로 **학습 GO 금지**.
- C 독립 학습 적합성의 정량적 제한: train11/val3/test4 및 U test1은 작은 표본. Near-pair/방향성 편향 위험 해소되지 않음. 제품 실측 성능·일반화 인증에 사용 금지.
- P1 조건: pretrained 가중치 사용권/프로젝트 연구 목적 검토, Family near-pair 독립성 위험 수락, C reviewer 기록, 계획 SHA·가중치 SHA·P0 report SHA와 정확 결합한 **별도 비공개 `C_P0_RESEARCH_TRAIN_GO`**가 있어야 실제 P2 착수. `ai/train/research_approval.py`의 기존 fail-closed 검증을 무력화하지 않음.
- Test 이미지/GT는 모델 선택과 무관하게 잠금 유지. P2 GO 뒤 train/val만 사용; P3 단일 Checkpoint/threshold 잠금 후 Test 1회.

## 4. 개발·수용 결과 및 남은 단계

- **P0** Owner private 42/42 재검사 PASS, 재실행하지 않음.
- **P1** 격리 venv+pretrained cache SHA·plan pin **기술 PASS**, 연구 활용/승인 **HOLD**. 재설치 불필요.
- **P2/P3/P4** `NOT_RUN`/`TEST_NOT_OPENED`/`NO_CHECKPOINT`.
- **P5** 기존 GitHub fixture-only CI [#45916836293](https://github.com/silverbjin/samsung_AXI/actions/runs/45916836293) 75 PASS(이전 코드 SHA), 이번 변경은 **문서만** 반영. **CI PASS ≠ Owner WSL2 인수**.
- **P6** D/E에는 P1 기술 증거·입출력 계약만 전달 가능. 실제 연구 모델·E 제품 AI ON 인수 HOLD.
- **절대 보호:** A18 마지막 Data Freeze, A19 `NOT_AUTHORIZED`; 추가 물리 생산/재라벨/재분할 없음; Production Contact `HOLD`; AI OFF `PROTECTED`.

## 5. C 교육 실습 요점

1. 코드 통과, 원본 파일 무결성, 실행환경 설치, 가중치 SHA, 사용권 검토, 제한 모델 학습 GO는 **서로 다른 검증 게이트**입니다.
2. `exit0`의 의미는 `P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED`: P2 학습이 이미 실행됐다는 뜻이 아닙니다.
3. 가중치 bytes 자체는 사용자 WSL2 캐시에만 있으므로 TAR에는 모델 가중치가 없고, 다른 컴퓨터에서 동일한 weight SHA를 직접 재해시했다는 뜻이 아닙니다.
4. 실제 학습 후 Test4의 100% 결과조차 제품 안전 일반화나 주행 전 트레이 안정성 보증으로 표현할 수 없습니다.
