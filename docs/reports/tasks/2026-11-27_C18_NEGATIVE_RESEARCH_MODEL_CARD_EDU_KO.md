# C18 — Frozen ResNet18 부정적 연구 결과 최종 모델 카드 제작 (2026-11-27)

## 목표/증거

- C15/C16 실제 연구 결과의 **부정적 성능 결론을 은폐하지 않고** 교육용/연구 감사용 모델 카드로 정리.
- 근거: P2 소형 Owner 집계, Train11/Val3, sealed Test4, P3 read-only checkpoint SHA 확인 및 AI OFF E L3 main PASS 기록.
- 출고 산출물: [C Dataset v1 Frozen ResNet18 모델 카드](../../../../ai/docs/C_V1_FROZEN_RESNET18_NEGATIVE_RESULT_MODEL_CARD_KO.md).
- 본 문서는 외부/private 이미지, 미승인 `.pt`, 원본 사람 승인 서명, 개별 예측을 포함하지 않음. 공개 가능한 집계와 SHA만 기록함.

## 검수 체크포인트

1. 연구 모델 `C_RESEARCH_PILOT_ACCEPTED=false` / `E_AI_ON=HOLD`와 제품 모델 아님을 최상단 표기.
2. 데이터 Train11 Val3 / sealed Test4 유지; 기준선은 **사후 비교**이지 사전 acceptance 임계값이 아님.
3. Loss/accuracy 원본 수치·epoch3 선택, Train mini-batch 로그와 checkpoint final inference의 차이 구분.
4. 확인 가능한 오류 원인 vs 미확정 가설 구분; 실제 UNSTABLE false-negative/UNKNOWN coverage/Test score를 만들지 않음.
5. 비상업적 내부 연구·교육/가중치 재배포 금지·A19/Production Contact/AI OFF 보호. C20 별도 승인 전 새 데이터나 학습 금지.

## 교육 결론

프로그램 정상 종료와 체크포인트 생성 및 인수 SHA PASS는 **학습 파이프라인의 기술 성과**입니다. 그러나 작은 Validation에서 기준선보다 낮은 실제 모델은 **제품 출고할 수 없습니다**. 유효하지 않은 성능 수치를 보강하기 위해 Test4를 소비하거나 연구 이력을 재작성하지 않는 것이 핵심 교육 포인트입니다.

**상태:** `C18_MODEL_CARD_COMPLETE_NEGATIVE_RESEARCH_PRESERVED`, `P3_TEST_SEALED`, `E_AI_ON=HOLD`. 신규 WSL2 실행 불필요.
