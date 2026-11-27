# SmartDish C10 — WSL2 전용 Python 가상환경 설치·자동 활성화 (2026-11-27)

## 요구와 현재 증거

- 사용자가 기존 WSL2 환경에서 `torch`/ `torchvision` `NOT_INSTALLED`, Pillow `10.2.0` 확인. 기존 P1 Owner TAR의 `ModuleNotFoundError` 원인과 일치하며 **데이터셋 P0의 결함이 아님**.
- ROS2 Jazzy·Gazebo Harmonic·다른 개발 브랜치의 Python을 변경하지 않고 **C 전용 독립 환경**을 운영.
- 공식 PyTorch 과거 버전 CPU 조합 `torch==2.5.1`, `torchvision==0.20.1`; `numpy==1.26.4`, `Pillow==10.2.0`, Python 3.12로 고정. 공식 문서: https://pytorch.org/get-started/previous-versions/

## 산출물

- `scripts/smartdish_c_v1_install_cpu_venv.sh`: 설치 명령만 처리하는 **별도 스크립트**. `/usr/bin/python3`로 `$HOME/.venvs/smartdish-c-v1-py312-cpu`에 `venv` 생성, 공식 CPU 인덱스로 설치, CPU-only 및 버전 검증, `pip check`, 설치 영수증·TAR+SHA 사이드카. `flock`으로 중복 설치 방지, 타 프로젝트 venv를 덮어쓰지 않음. **`sudo apt`·전역 `pip`·ROS/GPU 설정 변경 없음**.
- `scripts/smartdish_c_v1_p1_pretrained_once.sh`: P1 시작 시 위 venv를 **원샷 내부에서 자동 source/activate**하고 전용 `TORCH_HOME=$HOME/.cache/smartdish-c-v1/torch` 사용. 미설치면 `C_V1_P1_VENV_NOT_INSTALLED`로 fail-fast, 설치는 하지 않음. 기존 P0 보고서 재사용; P1 파일 검사 전용.
- `tests/test_c_cpu_venv_contract.py`: 패키지 pin/CPU 인덱스/가상환경 호출/패키지 격리/Weight 명시 opt-in/미설치·핀 미입력 fail-fast 테스트, 전용 CI에서 네트워크·실 package 설치 없이 실행.

## 실행 정책

**1. 설치 (명시적으로 1회)**

```bash
PIN=<최종_40자리_immutable_C_SHA>
curl -fsSLo "$HOME/smartdish_c_v1_install_cpu_venv.sh" \
 "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_c_v1_install_cpu_venv.sh"
SMARTDISH_C_PIN="$PIN" bash "$HOME/smartdish_c_v1_install_cpu_venv.sh"
```

사전학습 가중치까지 공식 모델 캐시에 확보할 필요가 있고 공식 가중치의 사용권 검토 전 **다운로드만 명시 허용**하는 경우에 한해 `--with-weights` 옵션을 사용. 자동 silent download 금지. 공식 Weight url은 torchvision enum에서 유도; `resnet18-f37072fd.pth` SHA prefix를 검증하고 **전체 SHA**는 private 영수증에 기록. 라이선스·연구 승인 여부는 `false`로 남김.

**2. P1 원샷(자동 활성화 / 수동 source 불필요)**

```bash
curl -fsSLo "$HOME/smartdish_c_v1_p1_pretrained_once.sh" \
 "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_c_v1_p1_pretrained_once.sh"
SMARTDISH_C_PIN="$PIN" bash "$HOME/smartdish_c_v1_p1_pretrained_once.sh"
```

P1 성공은 `P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED`로, **학습 허가가 아님**. 무게 캐시가 없을 때는 `C_V1_PRETRAINED_CACHE_MISSING`으로 HOLD를 기록. 설치 스크립트의 *explicit* `--with-weights`를 별도 실행할 수 있으며, 원샷은 절대로 설치·다운로드하지 않음.

## 기존 증거·정책 보존

- P0 42/42 Owner 검사 PASS, B Dataset v1 freeze 승인18/제외2/Family 11/3/4 유지. **P0/B QA06/A19 재실행 없음**.
- P1 사용권/가중치 SHA/연구 승인 미확정, P2 train·P3 Test·P4 model `NOT_RUN`.
- Production Contact `HOLD`, AI OFF `PROTECTED`, E AI ON `HOLD`. 반복실험 금지.

## 최종 코드 검토 반영

- Python P1의 `inspect()`는 venv 내부인지와 `torch 2.5.1` / `torchvision 0.20.1` / Pillow `10.2.0` / **CPU-only**인지 재확인합니다. 다른 설치자가 C 전용 디렉터리를 변경한 경우 `C_V1_P1_CPU_DEPENDENCY_VERSION_MISMATCH`로 HOLD합니다.
- P1 원샷은 설치 스크립트와 **동일한 설치 잠금 파일의 shared lock**을 nonblocking 방식으로 취득합니다. 설치 중이라면 `C_V1_P1_INSTALL_IN_PROGRESS`로 fail-fast, 설치 중간 상태를 인수 증거로 사용하지 않습니다.
- PyTorch 전체 wheel 실제 다운로드·설치 및 WSL2 P1 Owner 검증은 사용자 머신에서만 수행할 수 있으므로 GitHub의 fixture-only CI 결과와 구분합니다.

## C11 최신 증거 (기술 P1 PASS)

2026-11-27 사용자 WSL2 `23e5dcd49361405d2ee53fa379ed7a28ff3ce3c8` 원샷의 `exit0`, 전용 venv 사용, `ResNet18_Weights.IMAGENET1K_V1` 전체 SHA `f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec` 직접 제출 증거와 SHA sidecar 일치. `C_P1_WEIGHT_TECHNICAL_PASS_C_RESEARCH_APPROVAL_PENDING`: **설치 성공은 학습 승인이 아님**. [상세 원장](../acceptance/SMARTDISH_C_V1_P1_OWNER_TECH_ACCEPTANCE_20261127_KO.md) 참고.
