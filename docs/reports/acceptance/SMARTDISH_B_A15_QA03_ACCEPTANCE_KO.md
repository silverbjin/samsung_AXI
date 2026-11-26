# B-QA03 — A15 Owner 데이터 품질 검수 원장 (2026-11-26)

**검수 코드 개발 범위**: A15 nested 15+64 archive, CPU 1ms Pose/Contact/torque/RGB/GT isolation, fixture regression 25 PASS. **현재 이번 B 직접 원본 재계산: NOT_RUN** (원본 `a15_pilot_evidence.tar.gz` 및 `.sha256`가 이 실행 환경에서 확인되지 않음). 기존 A15 Owner 보고서 4/4 PASS는 기존 증거로 존중하되 재검수 PASS로 승격하지 않는다.

| Gate | 이번 B QA03 직접 판정 | 처리 및 장애 |
|---|---|---|
| B-Q01 | HOLD | Owner TAR SHA `828c168...` 실제 압축 바이트 미접근, nested 15/64 직접 재검 NOT_RUN |
| B-Q02 | HOLD | 이전 Owner 보고는 t0 PNG4/CameraInfo/loaded support PASS; 이번 B 원본 픽셀/가림 직접 미검 |
| B-Q03 | HOLD | 이전 보고에 Pose 164816/ECM 164800/ROS72951 및 500 trigger 기록; 직접 재계산 미실행, full production contact health HOLD |
| B-Q04 | HOLD | 승인자 0, `UNKNOWN_HOLD`, label 자동 추론 금지 |
| B-Q05 | HOLD | 이전 2 geometry family/4 layout, 단일 조명·카메라·외란, 클래스 shortcut 위험 |
| B-Q06 | HOLD | 그룹 기반 train/valid/test 미출고, Cloud↔Owner 동일 layout을 별도 그룹 계산 금지 |
| B-Q07 | HOLD | 승인 manifest 및 C real 학습 금지, RGB(t0)만 장차 사용 가능 |

### 현재 원본 기준 이전 Owner의 핵심 수치(직접 B 재계산 아님)

| Scene | Upper 최대 변위 m | 누적 거리 m | 내부 SHA |
|---|---:|---:|---|
| L15-01 | 0 | 0 | `99dd1d75880f6c9c14b9149da71f70c098b8234a1292c03cf353a162cb0edb77` |
| L15-02 | 0.8198921434956602 | 1.0207173090787534 | `e22d124764777d1e0bf3c8024557cc00d134d9804425840d6eccddf1c224ec97` |
| L15-03 | 0 | 0 | `fb1dc964c436fb725c1f3f78579dca150b950e1637e9b58014c78a09942e2f25` |
| L15-04 | 0.7811042800856003 | 1.0323368975342706 | `8c3e1c5569685811f56f501a46b9be596c65707528e6471f3a0d83d2c4662425` |

**분리 판정**: A15 DATA Owner 4/4 PASS (과거), GUI 4/4 PASS (과거), Gazebo server cleanup 4/4 -11 FAIL (과거), all owned stopped TRUE, B QA03 직접 raw NOT_RUN, model GT UNKNOWN, human approved 0, `production_contact_health=HOLD`, E/main merge HOLD. 새로운 full Gazebo 재수집 불필요.

### 앞으로 원본 파일 바이트가 제공될 때에만 적용할 전환 조건

1. 외부 Owner SHA + 내부 outer 15 + inner 64/64 전부 직접 PASS.
2. 4장면 1ms Pose grid 및 tray-relative 4개 entity × 10301, 500 torque command, ECM refresh/ROS exact positive subset 직접 검증.
3. 형상 family ID/레이아웃 재계산, PNG pixel/hash 및 split 독립성 재검.
4. 검토용 worksheet 생성. **원본 직접 검수 성공 후에도 Q04~Q07 HOLD** 유지. C 승인/학습 자동 실행 금지.

A15 생산 코드 원본 보고: [`docs/reports/acceptance/SMARTDISH_A15_OWNER_20261126_KO.md`](https://github.com/silverbjin/samsung_AXI/blob/ea68e96710b62e982308fe740afeeba6081fd551/docs/reports/acceptance/SMARTDISH_A15_OWNER_20261126_KO.md).
