# B-QA03 DBG-02 — FOV 스키마 연결 오류 및 입력 상태 분리

## RED (실제 Owner 원본)

기준 B `1c38c215e90eedebb2f3282c449dfed1d074e3c3`, 원본 SHA 고정. 두 Python 파일을 connector로 확보하여 Git blob SHA 검증 후 Linux CPU CLI 직접 실행. 전체 clone은 DNS 제한. 실제 첫 오류 `B_A15_CAMERA_FOV_RECALC_MISMATCH`, exit2, 진단 TAR SHA `78a9c50ec00d04b5d0498515048613b5f247381ea46e099d247eba5698f0ffe7`, 내부 2/2. 첫 장면의 계산한 bbox는 기록 bbox와 동일했으나 design에는 `dishes` 키가 없었다. 기존 함수는 design의 `initial_dishes`로 반경/두께를 읽고 같은 dict의 `dishes`에서 기록 bbox를 찾았다. 실제 `initial_validity.json.dishes`에 기록되어 있으므로 빈 배열 → mismatch 오탐. 또한 CLI는 검수 실패 보고서의 source_class를 원본 부재로 남겼다.

## GREEN / REFACTOR

- `visibility_geometry(pose_bytes, design, validity, info, t0)`: geometry는 design, 기록 bbox는 validity. 호출부에서 두 객체를 전달한다. 투영식, FOV 범위, 1e-4 px 허용 오차 및 fail-closed 그대로.
- CLI 오류 시 실제 파일 존재/검수 실패는 `OWNER_INPUT_PRESENT_VALIDATION_FAILED`, `B_QA03_OWNER_RAW_VALIDATION_FAILED`. 파일 부재는 기존 상태 유지. 모두 exit2/all HOLD/승인0.
- 동일 원본을 수정된 코드로 재검: exit0 `B_A15_OWNER_RAW_AUDIT_VERIFIED_REVIEW_ONLY`, release HOLD. outer15/inner64, 4 scene, Pose/Contact/torque/layout/pixel/aHash 직접 재검. GREEN 진단 SHA `c0f35a4c4950097e954036d00feca526c51e908a636f59aba23c2ca6d215fee4`, 내부 3/3, worksheet 4행 결정 공란. 진단 TAR 자체는 private.
- 새 독립 합성 테스트 2건(분리 스키마 양성+0.01px 변조 음성, 실제 입력 실패 vs 부재 상태) 원본 코드에서 실패/오류, 수정 코드에서 2/2 PASS. 기존 FOV 음성 fixture 호출을 새 시그니처로 맞췄다. 실제 원본 검수 결과와 합성 회귀를 구분. 새 전체 CI 결과는 별도 확인.

## REVIEW / 교육 요점

한 데이터 파일에 모든 정보가 있다고 가정하지 말고 생산자 스키마별 책임을 분리한다. 오류 허용치를 완화하거나 원본을 수정해 PASS시키지 않았다. 이전 Owner/CI 성공 증거 보존, 새 Gazebo 없음, A/C/D/S7/main 수정 없음, A15 GT UNKNOWN_HOLD/Contact HOLD/cleanup -11 FAIL/사람 승인 0/실학습 0 유지. 기존 진단 자동 출력과 승인 원장 차단 보존. 실제 물리/이미지 원본 또는 private QA 산출물은 Git에 게시하지 않는다. [새 인수 원장](../acceptance/SMARTDISH_B_A15_QA03_ACCEPTANCE_KO.md).
