# B-04 — GitHub Actions 데이터 계약 경량 회귀

- 기준: B-03 `2dfb12045afda1878fa1afa11a882a7c4f592059`; 본 문서와 Workflow 파일은 같은 Git commit.
- 목적: 소스가 원격 GitHub에서도 동작하는지 독립 runner에서 확인. Gazebo/ROS 실물 게이트를 늘리지 않음.
- 추가: `.github/workflows/smartdish-b-dataset-ci.yml`. PR과 B 브랜치의 B 관련 변경 시에만 실행.
- 순서: Python 3.12 → Pillow 12.3.0 / pytest 9.0.2 → compileall → 10개 pytest → 6개 단색 fixture → 그룹 split → `--allow-fixtures` 없는 안전 차단 확인.
- 이 방법을 선택한 이유: B는 ROS 토픽 발행자가 아닌 오프라인 데이터 소유자이므로 기존 대형 Gazebo CI 전체를 추가로 요구하지 않습니다. MOCK_ONLY 가드를 기본 인수 조건으로 넣어 오프라인 PASS가 실제 분류 능력으로 오인되는 것을 방지합니다.
- 최초 작성 시 결과: **GitHub CI NOT_RUN** (실제 Run이 완료된 뒤 이 보고서에 URL 및 결과를 기록). 로컬 10/10 PASS는 별도.
- 원본 증거: GitHub Actions의 `SmartDish B dataset contract CI` 실행 로그.
- 남은 범위: A 카메라와 물리 라벨/현장 확인, C 학습/추론은 NOT_RUN.
- 훈련생 질문: 오프라인 데이터 계약 CI를 실제 Gazebo 회수 주행 인수와 구별해야 하는 이유는 무엇입니까?
