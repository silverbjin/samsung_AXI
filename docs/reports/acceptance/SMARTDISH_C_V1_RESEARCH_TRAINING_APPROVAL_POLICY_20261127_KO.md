# SmartDish C — Dataset v1 연구 학습 승인 기록 및 사용권 제한 (2026-11-27)

## 승인 근거

- 프로젝트 Owner가 이번 대화에서 **"명시적으로 연구 학습을 승인한다."**고 지시함. 승인 자체는 실제 의사표시이며, 코드/CI/데이터 무결성 증거나 모델 성능 결과가 아님.
- 범위: B Dataset v1의 동결된 Train 11 / Validation 3, `ResNet18_Weights.IMAGENET1K_V1` frozen head 최초 1회. CPU Py3.12/torch2.5.1+cpu/torchvision0.20.1+cpu, epoch3/batch4/AdamW1e-4/seed42, augmentation NONE. Test 4개는 P3 별도 체크포인트·임계값 봉인 전 열지 않음.
- **연구 승인은 상업적 이용이나 가중치 재배포의 허가가 아닙니다.** 실행 원샷에서는 `NONCOMMERCIAL_INTERNAL_EDUCATIONAL_RESEARCH_NO_REDISTRIBUTION`을 명시적으로 제출해야 합니다. 이 조건을 충족하지 않는 환경이라면 P2를 실행하지 않고 제한사항 검토를 요청하십시오.
- 사용권 검토: TorchVision 소스 코드 라이선스 BSD-3-Clause ([원문](https://github.com/pytorch/vision/blob/main/LICENSE)) / TorchVision 공식 모델 설명의 **"가중치는 사용 모델과 훈련 데이터에 따라 별도 조건이 있을 수 있음"** 고지 ([링크](https://docs.pytorch.org/vision/stable/models.html)) / ImageNet의 비상업적 연구·교육 목적 이용 조건 ([링크](https://www.image-net.org/download)). 별도 계약서·유통권을 확인했다고 주장하지 않음. 이 검토는 **비상업적 내부 교육·연구에 한정된 보수적 범위 검토**이고 법률적 사용권 보증이나 상업적 제품 출시 승인이 아님.
- 승인 파일 `pretrained_license_reviewed=true`의 의미는 **위 제한적 사용조건을 검토하고 명시적으로 실행 범위를 한정**했다는 뜻. 가중치 또는 파생 checkpoint의 공개 재배포 허가와 다름.
- 연구 데이터 이용권: B release `GAZEBO_TRAY`, `PHYSICS_OBSERVED`, `AUTHORIZED` 18행만 사용. 원본 B Rights/Family 5, near-pair 132 검토 한계 보존.

## SHA 봉인과 비공개 승인 경계

| 영역 | 실제 PIN |
|---|---|
| C P0 원본 보고 | `56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0` |
| C P1 원본 보고 | `8143ecc11a5b1a81cbbc6ca65d714eccd66b617e05467768478d7b16b59b1582` |
| P1 실험 사전 계획 | `9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019` |
| ResNet18 V1 pretrained SHA | `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` |
| Dataset v1 version | `c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606` |
| B split SHA | `8a530b6a34788300bb507ea10aafd10a7ab5616a0c0ffc0f87b7ccf79d0db6d5` |

C private 승인 `C_P0_RESEARCH_TRAIN_GO`은 별도 `ai/train/prepare_v1_research_approval.py`가 위 SHA/스코프/P0·P1 원본 report를 검사한 뒤 Owner WSL2 private 경로에만 **한 번** 발급함. 공개 repository에 개인 승인 내용·이미지·모델 weights/checkpoint를 기록하지 않음. 임의 코드를 승인 없이 실행하는 것이 아닌, 이 사용자 명시 승인+scope attestation의 기술적 증거임.

`c_v1_p2_single_attempt_reserved.json`은 checkpoint 생성 전에 O_EXCL로 만들며 **재시도 금지**, 실패 시 최초 원인만 기록하고 사람 검토를 기다림. 원샷 출고 TAR는 로그·Train/Val 집계·checkpoint 해시만 포함하며 private checkpoint 자체는 포함하지 않음.

## 권한이 허용하지 않는 것

- 모델 성능·실물 로봇 안전 일반화 주장, 주행·다른 물리 조건 보증, Production Contact HOLD 해제
- A19 물리 추가 생산, 재라벨/새 Family 분할, near-pair 증식, Mock label 편입
- Test 평가(P3) 자동 실행, Test 보고서로 threshold 변경, fine-tuning 추가
- GitHub main 병합, 연구용 weights 또는 실제 PNG/원본 evidence 공개, E 제품 AI ON
