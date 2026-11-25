# SmartDish B — DACON 236686 데이터 품질 기준선 v1.0
- 작성일: 2026-11-25
- 상태: DACON 통계 기준선 확인 / 물리 GT 정량 검증 HOLD / SmartDish B 실제 증거 대조 대기
- 목적: A/B/C 팀 간 입력·정답·평가 계약 확립. 본 문서는 GitHub 병합을 수행한 결과가 아니다.

## 1. 근거와 검수 범위
첨부 `dacon_audit_20261125T065353664123Z.zip`, SHA-256 `6870dd8eed856525a71bccf78f33616dda18b04ede43e9f9c6270bfe4302ae0a` 직접 대조 일치, ZIP CRC PASS. `summary.json`, `sample_manifest.csv` 2,100행, `image_stats.csv` 4,200행, `csv_labels.csv` 2,100행, `duplicate_images.csv` 800행, `video_stats.csv` 12행, `issues.csv` 0행, 대표 이미지 시트 10개(40장면), 영상 시트 12개(48프레임)를 검사했다. 원본 ZIP 자체 및 원본 해시의 배포 출처는 독립 검증하지 않았다.

|분할|장면|stable|unstable|영상|
|---|---:|---:|---:|---:|
|Train|1000|500|500|1000|
|Dev|100|48|52|0|
|Test|1000|비공개|비공개|0|

모든 이미지 RGB PNG 384×384, 장면별 front/top 완비. 영상 표본 12/12 384×384, 30 fps, 300 frames, 10s, MPEG-4. 영상 전체 디코딩·물리 좌표는 미검증. 6 stable은 표본 시점에서 외형 유지, 6 unstable은 2.5초 시점에 붕괴/분리 관찰. 실제 붕괴 시간, 누적 1.5cm, 순간 복귀 여부는 판정 불가.

|분할|front 평균 밝기 / 표준편차(이미지 간)|top 평균 밝기 / 표준편차|
|---|---:|---:|
|Train|214.20 / 3.73|221.67 / 2.30|
|Dev|190.88 / 11.21|195.83 / 11.73|
|Test|191.47 / 10.52|196.82 / 11.25|

밝기 값은 전체 프레임 통계(0~255), 대상 자체 밝기가 아니다. 대표 이미지에서는 사선 전면/상단, 다양한 적재 높이·폭·형상·기울기, Dev/Test의 그림자 및 관측 변화가 관찰된다. 직립형도 붕괴하며 가느다란 구조도 안정 가능. 모든 unstable이 초기 정지 상태라는 보장은 없다.

## 2. 독립성 결함
`image_stats.csv`에서 split/id로 front/top 픽셀 해시를 묶어 비교: Dev 100개 모두 Test의 서로 다른 100개와 두 이미지의 파일 해시 및 픽셀 해시 일치. 200 중복 해시 그룹(각 2개 이미지), 총 4,000 고유 이미지, 2,000 고유 이미지 쌍. Train과 타 split 간 정확 중복 없음. 근접 중복/동일 기하 구조의 다른 렌더링은 미검증.
공식 안내는 dev 학습 허용, test 학습 금지. 중복의 의도나 배포 오류 여부는 미확정. 중복 ID 대응이나 test 정답 추정은 제공하지 않는다. SmartDish에서는 동일 scene/geometry family를 split 간 공유하지 않는 독립 holdout을 요구한다.
공식 참고: https://www.dacon.io/competitions/official/236686/data
https://www.dacon.io/competitions/official/236686/overview/description
https://dacon.io/en/competitions/official/236686/overview/rules

