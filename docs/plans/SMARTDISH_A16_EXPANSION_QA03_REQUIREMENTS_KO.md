# SmartDish A16 — A15 파일럿 품질 검수 기반 다음 확장 요구(제안)

A15 기존 네 장면·SHA·물리/GUI 인수 결과를 보존합니다. QA03의 Owner 원본 직접 재감사 완료와 운영자 검토가 우선입니다. 그 전에는 자동 대량 수집/사람 승인/모델 학습으로 넘어가지 않습니다.

**P0**: Owner archive 직접 QA03 검증과 B 계약 보완, 제품 입력 RGB(t0)·실물 물리 결과에 대한 인간의 가림·안착/지지·측정 provenance 검수. Contact production health는 HOLD로 명시, cleanup -11은 데이터와 별도 처리.

**P1**: 기존 두 형상 계열 내에서 중앙/편심만 바뀐 구조가 클래스 예측 shortcut이 되지 않도록 높이, 반경, 받침면 접촉 여유, 적재 수, 회전, 균형·near-boundary 사례를 교차 설계하고, 실험 정보(geometry family/layout/env/trigger/seed)를 content hash로 관리. 동일 layout의 Cloud/Owner 반복을 학습 분할 독립 표본으로 세지 않음.

**P2**: 초기 소규모 4~8 독립 장면의 B-Q01~Q06 검증 후에만 60/6+ family 후보 확대를 재검토. RGB top-only와 DACON 384x384 front/top 영상은 동등한 관측 영역이 아니며 C 제품 경로는 기존 단일 top RGB.

**P3**: 동적 tray/ROBOT_MOTION은 STATIC_TRAY_COMMON_TORQUE_PILOT와 분리된 후속 시험. 실제 가속/회전·측정 wrench·TF를 갖춘 경우에만 동적 안전성 자료로 출고하며 AI OFF/S7 경로는 변경하지 않음.
