# SmartDish A-13 DBG-16 — WSLg ST-02 RGB warmup one-frame failure, reliable subscription and bounded-step optimization

- 작성: 2026-11-25
- Repo: silverbjin/samsung_AXI
- Branch: feat/smartdish-a-tray-camera / Draft PR #45
- 변경 범위: A-13 real camera warmup only; 기존 S7 AI OFF main/Navigation Adapter/Collision Monitor/B/C/D/UI 불변

## 1. RED: 사용자 실제 원본과 무결성

세 번째 업로드 `smartdish_a_tray_evidence.tar(3).gz`, 외부 SHA256:
`bc86a9fec343af688d59b151b962a536d4ff6962c614046c2949ad7c6c042457`.
`SHA256SUMS`: 17/17 VERIFIED. 실행 HEAD `a9eb6f00b0e4b95db9f1ca2a8e4086dc33a27ce1`.
직전 #45533791807 Cloud CI 전체 PASS였으나 이 **현장 WSLg qualify FAIL**을 덮어쓰지 않는다.

| 증거 | 관측 결과 |
|---|---|
| `summary.json` | `mode=smoke`, `gui=true`, `FAIL`, 0개 성공 trial |
| `failure_context.json` | 최초 오류 `A13_REAL_CAMERA_BRIDGE_WARMUP_NO_TWO_IMAGES` |
| 실패 phase | ST-02 `sensor_warmup`, 식기 EntityFactory 실행 전 |
| Gazebo Image 원본 | `gz topic -e -n 2`, 2개 실제 640×480 protobuf Image. 첫 stamp=0, 두 번째 stamp=0.2s |
| ROS Image callback | `1`건; stamp 1.2s, `rgb8`, 640×480, 921,600 bytes |
| simulation time | 마지막 1.285s; /clock advance 260건 |
| wall elapsed | 77.711s, WSLg 초기 단계의 wall/sim 비율 약 60.5 |
| WSLg renderer | **D3D12 (NVIDIA GeForce RTX 3060)**, accelerated yes. 이전 llvmpipe 아님 |
| ros_gz_bridge | image ROS publisher 1, reliability RELIABLE / durability VOLATILE |
| capture node | image ROS subscriber 1, reliability BEST_EFFORT |
| processes | 실패 시 GZ server·bridge 둘 다 살아 있음, cleanup 완료. 서버의 종료 반환코드는 사후 SIGINT 시 -11로 기록됨 |
| UN-01 | **NOT_RUN** — ST-02 warmup에서 fail-fast |

이전 두 실패 유형:
- 구 SHA `603171dc...`: ST-02 warmup 2 ROS 양수 증가 stamp 미충족
- SHA `5578e6b...`: ST-01/ST-02 통과 뒤 UN-01 post-spawn 신규 ROS Image 없음
- 이번 `a9eb6f0...`: **ST-02 warmup** GZ 초기 2샘플 관측, ROS 1샘플만 관측. 가장 먼저 보이는 실패 지점은 `empty-tray warmup / ROS delivery` 경계.

**원인 해석 주의:** GZ 0초·0.2초 이미지는 초기 두 프레임이며, ROS 이미지 1.2초는 서로 다른 구간의 관측값이다. 두 Gazebo 프레임 중 하나가 ROS로 '유실됐다'고 직접 증명하는 근거가 아니다. DDS BEST_EFFORT 손실 가능성과 5ms Gazebo service 호출 오버헤드는 수정할 가치가 있으나 **단독 근본 원인은 미확정**. WSLg GPU 실제 renderer는 가속 상태임을 확인했다.

## 2. 재현을 설명하는 데이터 경로

```mermaid
flowchart LR
  G[Gazebo RGB 5Hz] --> B[ros_gz_bridge RELIABLE PUB]
  B -->|prior BEST_EFFORT SUB| R[rclpy Image callback 1/2]
  C[/clock 1.285s] --> R
  R --> F{Two positive increasing ROS stamps?}
  F -->|No| H[FAIL + 17 files SHA256 evidence]
```

기존 코드는 빈 트레이에서도 `pause: true multi_step: 5`를 반복 호출했다. 1.285초까지 진행하려면 대략 260번의 동기 Gazebo control service RPC가 필요하며, 렌더링과 ROS callback의 wall-clock 지연을 크게 만든다. **GZ image topic advertised 또는 성공한 probe 2개만으로 ROS image PASS를 합성하지 않는다.**

