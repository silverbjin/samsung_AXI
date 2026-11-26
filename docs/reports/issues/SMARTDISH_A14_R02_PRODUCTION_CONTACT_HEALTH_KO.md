# SmartDish A14-R02 — 동일 sim-time Contact 경계 독립 관측 (1차 진단 구현)

## 1. 목적·범위
- 기존 A14-P0 a99da4207bff358be8b2f228411b94524b2e1c8a / A14-07 2c362863cddbdfd50d656cbc8d97a624e072f04a의 PASS 증거를 재사용한다. R01 Owner NOT_RUN. 보호 main 및 B/C/D는 수정하지 않는다.
- ST-02 기존 production geometry/physics/camera/Contact SDF 생성기를 사용한 **새 2 sim-sec 진단 trial 1회**만 수행한다. 기존 RGB(t0) warmup/capture 10초 실행은 재검증하지 않으며 새 관측 결과를 이전 trial에 소급하지 않는다.
- 이번 최소 증분은 read-only ECM 관측 및 ROS 전달 경계 계측이다. 전체 P0 sensor health/GT 검수의 완료가 아니다. 진단 성공도 R02 전체 완료나 R03 인수 성공으로 승격 금지.

## 2. 원인 확인과 설계 결정
Harmonic upstream gz-sim8의 [Contact.cc](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/contact/Contact.cc) Publish는 접촉이 있을 때만 발행한다. [Physics.cc](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/physics/Physics.cc)의 UpdateCollisions는 ContactSensorData 컴포넌트를 갱신하지만 데이터가 동일할 때 NoChange가 가능하며 engine contact feature 미지원이면 early return한다. 이 브랜치 소스 확인은 설치 vendor 정확한 binary 버전/동작의 대체가 아니다. 따라서 component 존재, 빈 값, observer tick, /clock, publisher discovery를 모두 sensor update freshness와 분리한다.

## 3. 구현
- ProductionHealth.cc: actual ContactSensor, ParentEntity, Collision, ContactSensorData를 PostUpdate에서 const ECM으로 읽는다. sim ns, iteration, dt, topic/model/sensor/collision name, entity IDs, component present, contact count와 collision ID pairs를 TSV에 남긴다. 100000 rows 상한; overflow marker. 물리/센서/브리지에는 쓰지 않고 publish하지 않는다.
- a14_production_health_probe.py: 원래 ST-02 seed211 SDF와 bridge를 보존하고 복제본에 관측 plugin만 추가했는지 비교한다. 실제 ROS /clock 및 Contacts header stamp/pair IDs를 별도 저장한다. 24s discovery, 16s ROS discovery, 38s observe, 95s wall budget, CI 115s 외부 timeout. 세션 별 DDS/partition 및 owned process 정리. 새 window는 원래 t0 관측과 별개.
- a14_production_health_contract.py: SDF identity 및 per-step 1ms coverage, identity IDs, iteration, clock regression/gap, pair matching, source marker, overflow 검수. 정확한 동일 sim stamp의 positive collision IDs 교차검증. partial transport match는 partial로 기록한다. 진단 PASS는 모든 snapshot coverage 및 각 positive channel >=1 실제 일치 요구; 무접촉 증명이나 전체 전송 보장과 다르다. 빈 component는 ECM_EMPTY_FRESHNESS_UNPROVEN. GT는 항상 UNKNOWN/HOLD, 사람 승인 0, approval ledger 미생성.
- 전용 workflow는 신규 경로만 대상으로 하며 기존 A14-07 및 A14-P0 L2 trigger를 변경하지 않는다.

## 4. RED → GREEN 및 증거 원장
- Local RED: 신규 모듈 없이 작성한 pytest의 수집 단계 ModuleNotFoundError, exit 2. 구조적 RED이며 실제 Gazebo 결함 재현 아님.
- Local GREEN: Python pytest 22 passed. synthetic fixture만 사용 (실세계 evidence 아님).
- Local source SHA256: contract da5b8655a477b355d5c7ff118ce373b46e49128a17079f1ccecdd2530118b291; tests 9d4ca6375b085f1d8d849a280ff9d5ab6217f2143463424d99be0e5f9290f7da.
- 이 작성 환경에는 ROS/Gazebo 및 GitHub 직접 network가 없어 C++ compile/L2는 전용 Cloud CI에서 최초 실행한다. 현재 NOT_RUN/PENDING, 결과 확인 전 PASS 기록 금지.
- Artifact: generated/smartdish_a14/r02_production_probe/a14_production_health_evidence.tar.gz 및 .sha256, 내부 SHA256SUMS, 원본/관측 SDF, bridge, raw ECM/ROS/clock, 결과·로그. C++ build log 별도. 실제 생성 여부는 CI 결과로 검증.
- 진단이 PASS하더라도 production_contact_health=HOLD. positive-only calibration으로 과거 silent channel을 NO_CONTACT_OBSERVED로 변환 금지.

## 5. 후속 최소 검증
실제 Cloud probe compile과 raw pair/timestamp match, coverage/clock/SHA를 확인한다. 부족하면 최초 실패 경계를 기록하고 기존 PASS 재실행 없이 수정한다. 빈 ECM의 per-step freshness를 물리 update boundary에서 독립 입증할 수 있는 버전 고정 instrumented 경로를 조사한 뒤 설계/검증한다. 관측 플러그인 자체가 heartbeat를 만든다는 이유로 PASS 금지. 이를 기존 production RGB(t0) 관측 구간과 명시적으로 통합하기 전에는 R03 출고하지 않는다. R04/R05 대기, PR Draft 미병합.
