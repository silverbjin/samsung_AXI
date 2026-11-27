# E-DBG-003 — C PyTorch 환경 해결책의 E 통합 누락 (2026-11-27)

## 원본
- 사용자 WSL2: `e_aion_20261127T024809Z.log`; E PIN `4dbdeca6a0a8f8120cb42a44bd589d356726eb5d`.
- `E_OWNER_MODEL_SHA_PASS`, C/D 2 packages built, `SMARTDISH_D_UI_READY`, `C_DYNAMIC_THRESHOLD_APPLIED stable=0.650 unstable=0.900` PASS.
- `C_MODEL_UNAVAILABLE ModuleNotFoundError: No module named 'torch'`: 실제 Frozen model load **BLOCKED**. `C_STABILITY_READY`는 no-model UNKNOWN 준비일 뿐 모델 로딩 PASS가 아님.

## C에서 이미 구현한 진짜 해결책
- 독립 소스: `feat/smartdish-c-dataset-v1-pilot@ea0de9ce0c5b9ee1c500421b9de0feea5f68cffc`; 설치기 `scripts/smartdish_c_v1_install_cpu_venv.sh`, 실행기 `scripts/smartdish_c_v1_p2_frozen_owner_once.sh`, 검사 `tests/test_c_cpu_venv_contract.py`.
- 고정 가상환경 `~/.venvs/smartdish-c-v1-py312-cpu`. Python3.12, CPU torch 2.5.1+cpu, torchvision 0.20.1+cpu, numpy1.26.4, Pillow10.2.0. C 실행은 `source "$VENV/bin/activate"` 후 Python import·버전 검증, 실 모델 학습을 수행해 성공 근거를 확보함.
- C 브랜치의 위 설치기/테스트는 `main@ed59fa22bb53d1590ba10eef8f7982fcf44e7d29`과 E PR #64에 **없음**. GitHub compare는 해당 파일을 C 브랜치에서 추가된 것으로 표시.
- E의 실행기는 모델 SHA 확인 + ROS 패키지 빌드만 검사한 후 ROS Jazzy console script를 **기본 시스템 Python**으로 구동. C venv 자체도, 그 site-packages도 상속하지 않았음.
- E CI L1은 model-less UNKNOWN-only DDS를 사용하여 torch import 성공을 검사하지 않았음.

**최종 원인:** 독립 브랜치 분리 자체의 결함이 아니라, C→E runtime dependency/venv 인수계약과 실제 런타임 preflight의 누락. C에서 고친 코드가 E 실행환경에 자동으로 적용되는 구조는 원래 아님. E 담당의 통합 검수 미흡을 수정해야 함.

## E-DBG-003 해결 정책
- E는 C의 기존 CPU venv를 **읽기 전용으로 재사용**. 새 pip 설치·apt 변경·새 가상환경 생성·중복 모델 학습 없음.
- C receipt/.install_pending 상태, 버전/CPU 고정, C Python 실제 import, ROS 시스템 Python에서 C site-packages를 주입한 실제 import+ROS rclpy를 각각 검사한 뒤에만 preflight PASS.
- C 추론 노드 프로세스에만 PYTHONPATH를 전달해 D/UI/ROS 기본 작업환경 보존.
- 모델 지정 Owner 실행의 로딩 실패는 C 노드 종료 → E launch 전체 종료, 더 이상 UNKNOWN READY로 모델 인수 성공을 오인하지 않음.
- L0 fixture 사용 CI와 Owner WSL2 실환경 torch import 검증은 서로 다른 PASS 원장으로 기록. 실제 체크포인트 파일은 GitHub에 업로드하지 않음.
- 기존 C installer는 이미 구축된 경우 재실행하지 않음. 누락되었을 때만 C 담당의 원본 설치 이력과 기존 승인 범위를 확인해 복원.
- C20/Test4, A/AI OFF L3, Nav2/CM, 모델 성능 33.3% 판정 불변.

## 완료 증거
- 최초 RED: 사용자가 제공한 `torch` ModuleNotFoundError 로그.
- 신규 L0 검증: 누락된 C venv, 불완전 receipt, 버전 drift, Python import 실패, ROS process injection/launcher 계약의 회귀.
- 신규 Owner 기대 마커: `E_OWNER_C_RUNTIME_REUSED_VERIFIED` → `E_OWNER_AION_PREFLIGHT_PASS_OWNER_SCOPE_NO_GOAL` → `C_MODEL_LOADED version=resnet18-6afdcfe526e6`.
- 실제 WSL2 모델 로딩 확인 전에는 `E_OWNER_C_MODEL_LOAD_PASS` 금지.
