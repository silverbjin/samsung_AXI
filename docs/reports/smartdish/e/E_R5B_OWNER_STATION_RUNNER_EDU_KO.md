# E-R5b — 최종 Owner 통합 실행기 후보
## 목적과 권리
CI는 private C v1을 읽거나 사람 승인을 흉내 내어 L3라고 주장하지 않는다. 같은 witness의 실물 Nav2 + 독립 Gazebo station 검증 구조를 Owner 모드로 재사용하되 CI 코드와 분리한다. 실제 로봇 장착 tray와 model 성능은 미검증.
## 설계
- `--run-station`은 WSL/실제 TTY/GUI를 요구, 기존 C venv를 그대로 재사용하고 immutable source 및 설치 bytes 확인. A upstream은 고정 SHA, 기존 작업 복사본의 변경을 강제 reset하지 않는다.
- Owner에는 request/staff publisher가 없다. A 실제 /dev/tty 입력, D GUI의 T03 AI ON 10/5 요청, 직원 버튼만 허용한다. 잘못된 UI 옵션은 전송 전에 차단. D의 별도 acceptance 옵션도 동일 계약을 차단하며 기본 AI OFF와 기존 R2 경로는 유지한다.
- 실제 C 모델 로드와 입력 hash/정상 predictor 반환, D staff causal log, UI applied COMPLETED, 실제 Nav2 UUID/odom/AMCL 및 CM graph를 검수한다. C의 raw label/confidence는 모델 성능 보증이 아니다.
- 증거 TAR 및 SHA256 생성, 모델 파일 자체는 아카이브하지 않는다. CI와 Owner scope marker 분리.
## 검증 상태
후보 구현 단계. CI가 완료되기 전 최종 WSL2 원샷을 배포하지 않는다. 실제 private model load/GUI human click은 사용자 최종 인수에서만 수행한다.

DBG-03 E-only docking remap/실제 velocity graph 및 DBG-04 DDS cross-topic correlation 수정 계승. 동일 R4 CI에서 C predictor provenance 및 D 직원 승인 로그의 인과 순서를 추가 검증한다. 모델/실제 GUI/WSL 승인 PASS는 별도 인수 증거로만 인정한다.
