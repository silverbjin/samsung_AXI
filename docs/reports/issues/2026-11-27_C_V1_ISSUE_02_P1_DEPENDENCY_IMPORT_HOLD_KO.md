# C-V1-ISSUE-02 — P1 WSL2 torch/torchvision import 의존성 FAIL-CLOSED

## 사용자 제출 WSL2 원본 분석 (2026-11-27)

- TAR: `20261127T001421Z-p1-17c6db753b52.tar.gz`; 외부 SHA256 `52ed93611104983e7f776e798e992ca0a08b9a2dd71072648e44cd6f1f730998`, SHA sidecar 일치.
- 아카이브 구조 6개 일반 파일(로그 3, P1 JSON 1, 실행 상태 1, checkout 1); 안전한 상대경로, stderr 0바이트는 정상 diagnostic.
- Checkout `17c6db753b52333b971bfc0b380a3da29b62f8a4`/clean; Python 3.12.3, Git 2.43.0; `exit_code=2`.
- P1 `p1_report.json`: `verdict=HOLD`, `reason=C_V1_TORCH_OR_TORCHVISION_MISSING`, `error_type=ModuleNotFoundError`, `training_permitted=false`.
- 기존 C 코드에서 torch/torchvision을 한 try문으로 감싸 **정확한 누락 모듈명이 실시간 진단에 드러나지 않음**. 이번 파일만으로 두 패키지 중 어느 것이 빠졌는지 단정 불가. 사전학습 가중치의 cached SHA/라이선스 검사는 import 단계에서 중단됨.
- P0 검증 원본 보고서 `56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0`/42개 read-only 원본 PASS는 재실행 없이 보존.

## RED → GREEN 최소 코드 수정

- `ai/train/p1_pretrained_inspection.py`: Python 표준 라이브러리 기반 `package_inventory()`(import spec/배포 metadata version만 읽음), `classify_import_failure()`(정확히 torch/torchvision/PIL 상위 모듈 미존재를 구분) 추가. 내부 종속 DLL/추가 의존성 실패를 torch 자체가 없다는 잘못된 진단으로 승격하지 않음.
- `tests/test_c_p1_pretrained_inspection.py`: 분류 4유형, 기타 ImportError, metadata read-only 음성 검증을 추가. 실제 torch import/가중치 설치/다운로드/학습/실 Test 없음.
- 정상 패키지 존재 시에도 `ResNet18_Weights.IMAGENET1K_V1` **기존 캐시 파일 전체 SHA256만** 확인. Cache가 없으면 `C_V1_PRETRAINED_CACHE_MISSING` + exit2. 별도 사용권/환경/계획 승인이 없으면 학습 GO 발급 불가.

## 사용자 WSL2 최소 재현

다음 명령은 설치하지 않으며 원래 실패한 **동일 Python**에서 실행합니다.

```bash
python3 - <<'PY'
import importlib.util
from importlib.metadata import version, PackageNotFoundError
for module, dist in (('torch','torch'),('torchvision','torchvision'),('PIL','Pillow')):
    try: ver=version(dist)
    except PackageNotFoundError: ver='NOT_INSTALLED'
    print(module, 'spec=', bool(importlib.util.find_spec(module)), 'dist=', ver)
PY
```

ROS/system Python 전역에 임의 pip 설치하지 않습니다. P2 계획은 **CPU**이므로 GPU/CUDA 구성 문제로 착각하지 않습니다. 환경 복구는 별도 격리 venv와 호환되는 pinned torch/torchvision wheels를 승인한 뒤에만 진행합니다. 실행이 같은 경로를 통해 이루어지는지 확인해야 합니다.

## 인수 상태

- P0 **PASS**, Data Freeze/승인18/제외2/Family split11/3/4 유지.
- P1 **HOLD_DEPENDENCY_IMPORT**; ImageNet V1 pretrained whole SHA/사용권·C 연구 승인 미완료.
- P2 train / P3 Test / P4 model **NOT_RUN**.
- A19 **NOT_AUTHORIZED**, Production Contact **HOLD**, AI OFF **PROTECTED**, E AI ON **HOLD**.
