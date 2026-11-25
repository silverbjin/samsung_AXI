# A14-P0 — WSL2 GUI 기본, SHA 고정, 진단 자동보관 원샷

## 1. 전제

WSL2 Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic. NVIDIA D3D12 환경 변수와 기존 GUI 설정을 보존하고, A13 코드/기존 학습 데이터 변경을 금지합니다. **A14 독립 브랜치**에서 실행하며 최신 main/브랜치 SHA와 임의로 혼용하지 마십시오.

- A14 기능 프로파일: STATIC_GRAVITY, 독립 ST-02 안정/UN-01 낙하 두 장면.
- 기본 GUI, 시각 검수는 사용자가 직접 수행하고 자동 인수 게이트에서 제외합니다.
- Owner L3는 기존 A13 Owner 4/4 PASS를 재생하는 작업이 아닙니다.

## 2. 복사·붙여넣기 명령

현재 CI가 성공한 **정확한 40자리 SHA를** `PIN`에 넣습니다.

```bash
PIN=<A14_VERIFIED_40_HEX_SHA>
curl -fsSLo "$HOME/smartdish_a14_bootstrap.sh" \
  "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/smartdish_a14_bootstrap.sh" \
  && SMARTDISH_A14_SOURCE_SHA="$PIN" \
  bash "$HOME/smartdish_a14_bootstrap.sh" --gui
```

진단 전용 Headless 사용 시 `--headless`를 명시합니다. GUl 기본을 저절로 소프트웨어 렌더링으로 바꾸지 않습니다.

## 3. 자동 검증과 증거

실행기는 Git SHA/브랜치/WSL2/Ext4/Jazzy/Contacts 인터페이스를 확인하고, GUI 모드면 실제 Gazebo Qt/OpenGL preflight를 먼저 수행합니다. 이어 ST-02/UN-01 **각 1회** 실제 RGB·Pose·Contact 물리 수집, A14 후보 검수, 2개 독립 TAR 생성, 마지막에 표준 진단 TAR+외부 SHA sidecar를 생성합니다.

`generated/smartdish_a14/run_*/smartdish_a14_diagnostics.tar.gz`
`generated/smartdish_a14/run_*/smartdish_a14_diagnostics.tar.gz.sha256`

`A14_STATIC_GRAVITY_P0_EVIDENCE_HOLD` 발생 시 contact_status, camera metadata, TF header, gap, 적재 붕괴 이전 t0 결측 중 최초 원인을 확인하십시오. 파일이 생겼다는 사실만으로 PASS가 아닙니다. 사용자 명령 중 별도의 `exit 1`, `pkill`, `reset --hard`는 넣지 않습니다.

## 4. 예상 메시지

- `A14_SOURCE_SHA_PASS` → 코드 일치.
- `A14_TRAY_RELATIVE_POSE_PASS` → 역변환 검증.
- `A14_VELOCITY_PROVENANCE_PASS` → 실제 Pose 차분·단위.
- `A14_CONTACT_EVIDENCE_PASS` → 센서 근거. 안 나오면 무효.
- `A14_TIME_ALIGNMENT_PASS` → 실 sim timestamp 간격과 RGB 정렬.
- `A14_GT_CANDIDATE_REVIEW_REQUIRED` → 사람이 승인해야 한다는 뜻이지 GT 승인 아님.

## 5. 교육 질문

왜 앞선 A13 4/4을 다시 하지 않습니까? **새로 개발한 계측 계약만 2장면에서 테스트하고 변경되지 않은 기존 제품 PASS는 재활용**하기 때문입니다.