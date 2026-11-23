# S6-ACCEPT — 실제 Gazebo Vision 배달·복귀 통합 인수 및 주니어 교육 보고서

- 작성일 2026-11-23 / 브랜치 feature/s6-vision-flow-20261123
- 아직 완료되지 않은 검증은 PASS로 보고하지 않습니다. RTF 90% 목표는 HOLD입니다.

## 1. 요구사항 추적성
| 요구사항 | 테스트 | 입력 | 기대 결과 | 근거 |
|---|---|---|---|---|
| S6-00 식기 실제 관측 | S6-00 L2 | Gazebo 빈/적재 두 장면 | 접시 실제 가시성 및 원본 SHA | Run #45096925265 Artifact #14782884713 |
| S6-CAMERA 요청형 | L0/L2 | lazy Image/CameraInfo, 구독 개시/해제 | 주행 안전 토픽 변화 없음, 이미지 수신 | bridge profile, 이미지 수집 JSON |
| S6-VISION 학습·추론 | L0/L2 | 원본 RGB PPM 2장, 교사 레이블 | 모델 추론 결과와 판정 이미지 해시 | models/s6_dish_prototype.json, s6_vision_AI |
| S6-FLOW 자동복귀 조건 | L0/L2 | 첫 Nav2 SUCCEEDED, Odom 정지, RGB 판정 | STACKED에서만 두 번째 Goal | S6 state test, real_vision_evidence.json |
| S6 안전 주행 | L2 | 실제 LiDAR /scan, 원통 fixture | STOP, 최종 /cmd_vel≤0.025m/s, Odom≤0.045m | 기존 S4 actual check |
| S6 최종 WSL2 | L3 | 강사 WSL2 GPU/GUI 실제 세션 | 같은 장면·AI·복귀·STOP | 현장 ZIP (아직 NOT_RUN) |

## 2. RED→GREEN 디버깅과 첫 실패 경계
첫 번째 카메라 위치에서 실제 RGB 픽셀 변화 3.4%는 주로 그림자였고 접시가 테이블 전면에 가려져 있었습니다. 이를 가시성 PASS로 부풀리지 않았습니다.
S6 옵트인 카메라 높이 0.65m와 TF를 함께 조정하고, 파란 접시 테두리가 이미지 내부 세로 91~108행에 410픽셀 관측되는 근거를 추가했습니다. 기존 S5 로봇 시작점과 LiDAR 안전 설정은 유지합니다.
Vision은 부족한 영상/다른 크기/유사도 부족/모델 누락에서 UNKNOWN 또는 HOLD를 반환하고 자동 복귀하지 않습니다.

## 3. 주니어 개발자 해설 및 실습
1. 월드 좌표로 생성한 SDF 객체가 왜 Nav2 지도 좌표 목표와 다른지 시연합니다.
2. RGB-D 센서 활성화와 ROS2 Image 구독/브리지 연결이 왜 다른 계층인지 설명합니다.
3. 이미지 실제 PPM·SHA256 → 특징 → 학습 모델 JSON → 추론 결과 → 복귀 Goal 사이를 모두 추적합니다.
4. 원본 2장과 같은 장면에서 100%로 분류되는 것은 일반화 정확도 증명이 아니라는 데이터 누수 문제를 토론합니다.
5. 실패 주입: 빈 테이블/이미지 없음/낮은 confidence/Nav2 미도착/로봇 비정지에서 RETURN이 금지되는 이유를 설명합니다.
6. 실제 ROS/Gazebo 통합 검증이 없는 pytest PASS와 실제 두 Goal/CM STOP 증거를 엄격히 구분합니다.

## 4. 인수 정책
- 공개 L0: 안전 계약+ML 상태 테스트 성공.
- 실제 Gazebo L2: 한 세션에서 TABLE_3 Action, 실제 RGB Image, 학습 모델 판정, PICKUP_RETURN Action, LiDAR 물리 STOP 성공 필요.
- 최종 강사 WSL2 L3: 직접 실행 및 원본 ZIP 검수 전에는 NOT_RUN.
- ML 모델은 실제 Gazebo **하나의 시점·두 클래스**에서 학습한 제한적 프로토타입이며 현장/새 접시/조명 일반화는 별도 교육 과제와 HOLD입니다.
- S5 기능 PASS는 보존하며 S6 최종 L3 미완료 시 main 병합은 HOLD합니다.

## 5. 현재 상태
L0=NOT_RUN / L2=NOT_RUN / L3=NOT_RUN. 증거 Run ID와 SHA는 실제 검증 후 보고서에 추가합니다.