## 3. GREEN을 위한 최소 수정

1. **단계 한정 스텝:** 빈 트레이 `sensor_warmup`에만 `EMPTY_TRAY_WARMUP_STEP_COUNT=100` 도입. 짧은 service request 수를 줄이며, 100ms simulated steps 뒤 ROS `spin_once`로 bridge 데이터를 처리한다. 첫 두 개의 실제 ROS positive increasing stamps 요구는 그대로 유지한다.
2. **QoS 정렬:** image subscription을 `QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)`로 고정해 현장 bridge의 `RELIABLE` publisher와 정렬한다. Pose/clock QoS에는 변경이 없다.
3. **원본 증거:** 모든 trial에 `warmup_transport_metrics.json` 추가 — GZ probe bytes/hash/frame_count, ROS callback count/stamps, /clock advance, wall elapsed, sim elapsed, wall per sim second. 실패 직전에도 기록하고 SHA256SUMS/TAR에 자동 포함한다.
4. **교육용 음성 회귀:** 2개의 GZ probe sample + 단 하나의 ROS positive stamp는 반드시 **FAIL**. 현장 실패 수치 1.285s/1 ROS를 합성 fixture로 테스트한다. 정상 두 ROS stamp 테스트도 추가한다.
5. 기존 **post-spawn** `multi_step:5`, 510ms pre-fall camera cutoff, 실제 pose/image sync, `A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED`, 10 simulation seconds, B `REVIEW_REQUIRED`, SHA pin, owned process cleanup, protected AI OFF main은 모두 그대로 유지한다.

## 4. 검증/출고 기준

- L0: 변경한 sensor warmup 정책, REAL Image stamps, QoS contract, 기존 runner/manifest 4+ tests. `pytest`/shell syntactic PASS.
- L1: ROS Jazzy `ros_gz_bridge` real interfaces / package build.
- L2-H: real Gazebo 4 scenarios unchanged (ST-01/02 HELD; UN-01/02 FALL).
- L2-G: independent Gazebo GUI ST-01 2 cold runs.
- L2-G-BATCH: same-process GUI ST-01→ST-02→UN-01→UN-02 4/4 plus **warmup_transport_metrics.json** real stamps/ GZ sample.
- Regression product CI: A Navigation Adapter + Restaurant Robot MVP.
- WSLg: unchanged `--gui qualify` → same-SHA CI + real renderer preflight → ST-02→UN-01 smoke → batch → manifest + receipt. CLI callback/clock/GZ failure evidence remains in tar. **Cloud PASS ≠ actual WSLg L3 PASS**, and unsuccessful smoke cannot be promoted.

## 5. Junior debugging checklist

- `ros2 topic info -v`에서 실제 publisher와 subscriber의 RELIABLE/BEST_EFFORT 정책을 읽고 QoS 호환성과 신뢰성을 구분한다.
- /clock와 RGB의 시간 관계를 따로 추적한다. `gz topic` 2샘플은 일시점 샘플일 뿐이며 `ros_gz_bridge` 송신량 전체가 아니다.
- wall time과 sim time을 섞지 않는다. 첫 장면 shader 컴파일과 RPC 지연은 물리 시뮬레이션 시간과 다르다.
- `ST-02/UN-01` 실패 구분: post-spawn 카메라 이상은 실제 접시 이후이고, 이번 ST-02 warmup 문제는 접시 이전이다.
- RED→GREEN→REFACTOR→REVIEW→COMMIT: 원본 FAIL 보존, 최소 QoS+step 변경, 단위·실 CI, 변경 보호 검토, 독립 브랜치 Commit 및 Draft PR 업데이트.

## 6. 미검증 및 위험

- WSLg renderer는 NVIDIA D3D12 가속이다. 이전 소프트웨어 renderer 추정은 이번 원본과 일치하지 않는다.
- RELIABLE + 100ms batch warmup은 **증거 기반 완화 조치**이지, 사용자의 WSL2 GPU에서 오류를 완전히 해결했다는 선언이 아니다. 100ms 멀티스텝 요청이 WSLg에서 timeout을 일으킬 수 있으므로 실제 현장 qualify 로그로 최종 수용한다.
- 구 실패, 사용자 업로드 원본 및 L3 FAIL은 삭제하지 않는다.
- 새 commit의 실제 CI 결과는 GitHub 완료 후에만 PASS라고 기록한다.
