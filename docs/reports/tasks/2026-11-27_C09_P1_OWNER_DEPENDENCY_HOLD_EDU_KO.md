# SmartDish C09 — 실제 Owner P1 패키지 의존성 차단·진단 개선 교육 보고서

## 목적

C의 Dataset v1 P0 42/42 독립 검증을 이미 끝낸 뒤, 연구용 ResNet18 가중치 인수 P1에서 무엇이 실제로 실패했는지 **증거 중심으로 재현**하고 환경 설정과 학습 결과를 혼동하지 않도록 구분합니다. A/B 기존 Data Freeze 및 C 기존 학습·평가·ROS 코드는 보존합니다.

## 실제 증거 → 최초 실패

2026-11-27 사용자 WSL2 증거 `20261127T001421Z-p1-17c6db753b52.tar.gz`는 외부 SHA256 `52ed93611104983e7f776e798e992ca0a08b9a2dd71072648e44cd6f1f730998`로 sidecar와 동일. 내역은 checkout/environment/실행상태/P1 JSON/stdout/stderr 총 6개 정규 파일이며 실패 로그는 변조 없이 보존합니다.

- 실행 C immutable SHA `17c6db753b52333b971bfc0b380a3da29b62f8a4`; checkout clean.
- `Python 3.12.3`, `git 2.43.0`, exit2.
- P1 검사 **`ModuleNotFoundError`**, reason `C_V1_TORCH_OR_TORCHVISION_MISSING`. 기존 예외 처리에서 정확한 `exc.name`을 버렸으므로 어느 package missing인지 확정할 수 없음.
- `pretrained_weights_sha256`는 계산되지 않았음. 가중치가 없다는 뜻이 아니라 **import 단계 이후 검사를 수행하지 못했다**는 뜻.
- `training_permitted=false`, 학습/Test/가중치 다운로드 없음. P0의 원본 42/42 PASS는 유지.

## RED → GREEN 코드 수정

`ai/train/p1_pretrained_inspection.py`에서 `classify_import_failure`를 도입해 `torch`, `torchvision`, `PIL`을 정확히 구분하고, 다른 중첩 의존성 ImportError는 별도 `C_V1_P1_DEPENDENCY_IMPORT_FAILED`로 남깁니다. `package_inventory`는 표준 라이브러리만으로 각 패키지의 import spec 유무와 설치 배포 버전만 조회하고 **실제 패키지 import조차 하지 않습니다**.

`tests/test_c_p1_pretrained_inspection.py`에 정확한 패키지 오류 매핑과 기타 ImportError, 의존성 inventory 계약 6건을 추가했습니다. 코드 SHA `9a1f7bb46c91ab7f27727d5ba02bd1db9278a113`, GitHub Actions [Run #45916029495](https://github.com/silverbjin/samsung_AXI/actions/runs/45916029495) **70 passed in 0.22s**. CI는 합성 fixture-only, WSL2 P1 재검 성공 아님.

## WSL2 실습 — 기존 Python 의존성 확인(설치·학습 없는 읽기 전용)

```bash
python3 - <<'PY'
import importlib.util
from importlib.metadata import version, PackageNotFoundError
for module, distribution in (('torch','torch'),('torchvision','torchvision'),('PIL','Pillow')):
    try: v=version(distribution)
    except PackageNotFoundError: v='NOT_INSTALLED'
    print(f'{module}: present={importlib.util.find_spec(module) is not None}, version={v}')
PY
```

공식 CPU wheel을 위한 격리 가상환경/버전·사용권은 별도 승인된 P1 환경 구성 단계에서 확정합니다. ROS 시스템 Python 전역에 무단 pip 설치하거나 CUDA/GPU 설정 변경, 자동 모델 다운로드를 하지 마십시오. 패키지가 준비된 뒤 새 immutable SHA로 **P1만** 1회 재검합니다. P0/QA06/물리 생산을 재실행하지 않습니다.

## 남은 승인 게이트 / 모델 경계

실제 `ResNet18_Weights.IMAGENET1K_V1` cache 파일 **전체 SHA256**, torchvision/torch/Pillow 버전, 가중치 사용권 검토, C 연구 목적·Family 근접유사성 위험을 검토하고 별도 명시적 `C_P0_RESEARCH_TRAIN_GO` 승인을 기록해야 P2 frozen-head 1회 학습을 진행합니다. Val 선택 전 Test 개봉/학습 조정/AI ON 제품 활성화/추가 A19/Contact HOLD 해제는 허용하지 않습니다.

**인수 상태:** P0 PASS, **P1 HOLD**, P2/P3/P4 NOT_RUN, D/E는 코드·UNKNOWN 계약만 인계 가능.
