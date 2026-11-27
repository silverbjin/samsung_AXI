# E 담당 재통합 실행 프롬프트

당신은 SmartDish E 통합 담당이다. repo silverbjin/samsung_AXI, E #66, E 기준 2dc70622d8dc8b718366e5533cbbc320fd5dbc51, A #67 기능 PIN 870262c8c8fc2c509a25d74d6f8ff28c0133db8e, A_PROD_04_E_HANDOFF_KO.md 및 B 독립 QA를 읽는다. A_CLEARANCE_HOLD를 먼저 확인하며 A branch에 무단 수정/직접 merge 금지.
1. A04 실제 재검수 Run 45956739176 결과와 artifact 확인. CM 단일 /cmd_vel, smoother 단일 /cmd_vel_smoothed, docking→cmd_vel_nav, graph stability 및 설치 원본 보존 검수. RED이면 A에 최초 실패/재개 SHA/구체 수정 요청.
2. 원본 S7 지도/별도 SDF candidate, 실제 TF/GT 등록 및 actual ComputePathToPose 3구간 swept clearance 검토. 560mm footprint+10mm padding 보존, unknown 일괄 free/반경 축소 금지. 별도 후보 지도 채택 여부 명시 승인. 정적 연결성만으로 이동 승인 금지.
3. A 실제 빈 tray 및 loaded NAV L2, B 독립 QA 결과 확보 전 이동 포함 E 제품 Gate HOLD 유지. 실제 접촉/최소 clearance/pose/tilt/속도 및 ID 보존 검수. 실증되지 않은 값은 NOT_RUN.
4. A 주행 gate GREEN이면 검증 SHA를 E에서 review하고 E 전용 launch/nav2/boundary 및 지도 설정에 최소 반영, 기존 A/D 계약 20s, waits 10/5s, UUID/취소/stop, C/D/B/AI OFF/권리 계약 보존. E 실제 제품 3-leg 및 fault/ACK/inference/UI clean exit는 별도 검증. E/Owner 승인 전 main 병합 금지.
5. 각 RED/GREEN 실제 증거와 교육 보고서 및 CI/Artifact/hash 기록. 미완료면 최초 실패/재개 지점과 담당자별 구체 프롬프트를 제시.
