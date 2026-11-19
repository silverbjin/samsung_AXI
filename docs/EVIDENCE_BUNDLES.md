# SAMSUNGAXI — Gazebo 실행 로그 경량 ZIP 사용 가이드

**현장 관찰:** 2026-11-19 사용자가 제공한 Gazebo GUI에 World/로봇이 정상 표시되고 RTF 99.89%가 보였습니다. 이전 화면 61.95%보다 개선됐지만 지속 평균 RTF, Scan/Depth, 배달 주행의 인수 증거는 아닙니다.

## 기존에 종료된 Gazebo S1 실행 로그 압축

```bash
cd ~/samsung_AXI
mkdir -p logs/evidence
LAST="$(ls -t logs/world_*.log | head -1)"
python3 /path/to/samsungaxi_evidence_bundle.py --root "$PWD" \
  --session-log "$LAST" --since-unix 0 \
  --output "$PWD/logs/evidence/samsungaxi_existing_$(date -u +%Y%m%dT%H%M%SZ).zip"
```

## 다음 Gazebo부터 종료 시 자동 ZIP (권장)

기존 성공한 `samsungaxi_d3d12_world_once.sh`와 `restaurant_demo.sh`를 **수정하지 않습니다**. 추가 래퍼 `samsungaxi_d3d12_evidence_once.sh`만 실행해 종료/오류 시 이번 세션 ZIP을 생성합니다. 루트 기본값: `~/samsung_AXI`.

```bash
SAMSUNG_AXI_CORE_SCRIPT=/path/to/samsungaxi_d3d12_world_once.sh \
SAMSUNG_AXI_BUNDLER_SCRIPT=/path/to/samsungaxi_evidence_bundle.py \
  bash /path/to/samsungaxi_d3d12_evidence_once.sh world
```

GitHub에서 래퍼만 다운로드하는 경우 `SAMSUNG_AXI_EVIDENCE_REF=<검수한40자SHA>`를 지정하면 보조 파일 두 개를 **같은 커밋 SHA에서만** 다운로드합니다. 작업공간의 이전 성공 코드는 덮어쓰지 않습니다.

### Gazebo RTF 실측 (선택, World 실행 중 별도 터미널)

```bash
bash /path/to/samsungaxi_snapshot_rtf.sh
```

`/world/restaurant/stats`에서 최대 7초의 `real_time_factor`를 추출하여 `logs/evidence/gazebo_stats_*.txt`를 저장합니다. 이후 종료 시 같은 세션 ZIP에 포함합니다. 수신하지 못한 값을 임의로 생성하지 않습니다.

### ZIP 구성/제한

- `manifest.json`: 원본 크기, 추출 크기/누락, SHA256
- `logs/session.log` · `logs/world.log`: head·최초 오류/경고·tail
- `ros/*.log`: 해당 실행이 출력한 ROS launch 로그 경로 내부의 최대 8개
- `metrics/gazebo_rtf_observation.txt`: 별도 측정했을 때만 포함
- `README.txt`: ZIP 자체가 인수 PASS는 아님

파일당 추출 내용 최대 300KB, 전체 원본 로그/rosbag/영상 제외. 알려진 토큰·자격증명 패턴 행 마스킹 및 타 프로젝트 로그 제외. **외부 제출 전 ZIP 내부 정보 직접 확인**. 원본 로그·PC 설정·기존 S1 코드는 변경하지 않습니다.

교육용 경과: [EVD-01](reports/tasks/2026-11-19_EVD-01_compact_evidence_bundle.md).
