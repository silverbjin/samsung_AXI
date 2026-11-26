# A14 — 실 Gazebo 증거와 합성 Fixture 구분 실습

## 어떤 자료를 신뢰할 수 있나요?

`pytest`의 synthetic Pose는 수식 오류를 검출하는 데 유용하지만 **실제 접촉이나 Gazebo 동역학 수신 성공을 입증하지 않습니다.**

| 증거 | 합성 Fixture | 실제 Gazebo |
|---|---|---|
| T_world_tray/relative 수식 | 90° yaw 역변환 수치 검사 | 정적 SDF와 실제 TF header |
| Velocity | x=0.2m/0.2s → 1m/s | 실제 Pose 차분과 시간 간격 |
| Contact | fake collision1/2 생성 | 실제 Contact Sensor ROS callback |
| Label | review-only 후보 | 실제 관측도 사람 승인 전 REVIEW_REQUIRED |
| Clock | 임의 ns | /clock 및 TransformStamped header ns |
| GT 인수 | 불가 | 사람 검토 전 여전히 불가 |

## 실습 질문

1. 한 Gazebo topic에서 콜백이 0건이었다면 Contact0이라고 말할 수 있습니까?
2. 로봇 트레이가 1m 움직이고 식기 위치도 1m 이동했다면 WORLD 누적 거리로 UNSTABLE을 판정할 수 있습니까?
3. GZ Raw 2프레임과 ROS Image 1프레임은 같은 시간 구간을 의미합니까?
4. 0.015m 비교 후보 임계치를 제품 설정으로 바로 넣으면 어떤 데이터 누출/판정 위험이 있습니까?
5. 모듈 테스트가 25/25 PASS여도 실제 Contact L2가 실패할 수 있는 이유는 무엇입니까?

## 실습 프롬프트

> 제공한 A14 L0 합성 결과와 L2 실제 Gazebo 원본을 분리하고, 같은 열에 PASS를 합치지 마십시오. L0 수학 수식과 L2 센서 수신의 증거 차이를 명시하고, 승인되지 않은 STABLE/UNSTABLE 후보는 별도 REVIEW_REQUIRED로 처리하십시오.

## 완료 지표

각 증거가 `actual sensor callback` / `SDF source` / `DERIVED` / `fixture` 중 어느 출처인지 설명할 수 있으면 성공입니다. 실제 소스 확인 전 L2 PASS 표현은 금지입니다.