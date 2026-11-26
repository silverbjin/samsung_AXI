# 차기 A 독립 데이터 확대 요구 (QA05 실제 결과 전 잠정)
기존 QA04 보고의 4 family/12 layout, 동일 overhead, signed offset 결합, 66 aHash 후보를 근거로 한 잠정안. 실제 ROI/shortcut 결과 이후 확정. 신규 A 과업 번호는 A17 독립 종료 장애 과업과 충돌 여부 확인 후 확정. 4–8 독립 파일럿: 기존 family 내 지지 여유 작은/큰 × signed offset 양/음 × 중앙/편심을 교차하고, 신규 family는 형상·2/3+ 적재 수·높이·가림을 교차. 물리 변수 질량/마찰/외란은 RGB에서 숨겨진 경우 고정하거나 제품 입력/예측 목표를 먼저 합의. 카메라/배경 변화는 동일 layout observation group, 클래스와 결합 방지; seed/색만 변경한 구성은 새 layout 아님. near-boundary 실제 관측 후 사람 검토. 60 layout/6 family는 비교 출발점, 승인 수량/성능 보장 아님. 실제 QA05 보고의 빈 교차 cell을 기반으로 수량/설계를 갱신. 이번 B에서 Gazebo 신규 생성 금지.

공식 QA05 성공 시 next_a_requirements.json은 실제 family×nominal center×signed offset의 빈 조합 및 고정 변수 목록을 추출한다. A 담당은 해당 목록을 바탕으로 최소 독립 파일럿의 각 장면을 설계하고 사용자가 검토하기 전 신규 과업 번호나 생산량을 확정하지 않는다.


## 실제 QA05 근거 및 차기 A18 제안 (2026-11-26)
A17 cleanup branch/PR53 존재, A18 branch 미발견; 데이터 확장 과업은 A18로 제안, 아직 생성/승인 아님. 실제 12 layout에서 small offset +5/-1 모두 유지, large +4 모두 큰 변위, large -2 모두 유지. World-Y torque 고정이므로 부호×크기 상호작용을 물리 원인 후보로 보존하되 예측 목표가 방향 조건부인지 사전 확정. 15/24 family×nominal center×sign cells 미확보. 4~8 신규 독립 파일럿 제안: F1/F2에 CENTER 및 negative offset 대조 2개; F3에 CENTER large negative 및 near-zero margin 2개; F4에 ECCENTRIC large negative 또는 CENTER large positive 대조 2개; 새로운 family 2개는 2/3+ 적재 및 near-boundary 조합에 우선 배정(총 최대 8, 상세 기하 설계에서 중복 점검). 예상 관측값 사전 라벨 금지. 색/배경/카메라 변화는 동일 layout 관측 그룹, 숨은 마찰/질량/torque는 현재 고정 유지 또는 명시적 입력 계약 개정. 0.03m bin은 탐색적; 신규 결과로 보정, 실제 초기 지지/settle 검증 우선. 60/6은 비확정 확대 목표. A17 코드나 기존 원본 수정 금지. B 새 버전 어댑터 필요.
