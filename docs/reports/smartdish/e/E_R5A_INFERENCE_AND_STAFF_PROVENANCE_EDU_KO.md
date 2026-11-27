# E-R5a — 실제 모델 입력 및 직원 승인 provenance
## 목적
최종 WSL2 인수에서 READY 또는 model-version 문자열만으로 실제 추론 PASS를 주장하지 않는다. R1/R2 검증 이후에는 실제 predictor 호출과 반환, RGB 해시, capture/request correlation 및 직원 승인 발생 근거가 필요하다.
## 구현
- Owner 모드에서만 predictor의 성공 반환(label, finite confidence)을 감싸고 동일 RGB SHA, frame stamp, dimensions, monotonic receipt, raw decision/confidence 및 결과를 기록한다. 실제 모델 로더/threshold/권리 계약은 변경하지 않는다. 예외가 발생했거나 유효한 결과가 없으면 inference success marker는 없다.
- 주기 제한된 C frame accepted marker는 readiness용이며 inference success와 다르다.
- D는 유효 직원 응답을 수락한 경우에만 acceptance 로그를 남긴다. UI는 명시적 직원 버튼 동작을 기록한다. 기존 승인/ABORT/timeout 및 AI OFF 정책 그대로.
## 검증
새 CI의 R3b/R4 synthetic predictor와 실제 DDS 경로에서 provenance를 대조하고 L0/L1 기존 권리 계약 회귀를 검증한다. 실제 v1 weight와 UI 사람 클릭은 최종 WSL2에서만 확인한다. 본 문서는 구현 시점 보고이며 아직 새 SHA GREEN으로 간주하지 않는다.
