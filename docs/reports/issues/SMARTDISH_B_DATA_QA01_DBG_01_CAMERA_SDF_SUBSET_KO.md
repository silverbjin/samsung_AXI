# SmartDish B-DATA-QA-01 DBG-01 — B15 부분 증거의 카메라 SDF 누락 오판 수정

- 날짜: 2026-11-25
- 원본 WSL2 코드 SHA: `ff1e2e2c32f8d3f53df3352b1bc0601a003d0b81`
- Owner 첨부 진단 TAR SHA256: `483c859767566d1d46bd7da07014dd1dfcda7f0804b9b833c33136cc81bc0dbe`; 외부 SHA 일치, 내부 12/12 PASS, `exit_code=0`, `run_status=AUDIT_COMPLETED`.
- 원본 A13 전체 TAR SHA256: `bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e`; B-Q01 내부 SHA 88/88 PASS.
- 원인 분류: **B 검수기 입력 범위 문제, A 센서 캡처 기능 결함 아님**.

## RED — 실제 사용자 원본 재현

원래 B12R 검토 workspace는 보안상 원본 A13 SDF를 모두 보관하지 않는 진단 부분집합입니다. 이전 `camera_sdf(raw,trial)`은 `raw/trial_000N/sensor_preflight.sdf`만 검사하므로 4개 장면 전부 `camera_pose_source=MISSING`, `B_Q02_CAMERA_POSE_MISSING`을 보고했습니다. 단 `capture_metadata.json`의 `frame_id=smartdish_tray_optical` 및 640×480 RGB·time stamp는 확인했습니다. 이는 카메라 포즈가 실제 Gazebo에 없다는 증거가 아닙니다.

실제 동일 A13 전체 TAR의 `trial_0001..0004/sensor_preflight.sdf`에는 모두 `sensor[@name=smartdish_tray_rgb]/pose = 0 0 1.50 0 1.57079632679 0`, `topic=/smartdish/tray/image_raw`, `gz_frame_id=smartdish_tray_optical`, `width=640`, `height=480`이 포함됩니다.

## GREEN — 최소 수정

- 기존 `verified_archive()`의 전체 TAR·88개 SHA 검증을 **선행**한 경우에만 원본 TAR 내 각 `sensor_preflight.sdf`의 바이트를 불러오고 해당 파일의 SHA를 또 대조합니다. 원본 TAR 전체 압축 해제·파일 변조 금지.
- B15 부분집합의 SDF 부재를 원본 A 캡처 기능 부재로 오판하지 않습니다. 원본 TAR가 없을 때는 기존 보수적인 `MISSING`/HOLD 정책 유지.
- `camera_metadata.csv`에 원본 SDF source·pose·640×480·topic·frame 및 `STATIC_SENSOR_SDF_LOCAL_POSE_NOT_OBSERVED_DYNAMIC_TF` 표기. **정적 SDF 설정 포즈가 동적 카메라 TF의 실측을 대체하지 않음**.
- 사람 가림/화각 판정은 여전히 하지 않았으므로 B-Q02 **HOLD**의 `B_Q02_OCCLUSION_VISUAL_QA_NOT_SIGNED` 유지. B-Q03~B-Q07 HOLD, B-Q04 승인 0, C 학습 NOT_RUN.
- 테스트: (1) 원본 SDF가 비어 있는 B12R 합성 subset + SHA 인증된 합성 원본 TAR 대체 검사, (2) SDF 멤버 해시 오염 차단 및 파일 미출고. 실제 4개 장면 full TAR를 이용한 로컬 재검으로 B-Q02 `CAMERA_POSE_MISSING` 오류 제거 확인.

## 책임 범위와 교육 포인트

A에서 `sensor_preflight.sdf`를 재수집하거나 GUI를 다시 시연할 필요가 없습니다. 원본과 진단 부분집합의 파일 계약을 구별하십시오. B의 미존재 표시는 '관측/증거 미수집'일 수도 있고 '부분집합의 미포함'일 수도 있습니다. SHA로 출처 검증한 원본에서만 누락 증거를 복원해야 합니다.

**이 수정은 B-Q02를 PASS로 승격하지 않으며, 데이터 제품 출고 HOLD 판정을 변경하지 않습니다.**

## 연관 기준선 오류 — 권고 60장면을 강제 실패로 취급한 문제

DACON 사용자 문서의 60개 장면은 `MVP 추천 규모(확정 수치 아님)`입니다. 이전 B-Q05 검사기는 후보 60건 미만을 `B_Q05_PILOT_60_SCENES_RECOMMENDATION_NOT_MET`이라는 gate blocker로 기록했습니다. 신규 코드는 이를 `nonbinding_advisories`의 `B_Q05_PILOT_60_SCENES_NONBINDING_RECOMMENDATION_GAP`으로 이동했습니다. B-Q05 자체는 **다양한 geometry/environment × 클래스 교차 증거 부족**으로 HOLD를 유지합니다. 테스트는 권고수량 미달 자체가 합격을 강제 차단하지 않는다는 점을 고정합니다.
