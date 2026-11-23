# S6-VISION-01 — 실제 Gazebo RGB 기반 지도학습 식기 판별기 / 교육용 중간 보고서

- 날짜: 2026-11-23
- 브랜치: `feature/s6-vision-flow-20261123` (S6-00/CAMERA-01 이후)
- 실증 상태: 코드 및 L0 계약 작성. **실제 카메라 이미지·독립 모델 검수는 아직 미확인**.

## 1. 실무 과제·입력 데이터
식기가 비어 있는 테이블과 접시 3장이 실제 카메라에 보이는 이미지를 각각 PPM 원본으로 취득해야 합니다. 학습 단계에서 `empty.ppm`과 `stacked.ppm`은 반드시 실제 Gazebo RGB 프레임이어야 하며, 클래스 레이블은 별도의 실제 SDF 장면에 근거합니다.

## 2. 데이터 처리 및 학습 아키텍처
PPM(RGB8) → 6×6 이미지 그리드별 RGB/푸른색/밝은색의 5개 특징 평균(총 180차원) → NOT_STACKED / STACKED 두 원형(prototype) 학습 → 거리가 작은 클래스로 분류. 모델 JSON에는 두 이미지 SHA256과 학습 거리, UNKNOWN 임계값을 보관합니다.

## 3. 왜 이러한 MVP 모델인가?
- 대규모 YOLO 학습보다 파이프라인의 데이터 수집·레이블·특징 추출·모델 추론·증거 계약을 단시간에 학습할 수 있습니다.
- 엄밀하게는 1회 실물 장면/클래스 기반의 작은 지도학습 모델이지, 일반화된 식기 객체 탐지 모델이 아닙니다.
- 거리·신뢰도 불충분, 시점·크기 변경에서는 UNKNOWN으로 복귀를 허가하지 않습니다.
- 새로운 클래스·독립 환경·조명·가림·사진에 대한 정확도는 **아직 NOT_VERIFIED**입니다. 같은 두 장으로 학습/시험 후 100%라고 말하는 것은 데이터 누수입니다.

## 4. 실습 명령과 코드 연결
- `python3 scripts/s6_vision_ai.py train --empty empty.ppm --stacked stacked.ppm --out model.json`
- `python3 scripts/s6_vision_ai.py predict --model model.json --ppm stacked.ppm`
- `scripts/s6_vision_ai.py`의 `accept_return()`은 AI 출력과 실제 Nav2 도착/로봇 정지/새 이미지 4가지 조건을 동시에 평가합니다. Vision은 `/cmd_vel`을 직접 발행하지 않습니다.
- 훈련생 과제: 새로운 카메라 시점·빛·한 장 식기·부분 가림의 **독립** 이미지를 수집하고 클래스별 confusion matrix와 UNKNOWN 비율을 보고하십시오.

## 5. 검수 정책
알고리즘과 합성 픽셀 L0 테스트의 성공은 ML 코드 계약에 한정합니다. 실제 Gazebo 이미지에서 판정 성공해야 L2 AI 연동의 후보이며, 독립 데이터 평가 전 일반화 모델 PASS를 주장하지 않습니다. 실물 AI 판정 실패는 `UNKNOWN` 또는 `NOT_STACKED`로 종료하며 복귀 Goal은 보내지 않습니다.

## 6. 첫 실패 경계
`S6_UNSUPPORTED_PPM_HEADER`, `S6_INVALID_TRAINING_RGB_SHAPE`, `S6_TRAIN_CLASSES_NOT_VISUALLY_SEPARABLE`, `S6_UNVERIFIED_MODEL_SCHEMA`, `LOW_SIMILARITY_OR_AMBIGUOUS`를 구분합니다.

## 7. 단계 판정
코드 구현: 완료 / L0: NOT_RUN / 실제 Gazebo 모델 학습·추론: NOT_RUN / 독립 새 장면 평가: NOT_RUN / WSL2 L3: NOT_RUN / RTF 90%: HOLD.
