# B-02 — 트레이 이미지 접수·표준화 코드

- 기준: `main@2dd7f968dd3d24e2afb48e0917ef8c9d054ac894` (B-01 이후)
- 상태: **PASS(로컬 함수 및 fixture 테스트)** / Gazebo 카메라 수집 **NOT_RUN**
- 작업 커밋: 본 문서와 같은 Git 커밋. Actions Run: **NOT_RUN**.

## 설계·재사용 근거

사용자는 파일 경로, 근거 링크, 물리 라벨을 명시적으로 입력합니다. 기존 전방 RGB를 트레이 촬영본이라고 간주하거나 ROS 토픽을 강제 연결하지 않습니다. Pillow 변환만 사용하고 새 ROS 노드/웹서비스/DB는 만들지 않아 A·D 통합 작업과 충돌하지 않습니다.

## 소스와 명령

- `ai/scripts/collect_tableware.py`: Pillow로 EXIF 방향 처리 → RGB → 224×224 fit → PNG, sha256, CSV append, 해시 중복 방지.
- `ai/docs/B_DATA_USAGE_KO.md`: 실습/데이터 수집 명령과 오류 메시지 해설.

```bash
python3 -m pytest -q tests/test_b_dataset.py
```

- 실제 로컬 관찰: 인수 증거 없는 요청은 `B_OBSERVATION_METADATA_REQUIRED`, 동일 변환이미지는 `B_DUPLICATE_IMAGE` 차단. 스모크 10개 테스트 중 관련 테스트 PASS.
- 실제 트레이 센서나 정답 라벨은 아직 없습니다. `--physics-evidence`의 문자열 입력은 **증거 존재를 자동 검증하지 않음**.

## 학습 포인트

해시는 왜 중복 검출에는 유용하지만 물리적인 안정성 검증은 할 수 없을까요? 다음 단위 B-03에서는 배치/장면 단위 데이터 누수를 검사합니다.
