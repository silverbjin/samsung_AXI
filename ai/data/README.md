# B 데이터 실제 범위

- `manifest.csv` / `split_manifest.csv`는 **헤더만 제공**합니다. 실제 물리 안정성 라벨 이미지 수는 **0건**입니다.
- `images/`, `private/`는 추적하지 않습니다. DACON 원본/영상/평가 데이터 및 동의 없는 촬영본을 GitHub에 올리지 마십시오.
- `GROUND_TRUTH=MOCK_ONLY`로 생성한 계약 fixture는 모델 학습/평가에 사용하지 않습니다.
- CSV의 `image_path`는 `--root`로 지정한 프로젝트 루트 상대 경로입니다. 예외: `--make-fixtures` 사용 시 fixture 폴더를 `--root`로 지정합니다.
