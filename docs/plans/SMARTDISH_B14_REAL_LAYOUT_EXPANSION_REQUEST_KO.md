# SmartDish B-14 실제 독립 적재 배치 확장 — A 담당 인터페이스 요청

## 현재 A 코드에서 실제로 가능한 범위

- `scripts/smartdish_a_tray_live.py`의 실행 방식: `demo`, `single`, `batch`, `smoke`, 옵션 `--scene`(ST-01/02, UN-01/02), `--seed`, `--gui/--headless`, `--expected-sha`.
- `scripts/smartdish_tray_world.py`의 `placements(scene_id,seed)`: 현재 4개 고정 조합·좌표·크기·기울기 레이아웃. seed로 변화하는 것은 각각 x/y의 **±1mm 미세 jitter**.
- 따라서 현재 A 코드만으로 **증거 재현 및 통계적 반복성**을 확인하는 것은 가능하지만, 독립 물리 배치 수를 클래스별 3개 이상으로 실질 증가시켰다고 판정할 수 없습니다.

## A 개발자에게 요청할 최소 계약

현재 성공한 A-13 sensor/physics/GUI 경로는 수정하지 않고 구성 입력에 아래 항목을 선택적으로 추가하는 방안을 검토합니다.

1. `physical_layout_id`: 초기 식기 기하 및 조합의 내용 기반 불변 해시, seed와 별개.
2. 실제 변화 항목: 적재 개수·치수·무게/마찰 승인 프로파일·x/y/z·기울기·쌓기 조합 중 최소 1개를 구조적으로 변경한 명시적 layout config.
3. 기존 `trial_id`, `seed`, PNG+Pose+physics SHA/size+timing 계약은 그대로 유지.
4. A-13 L2 owner 4/4 PASS 증거는 재사용하고, 새 layout 변화만 A 담당 독립 브랜치에서 테스트.
5. B에서 생성하는 실제 approved dataset이 아닌 **A의 물리 근거 후보**로 유지 (`REVIEW_REQUIRED`).

## 단계화

- 1차: 이미 인수된 4개 후보로 사람 라벨 검토만 진행. 무단 승인 금지.
- 2차: 실제 **신규 독립 레이아웃**이 클래스별 최소 1개씩 더 생긴 뒤 B 그룹 분할 정책 검증.
- 3차: 클래스별 독립 50배치 목표는 학습·검증 품질을 보면서 조정(자동 게이트 아님).

데이터 누수 위험이 있는 seed 반복은 별도 시험 자료이지 학습 분할용 독립 표본이 아닙니다. 현재 B-14 확대 생성을 위해 A 코드를 임의 변경하거나 Gazebo를 재시작하지 않습니다.
