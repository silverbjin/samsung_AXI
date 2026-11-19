# S1PERF-01 — 현장 S1 승인 범위와 성능 진단·S2 진입 준비

- 날짜: 2026-11-19 KST
- 기준: main `8968fd212e9fe50413d3f509abe6b08ef6f104bb`; Owner pinned S1 `f211d043bd3e503015dd2babac6596e08db8ef86`
- 상태: **코드 정적 검증 후 CI 예정; WSL2 개선 효과 NOT_RUN; S2 지도 NOT_RUN**

## 요구와 실제 확인
강사가 WSL2 Gazebo 실행 화면/로그를 제공. World·가구·물리 사람 프록시·Waffle Pi 모델이 화면에 나타났으며 Gazebo에 표시된 RTF는 약 0.6195. `Entity creation successful`과 bridge 생성 메시지 확인. 이는 S1의 **월드 렌더링** 근거이며, 브리지 생성 로그만으로 센서 실제 데이터나 1→3→1 주행 완료를 의미하지 않음.

## 원인 후보와 최소 수정
업스트림 Waffle Pi의 RGB 30Hz `type=camera`와 등록 RGB-D 5Hz `type=rgbd_camera`가 중복 렌더링되는 점을 소스로 확인. GPU LiDAR의 `visualize=true`도 GUI 디버그 표시 용도임. **성능 병목 기여도 자체는 현장 미측정**.

- 원본 ROBOTIS SDF/드라이브·TF·Scan 10Hz 유지; 생성 로봇 SDF에서 불필요 RGB 카메라만 제거, 광선 시각화만 false.
- 단독 카메라 전용 ROS Image Bridge와 관련 CameraInfo 브리지 제거; 등록 RGB-D RGB/Depth/PointCloud2를 유지.
- S2 `mapping.launch.py gui:=false` 인자를 추가하여 이후 실제 CI /map 검증 가능.
- RAM·GPU는 자동 변경하지 않으며 `scripts/wsl2_perf_doctor.sh`가 읽기 전용 보고서 생성.

## 검증 및 추적
정적: Python compileall, Bash -n, SDF XML, pytest. 실제 Gazebo L2에서 `/scan`, `/odom`, RGB/Depth/Points가 모두 수신되어야 GREEN. RTF 개선치 및 WSLg GUI는 강사 실측 후 갱신. 정량 성능 KPI를 합격 게이트에 추가하지 않음.

## 다음 경계
PR의 L0/L1/L2 결과 확인 → 개선된 World 현장 RTF/렌더러 진단 → S2 SLAM Toolbox 실제 `/map` 및 지도 파일 저장 → S3 AMCL+Nav2 1→3→1 주행 준비.

[문제 원인 분리 보고서](../issues/2026-11-19_PERF-01_wsl2_rtf.md) · [실행 가이드](../../WSL2_PERFORMANCE.md)
