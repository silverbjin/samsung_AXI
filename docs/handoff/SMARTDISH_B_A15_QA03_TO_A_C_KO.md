# B-QA03 → A16/C 데이터 인계 및 독립 검수 조건

## A15 현재 상태 (출처 분리)

A15 **이전 Owner 원본 검수 보고** SHA `828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05`: data 4/4 + GUI 4/4 PASS, server cleanup -11 ×4 FAIL, contact production health HOLD, GT UNKNOWN_HOLD, human labels 0. QA03 공식 CLI의 실제 원본 오프라인 검수는 FOV 스키마 연결 오류 수정 후 exit0 REVIEW_ONLY, B-Q01 PASS / Q02~Q07 HOLD. outer15/inner64, 4 RGB/초기 지지/1ms Pose·ECM·500 명령/ROS exact positive subset을 직접 검증. 새 Owner WSL2 runner는 미실행. Cloud CI #45737733210과 Owner는 동일 family/layout 재연이며 독립 표본 8개가 아니다. A15를 다시 돌려 데이터 4개를 재생성하지 말 것.

## A16 요구안 — 품질 우선, 단순 seed 반복 금지

1. A15의 2 family/4 layout 구조를 그대로 보존하면서 각 family에 **여러 안정·불안정 후보**를 교차 추가하되, 중앙/편심/색상/배경/카메라/외란/파일명과 후보 결과가 일대일 매핑되는 shortcut을 피하십시오.
2. t0 사전 200ms 실제 지지·안착과 `CameraInfo`·Pose 1ms 동일 시각은 유지하고, 초기 FOV 및 자연스러운 가림은 사람 검토용 시트로 남깁니다.
3. 실제 measured wrench·동적 tray pose가 없는 STATIC_TRAY_COMMON_TORQUE_PILOT 결과를 ROBOT_MOTION/안전 인증이라고 주장하지 않습니다. 0.015m는 비교 후보 기준이며 확정 판정 임계치가 아닙니다.
4. Contact component refresh(10300×4 topic)와 ROS 동일 시각 positive pair 매칭은 **full production health**가 아닙니다. 엔진 collision registration, silent channel 및 ROS 전체 전달을 별도 계약으로 검증하십시오.
5. 물리 데이터 PASS와 Gazebo teardown -11 FAIL을 분리하여 보존하십시오. 기존 A15 실물리 반복 대신 필요할 때만 별도 종료계약 실험을 계획합니다.
6. 생산 스키마 `physical_layout_id`, `geometry_family_id`, camera intrinsics, SHA, versioned trigger/physics policy, release profile을 장면별 고정하고 독립 그룹 평가 전에 사람이 물리적 차별성을 검토하게 하십시오.
7. 확대는 우선 4~8 신규 독립 loaded-domain 구성으로 소규모 QA. 이전 제안의 60장면/6 family는 승인되지 않은 계획 수량이며 강제 게이트가 아닙니다.

## B → C 실제 승인 계약

현재 C의 실제 Owner 승인 manifest 0, independent train/val/test split 0, real training 0입니다. C는 `t0 RGB`만 추론 입력으로 사용할 수 있습니다. post-t0 Pose/velocity/contact/trigger 결과, scene ID/filename/seed/geometry label은 대상 안정성의 미래 정보 또는 shortcut이므로 **RGB-only 모델 입력 금지**. B의 raw validation·사람 검토·사용권·독립 geometry family split·중복 감사·C readability가 모두 PASS될 때만 별도 승인된 manifest를 만들 수 있습니다. C dummy-only 개발은 별도 브랜치에서 계속 가능.

## 다음 작업

실제 B 오프라인 CLI 검수는 완료되었습니다. private `qa_report.json`, 4행 공란 worksheet 및 진단 TAR/sidecar로 운영자 가림·안착·사용권을 검토하십시오. 정확한 수정 SHA로 WSL2 원샷을 사용하면 기존 원본의 읽기 전용 재검수만 수행됩니다. A16 신규 4~8 독립 구성은 계획이며 데이터셋 출고 승인이 아닙니다. **원본 물리 시험 반복이나 main 병합은 이 단계에 필요하지 않습니다.**