## 3. SmartDish 제안 계약 (사용자 승인 전 v1.0)
대상은 트레이 적재 식기의 미래 안정성. 정지 중 중력 안정성과 주행 중 가감속 안정성을 별도 프로파일로 정의. 초기 입력 RGB(t0), 이후 물리 증거는 label only. 단일 카메라 제품 경로 유지, 연구용 추가 측면/상단 시점으로 관측 가능성 검증. 두 시점 모델은 제품에 두 시점이 없으면 직접 배포 금지. 동일 물리 초기 상태, sim time 동기화, 원본과 전처리 별도 보존. 384×384는 비교 입력 후보, 원본 640×480 유지 및 종횡비 보존(letterbox).
관찰 10 sim seconds는 DACON 비교 프로파일 제안. 실제 로봇 주행 프로파일은 속도/가속/회전/지속시간을 별도 고정. t0 이전에 붕괴하거나 로딩·스폰 오류가 난 장면은 UNKNOWN/INVALID. 단 초기 자세의 기울기만으로 제외하지 않는다. t0 스냅샷은 외란 전 기록.
트레이 상대 좌표 T_tray,dish = inverse(T_world,tray) @ T_world,dish. 물체별 누적 이동 L_i = sum ||p_i(k)-p_i(k-1)||, max_i L_i를 기준 후보로 기록. 물체별 순변위, 회전각, 전도, 접촉/지지 상실, 트레이 이탈, 속도 함께 기록. 고정 sim time 샘플링·노이즈 처리와 단위 명시. 0.015m는 DACON 비교 후보일 뿐 제품 임계치 미승인. 누적 이동과 붕괴를 OR로 평가하는 비교 규칙을 명문화. 기록 누락/경계/충돌은 UNKNOWN, 사람 검수 전 ground_truth_approved=false. 자동 라벨과 시나리오 기대값을 분리. 실제 pose/velocity/contact 증거에서 독립 판정.
같은 기본 구조를 변형하여 높이, 편심, 지지면, 접촉, 가림을 교차 설계. 각 형상에서 양 클래스 및 경계 사례를 확보. 질량/마찰/외란이 이미지에서 관측 불가하면 고정하거나 명시적 제품 입력에 추가, 그렇지 않으면 이미지 단독 결정론적 예측 불가를 인정. 조명/배경/재질/카메라 조건이 클래스와 일대일 대응하지 않도록 교차 설계.
분할은 stack/geometry family 그룹 우선, scene/seed/프레임/렌더링 변형 단위 누출 차단. 분할 간 exact hash 및 그룹 중복 0. 유사 구조는 검토. test는 모델 선택·threshold 설정에 미사용.

## 4. 검수 게이트
|게이트|PASS 조건|HOLD 조건|
|---|---|---|
|B-Q01 Provenance|A-13 원본 SHA 및 내부 해시 모두 일치, 출처/버전 기록|누락, 불일치|
|B-Q02 Input|제품 입력 규격·카메라 pose·t0·동기화·디코딩 전수 확인|시점/형식 불명, 물체 가림으로 정보 부족|
|B-Q03 Physics|시뮬레이션 시간·물체별 tray 상대 pose/velocity/contact 궤적 완비, 규칙 버전 명시|물리 증거 누락, 불완전 관찰|
|B-Q04 GT|독립 규칙과 사람 승인, 불일치 해결 또는 제외|기대 라벨 복사, UNKNOWN 학습 혼입|
|B-Q05 Diversity|형상·클래스·관측 환경 교차 커버리지, 경계 사례 명시|ST/UN이 외형/배경/ID로 구분|
|B-Q06 Split|그룹 및 정확 해시 교차 중복 0, 근접 중복 검토|장면/파생 프레임 교차 누출|
|B-Q07 C contract|승인 manifest와 입력/정답 분리, 데이터셋 카드, 모델 학습 재현 정보|미승인 데이터 혼입, 미래 정보 입력|

MVP 추천 규모(확정 수치 아님): 기존 ST-01/02 UN-01/02는 기능 smoke 유지. 데이터 파일럿 60 독립 장면(클래스당 30 목표), group-aware 36/12/12(가능한 경우 클래스 균형). 6 형상 계열 이상, 각 클래스의 경계 사례 포함 목표. 분할 그룹 및 라벨 실측 결과가 목표와 충돌하면 샘플 추가보다 원인 확인 우선. 파일럿은 파이프라인 검수용이며 성능 인증용 아님. 이후 독립 장면 200~500개로 확대 판단. 모델 평가는 LogLoss, confusion matrix, unstable recall, calibration, slice 성능 및 단일/다중 시점 비교. 모델 안전제어 자동 승인 아님.

## 5. B 담당 다음 제출
A-13 원본 archive SHA 및 provenance, sample manifest, image stats, camera metadata, physics trajectories, GT candidate/approval records, group split manifest, duplicate summary, class × geometry × environment coverage, 대표 front/top(또는 제품 카메라) 및 시간대별 비교 시트, dataset card와 실행 로그. 원본 파일 전체 재업로드 불필요.
기존 A-13 WSL2 4/4 기능 인수와 AI OFF 제품은 보존한다. B 실제 데이터 아카이브는 본 대화에 미첨부이므로 B의 실패/성공을 확정하지 않는다. C 더미 기반 개발은 독립 진행 가능하되 실제 GT 학습 출고는 B-Q01~07 충족 후 승인. 별도 브랜치에서 변경하고 교육 보고서와 증거를 함께 보존한다.
