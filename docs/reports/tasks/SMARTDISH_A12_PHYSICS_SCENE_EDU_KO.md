# A-12 — Gazebo Harmonic 독립 식기 물리 시험 World (교육용 개발 보고)

## 개발 배경

S7 `s6_stacked_dishes`는 `static=true` 시각 fixture이므로 낙하/전도 물리 결과를 낼 수 없습니다. 독립 `smartdish_tray` world를 시험마다 새로 생성해 인공 결과를 만들지 않고 실제 중력·접촉·마찰을 관측하도록 설계했습니다. 레스토랑 지도/경로 주행을 다시 시작하지 않습니다.

```mermaid
flowchart TD
 S["ST-01 / ST-02 / UN-01 / UN-02 + seed"] --> G["smartdish_tray_world.write_trial()"]
 G --> W["독립 Gazebo physics, Sensors OGRE2, SceneBroadcaster"]
 W --> D["Dynamic dish (collision/mass/inertia/friction/gravity)"]
 D --> PO["/world/smartdish_tray/dynamic_pose/info"]
 W --> RGB["A-11 /smartdish/tray/image_raw"]
 PO --> E["A-13 before/after pos+orientation history"]
 RGB --> E
 E --> HR["B 사람 검수, Ground Truth 승인 전 HOLD"]
```

## 소스와 핵심 함수

- `scripts/smartdish_tray_world.py`: `build_world()`, `plate_model()`, `inertial()`, `write_trial()`, `validate_world()`.
- 동적 식기는 `static=false`, 표준 cylindrical visual/collision, `mass=0.22kg` 실험값, 마찰 `mu=0.65` 실험값, 실린더 관성식 `Ixy=m(3r²+h²)/12, Iz=m*r²/2`로 생성. 고정 joint 없음.
- 시나리오 `ST-01` 중앙 정렬 2장, `ST-02` 크기 다른 세 장, `UN-01` tray 지지면 밖 2장, `UN-02` 틸트/편심 2장.
- 고정 seed로 최초 위치 jitter 재현, `scenario.json`에 scene_id/stack_id/trial_id/world SHA/모델 초깃값/재질·관성/10초 관측 시간 기록.
- 예상 시나리오 명칭만으로 자동 `STABLE`/`UNSTABLE` 라벨 생성하지 않음; `REVIEW_REQUIRED` 고정.

## 테스트와 경계

`python3 -m pytest -q tests/test_smartdish_tray_world.py`

L0 확인: SDF ElementTree, 중력 시스템, 식기 동적·충돌·관성 존재, 재현 가능 seed, 중복 파일 차단, Ground Truth 자동 출고 금지.

**실제 물리 결과는 Gazebo가 sensor+pose를 발행한 다음 A-13 L2 물리 계측이 확보돼야 PASS.** 수집 전은 PHYSICS_NOT_VERIFIED입니다. 정지 10초 안정 관측은 이동하는 로봇의 긴급 제동/실물 안전 인증과 다릅니다.

## B 담당 인계

SDF의 초기 배치/마찰/질량은 실제 실험값이며, B가 시행 결과를 독립적으로 검수해 라벨 승인해야 합니다. 같은 stack_id 연속 프레임을 서로 다른 split에 분리하지 마십시오. 이미 낙하한 후의 프레임만 학습 이미지로 사용하지 않도록 A-13 캡처 시각 계약을 확인합니다.

## 2026-11-24 — 실제 Gazebo L2 전체 검증(최종 관측 사실)

- [GitHub Actions #45325486957](https://github.com/silverbjin/samsung_AXI/actions/runs/45325486957), 실주행 코드 SHA `05779ae191ff41c922e067ec7cc5c2356dcffeaa`.
- L0 **26 PASS**, ROS Jazzy L1 **PASS**, 독립 Gazebo L2 **4/4 PASS**.
- `/smartdish/tray/image_raw` ROS Image 실제 도착 및 B `save_unlabelled_frame()` PNG 실저장 4건, 모든 첫 캡처 timestamp `200000000ns`. 센서 포맷은 런타임 validator에서 `rgb8` 또는 `bgr8`을 허용했으며 각 trial JSON에 원본 encoding/step 포함 여부를 인수에서 확인하십시오. 이미지에 트레이·식기가 모두 적절히 보이는지의 시각 검수는 **사용자 L3**입니다.
- CI console에서 `SMARTDISH_A_TRAY_REAL_GAZEBO_L2_EVIDENCE_VERIFIED` 관측. 각 PNG와 별도 동적 Pose JSONL은 SHA256/size/시간정렬 검증기 통과.

| Scene | 실제 Image→PNG | 10초 동적 Pose 관측 | 원본 관측 판정 |
|---|---|---|---|
| ST-01 | PASS / 0.200s stamp | PASS | `HELD_OBSERVED` |
| ST-02 | PASS / 0.200s stamp | PASS | `HELD_OBSERVED` |
| UN-01 | PASS / 0.200s stamp | PASS | `FALL_OBSERVED` |
| UN-02 | PASS / 0.200s stamp | PASS | `FALL_OBSERVED` |

**원본 시나리오 명칭을 정답 라벨로 사용하지 않습니다.** 모든 trial의 `label=REVIEW_REQUIRED`, `ground_truth=NOT_OPERATOR_APPROVED` 계약은 유지합니다.

- 기존 운영 AI OFF Nav2·D UI·Map/CM 수정 없음. 독립 물리 World의 화면/배치가 실제 로봇 트레이 설치 환경과 동일하다는 검증은 아직 **NOT_RUN**.
- B 담당 최종 안정성 라벨 승인 및 C 실모델 추론은 **NOT_RUN**, A 코드가 승격하지 않습니다.
