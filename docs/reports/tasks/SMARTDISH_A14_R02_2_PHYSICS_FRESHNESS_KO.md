# R02-2 — Physics 컴포넌트 갱신 증명 (교육용)

## 배경
R01 Owner 물리 양성 교정과 R02-1 Cloud 관측 PASS를 재사용한다. ST-02 2초 새 진단만 수행한다. R02-1 observer는 빈 값 자체를 freshness로 승격하지 않았다.

## 원리
Harmonic gz-sim8 8.15.0 [Physics.cc](https://github.com/gazebosim/gz-sim/blob/gz-sim8_8.15.0/src/systems/physics/Physics.cc) (blob 14c7d5eb6aaf396d8d710340e2bc9cff542e4f3c) UpdateCollisions는 각 ContactSensorData에 SetChanged(NoChange/PeriodicChange)를 호출한다. [ECM](https://github.com/gazebosim/gz-sim/blob/gz-sim8_8.15.0/src/EntityComponentManager.cc)의 SetChanged는 OneTimeChange를 제거한다. PreUpdate에서 metadata만 OneTimeChange로 표시하고 PostUpdate에서 상태를 읽는다. Contact protobuf payload, pose, force, collision 및 ROS 메시지는 변경하지 않는다. 100 iteration마다 Update에서 의도적 late re-arm을 적용하여 marker가 그대로 남는 음성 대조군을 한 진단에 포함한다. 실제 Physics 실행 순서가 다르거나 generic reset이 marker를 제거하면 이 대조군이 실패해야 한다. CMake는 8.15.0 EXACT; vendor binary hash 기록.

## 검수 경계
매 스텝 collision/sensor ID 동일, 실제 sim time/iteration 1ms coverage, marker armed 및 정상 step의 해제, late control에서 marker 잔류를 검수한다. 이것은 해당 contact component 갱신 경계 증거이며, 개별 collision의 engine registration 및 빈 ROS 메시지 전달 증거까지 보증하지 않는다. GT UNKNOWN/HOLD, 사람 승인 0 유지. 진단 제어는 생산에 사용 금지.

## 검증 상태
음성 fixture 작성, 실제 테스트 실행은 전용 CI에서 확인한다. 신규 C++ build/실제 Gazebo 진단은 커밋 시점 미검증. 기존 A14/P0와 R02-1 CI 재실행 금지. R02-3 통합은 별도 단위; 실제 생산 RGB t0 구간에서 재검증하기 전 인수 출고 금지. 

## 실제 CI 결과 (2026-11-26 KST)
- SHA `a71c2b67ac9eb3aafc902ed4775ff64dfbc68a44`, [Run #45727749943](https://github.com/silverbjin/samsung_AXI/actions/runs/45727749943) completed success. L0 13 passed, L2 real C++ build and metadata normal/late negative control PASS; log `R02_2_REAL_PHYSICS_COMPONENT_REFRESH_PASS_GT_HOLD`.
- [Artifact #15075900684](https://github.com/silverbjin/samsung_AXI/actions/runs/45727749943/artifacts/15075900684) inner TAR SHA from CI log `aa9cb11679ba78e0cfdfd496eecb4001bfa9051883ad486c194c6b66713cca7e`, ZIP digest `a56be4a02b0189a9a415d585c6066eeaa41b50c4d07b41e5bc2de19194c182f1`. Cloud binary independently rehashed outside CI: NOT_RUN. Vendor Physics binary SHA `c672bc21950d6c522e1238c050550112cfc124dc34219aa7b173d862e4795fa8`. R02-2 component-refresh PASS, no GT promotion.
