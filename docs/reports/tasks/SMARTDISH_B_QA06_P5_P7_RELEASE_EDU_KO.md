# P5–P7 출고·readiness
Audit receipt SHA를 운영자가 별도 보관; 파일 해시 및 source pin 확인. 승인 JSONL과 정책 JSON sidecar는 변조 탐지(서명/신원 인증 아님). 모든 20 결정 및 근거, 제외 이유, 권리, C/PM/B 연구 범위 승인, 근접쌍 검토와 Family 독립 split; 최소 클래스별 3 Layout. 기존 224 RGB ImageOps.fit, crop 확인, B manifest validator 재사용. 실제 학습 입력 RGB only, evidence/metadata는 audit용. 원자적 private dataset release, 승인 전 미생성. C REVIEW_REQUIRED, E HOLD. C/D/E 실제 코드 미변경.

보강: 별도 REVIEW_COMPLETED 상태, frozen readiness, 명시적 diversity risk acceptance, no-go 판정. 실제 approval 없이 positive path를 테스트하기 위해 모의 receipt+완전히 합성 RGB/evidence/decision으로 6개 fixture만 private pytest 임시 디렉터리에서 출고/검증/변조 거부를 실행. 실물 승인·학습 증거 아님. 근접쌍 검토 양식 공란과 100ms 누적 경로 표시(1ms 실측 총량과 구분)를 추가.
