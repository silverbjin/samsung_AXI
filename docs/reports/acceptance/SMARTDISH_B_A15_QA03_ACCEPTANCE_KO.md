# B-QA03 — A15 Owner 실제 원본 직접 검수 원장 (2026-11-26)

## 범위와 출처

기존 원본 부재 시점의 원장은 Git 역사 `1c38c215e90eedebb2f3282c449dfed1d074e3c3` 및 기존 OWNER_RAW_NOT_AVAILABLE receipt로 보존한다. 사용자가 제공한 실제 WSL2 Owner TAR/sidecar를 읽기 전용 사본으로 정규화하고 원본 SHA `828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05` 그대로 검수했다. A15 생산 SHA `65f0fa6fbf140f8fd2553ce2d8fdf3f515918695`; platform `b8ef3998973a5e33b67ddd5c5b63c3c89b837840`는 GitHub compare에서 B 기준 SHA의 조상(behind=0) 확인.

실행: ChatGPT Linux x86_64, Python 3.13.5, Pillow 12.3.0, CPU 프로세스. 컨테이너 GitHub DNS 차단으로 전체 Git clone/WSL2 bootstrap 미실행; 기준 SHA의 두 공식 Python 파일을 GitHub connector로 읽어 Git blob SHA 각각 e41355f68f0ae104d5b4ed6e101e979c51c30d86 / 588547572736effa468d5c49fb51a3fe1d5a54c6 일치 확인 후 CLI 직접 실행. RED exit2 B_A15_CAMERA_FOV_RECALC_MISMATCH; 최소 수정 후 GREEN exit0, 실제 4장면 검수 완료. GREEN 실행 blob SHA audit 9bc6ade9bde754f7c03c10c02ad65bedb41eb867 / CLI 7d9186c1e554e26db9451b0e971d85ba7cc16120. 이 실행은 Owner가 생성한 실제 원본의 B 오프라인 검수이며 새 WSL2 runner 실행이 아니다.

| Gate | 직접 판정 | 증거 및 차단 |
|---|---|---|
| B-Q01 | PASS | 고정 Owner SHA/sidecar, 안전 TAR, outer15/15, inner64/64, 생산 SHA, schema 및 layout provenance 검증 |
| B-Q02 | HOLD | 4 RGB 640×480, CameraInfo t0 2.0s skew0, 200ms settle, 2개 exact ECM support pair/장면, 보수 FOV 재계산 PASS; 사람 가림/자연스러운 적재 검토 대기 |
| B-Q03 | HOLD | 4 entity ×10301 ×4 =164816 관측 구간 Pose, ECM 164800, ROS callbacks 72951, 500 torque 명령/장면, 동일 stamp positive subset 재계산 PASS; full delivery/engine registration 미입증 |
| B-Q04 | HOLD | 승인자 0, GT UNKNOWN_HOLD, rule UNKNOWN; 자동 라벨 금지 |
| B-Q05 | HOLD | 2 family/4 layout, 단일 overhead 환경/공통 외란, 중앙/편심 shortcut |
| B-Q06 | HOLD | 파일 및 픽셀 exact duplicate 0, aHash 6쌍 검토 후보(거리 0–2), 승인된 독립 그룹 split 0 |
| B-Q07 | HOLD | 승인 manifest 0, C real training 0, 미래 물리 정보 RGB 입력 금지 |

## 공식 검수기 직접 재계산 (m, rad)

| Scene | Upper cumulative path m | Max displacement m | Net displacement m | Max rotation rad | ROS matched / ECM positive |
|---|---:|---:|---:|---:|---:|
| L15-01 | 0 | 0 | 0 | 0 | 11855/30900 |
| L15-02 | 1.020717309 | 0.819892143 | 0.819387093 | 3.141592649 | 16649/39639 |
| L15-03 | 0 | 0 | 0 | 0 | 11506/30900 |
| L15-04 | 1.032336898 | 0.781104280 | 0.780894151 | 3.141592628 | 15922/39305 |

기존 독립 계산 및 생산 verdict와 일치(공식 metric tolerance 2e-7). ROS exact subset 55932/140744=39.74%는 전체 전달 손실률이 아니다. world-Y 0.12Nm, 500×1ms 명령이지 실측 wrench가 아니다. STATIC_TRAY_COMMON_TORQUE_PILOT는 동적 주행 안전 검증이 아니다.

**분리 판정:** actual_owner_raw_directly_recomputed=true; CLI exit0 REVIEW_ONLY; A15 원본 DATA/GUI 4/4 PASS; server cleanup 4/4 -11 FAIL, all_owned_stopped=true; production contact HOLD; GT UNKNOWN_HOLD; human approved 0; C 실학습 0; E/main merge HOLD. Worksheet 4행 사람 결정/가림/리뷰어/사유/사용권 공란, 승인 ledger 없음. 원본 재수집 없음.

RED/GREEN private 진단 자동 출력 및 SHA 검증 완료(내부 각각 2/2, 3/3). 원본 TAR/PNG/TSV/JSONL 및 private 진단/worksheet/report 원본은 Git에 올리지 않음. 교육 [DBG-02](../issues/SMARTDISH_B_A15_QA03_DBG_02_FOV_SCHEMA_KO.md). 기존 CI #45743090972 (172) / #45743090982 (25+7)는 이전 기준 SHA 증거. 새 코드에 대한 focused 합성 회귀 2건 로컬 PASS, 기존/신규 scoped CI는 새 commit에서 별도 확인한다.

다음: 운영자 RGB 가림/안착·사용권 검토, A16 소규모 신규 독립 구성 요구 확정, 생산 Contact/teardown 별도 A 계약, C 실제 출고 HOLD 유지.
