# SmartDish A Tray → B/C/E 기술·데이터 계약 인계

## 1. 공급 토픽과 원본 범위

- Gazebo: `/smartdish/tray/image_raw` `gz.msgs.Image` → `ros_gz_bridge` (`GZ_TO_ROS`) → ROS 2 `/smartdish/tray/image_raw` `sensor_msgs/msg/Image`.
- 초기 구성: 640×480 RGB, 5Hz, `smartdish_tray_optical`, SensorData QoS(best-effort/volatile), Gazebo sim stamp. 정확한 실제 encoding·QoS 및 출력률은 L2 로그에서 재검증.
- 실제 동적 식기 Pose: Gazebo `/world/smartdish_tray/dynamic_pose/info` `gz.msgs.Pose_V` → `/smartdish/tray/poses` `tf2_msgs/msg/TFMessage`. 제어/안전 ROS 토픽을 발행하지 않습니다.
- 독립 4 시나리오 초기 배치의 mass/inertia/collision/friction은 SDF manifest에 고정. static S7 `STACKED` fixture와 별개입니다.

## 2. B 담당 사용 절차

A 원샷으로 생성된 `trial_0001/tray_rgb.png`는 **라벨 없는 원본**이며 `trial_0001/physics_observations.jsonl`은 반드시 같은 run_id/scene/stack_id에서 나온 **별개의 실제 pose 근거**입니다.

1. `trial_summary.json`의 `capture_stamp_ns`, `pose_at_capture_ns`, `observation_start_ns`, `observation_end_ns`, `physics_sha256`, `image_sha256`과 실제 파일 SHA를 확인합니다.
2. `initial_state.json`/JSONL/`final_state.json`로 낙하·지지·전도 여부 및 캡처 시점의 타당성을 사람이 검토합니다. 관측 코드의 `HELD_OBSERVED`/`FALL_OBSERVED`는 **정답 자동 판정이 아니라 검토 후보**입니다.
3. 충분한 근거가 있으면 사람이 `STABLE` 또는 `UNSTABLE`, 사용권 `OWNED`를 명시적으로 결정합니다. 애매하면 그대로 `REVIEW_REQUIRED` 보류.
4. 그 뒤 **기존 B 코드만** 사용하여 등록:

```bash
cd ~/samsung_AXI_A_TRAY
python3 ai/scripts/collect_tableware.py \
  --image generated/smartdish_tray/run_<ID>/trial_0001/tray_rgb.png \
  --physics-evidence generated/smartdish_tray/run_<ID>/trial_0001/physics_observations.jsonl \
  --root . --manifest ai/data/manifest.csv \
  --label STABLE --scene-id tray-ST01-001 --stack-id tray-stack-001 \
  --source GAZEBO_TRAY --license-status OWNED --camera /smartdish/tray/image_raw
```

**위 경로/라벨은 사용 절차의 예시이며 실제 관측을 승인한 결과가 아닙니다.** `scene_id`와 `stack_id`는 반복 샘플과 불변 물리 배치를 구별하도록 유지해야 합니다.

5. 클래스별 독립 stack_id 최소 3개 이상 등 B Dataset Card의 품질 하한이 충족된 뒤 `python3 ai/scripts/prepare_dataset.py --root . --manifest ai/data/manifest.csv --out ai/data/split_manifest.csv --report ai/data/quality_report.json` 수행. 처음 4건의 자료만으로 Train/Val/Test 성공을 보장하지 않습니다. `--allow-fixtures` 금지. B manifest를 A 코드가 자동 업데이트하지 않습니다.
6. 원본 `generated/` 및 `ai/data/private/`는 비공개, 라이선스·개인 로그 Git 공개 금지.

## 3. C 담당 사용 절차

기존 `src/smartdish_ai/smartdish_ai/stability_inference_node.py`는 `qos_profile_sensor_data`로 해당 토픽을 구독하며 rgb8/bgr8를 처리합니다. 프레임 TTL은 **도착 시 monotonic 기준 2초**입니다. 5Hz면 정상 시 0.2초 간격의 신규 프레임이 필요하며 실제 L2에서 rate·stamp 증가 확인 후에만 생산용 주장합니다.

실행(기존 ROS 빌드 후):
```bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run smartdish_ai stability_inference_node
```
모델/가중치가 없는 기본 상태에서는 `C_MODEL_UNAVAILABLE` 및 올바른 요청에 `UNKNOWN`을 반환하는 것이 정상. A에서 임의 체크포인트·`STABLE` 결과를 생성하면 안 됩니다. 실제 모델은 B 승인 데이터, 독립 test, Model Card 및 본 RGB 프레임 수신 이후 C 책임으로 배포합니다.

## 4. E 담당 인수·보호 경계

- 베이스 `main@cc66b66a16ffc8020498d973ebe31a5c4ca439e0`, AI OFF 통합 PR #44 완료. **새 트레이 기능은 opt-in world + 별도 bridge**, 기존 E WSL2/restaurant.sdf/Map/Nav2/AMCL/CM/A nav adapter/D UI 변경 0건.
- 신규 브랜치 `feat/smartdish-a-tray-camera`에서 Draft PR. 기존 A 브랜치 재병합하지 않음.
- AI ON 통합은 원본 B 이미지+별도 물리 근거→사람 label 및 권리 승인→C 학습/평가→A 실제 RGB 1프레임/동일 capture_id→D 승인 분기 순.
- 독립 world RGB 시야와 **실제 이동 로봇의 트레이 고정 구조/운동 중 시야 동등성은 현재 미검증**. 로봇 opt-in 카메라 SDF는 제공하되 이동 로봇 트레이 하중 물성을 재개발하지 않습니다.
