# SmartDish C Dataset v1 — WSL2 Owner 독립 P0 증거 실물 검수 (2026-11-26)

## 수령한 원본과 무결성

- 원본: `20261126T084104Z_ea54959b66b1.tar.gz`, SHA256 sidecar 별도.
- 이번 제출 TAR의 직접 재계산 SHA256: `0aa3f44225df91a0bba606c842a9760131b5150070057fe48cefdb42ad758dda`. Sidecar 첫 필드와 **정확히 일치**.
- TAR 실제 일반 파일 7개: `checkout.log`, `environment.log`, `execution_status.json`, `p0_report.json`, `preflight_stderr.log`(정상 빈 파일), `preflight_stdout.log`, `summary.json`. 멤버는 정규 파일이며 데이터/weights는 첨부하지 않음.
- P0 report JSON 직접 SHA256: `56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0`; 실행 status SHA256 `e84b28e93cc4e9807513860063c4f7393119fb8dbdf82daa26f7bef82268b675`. 원본 값과 sidecar 보존.
- P0 실행 pin/checkout: `ea54959b66b1744fa7bc9f9500ae95cf11cedf57`, `C_V1_CHECKOUT_CLEAN=1`, Git 2.43.0, Python 3.12.3, Pillow present. UTC 시작 08:41:04, 종료 08:41:06.556718, `exit_code=0`. 기록된 `B_AUDIT_REEXECUTED=false`, `training_executed=false`.

## 검사기 실제 동작 재검토

동일 pin의 `ai/train/dataset_v1_gate.py::verify_release_root`는 `dataset_release.json`/manifest/split의 **고정 SHA**와 42개 registry의 파일 경로·파일 SHA256을 검사하고, 기존 C `read_verified_split`를 통해 이미지 PNG RGB224·물리 증거 SHA/size·label·class·stack split 계약을 검증한 뒤에만 `files_independently_hashed=42`를 기록하도록 되어 있음. `scripts/smartdish_c_dataset_v1_owner_once.sh`는 detached checkout/clean → read-only gate → TAR/sidecar를 생성하며 training을 실행하지 않음.

해당 **42개 private 파일 바이트는 제출 TAR에 들어 있지 않으므로 이 작업 환경이 다시 42/42를 직접 해시한 것은 아님**. 재현 가능한 immutable C 원샷과 그 결과를 증거로 수락하며, 사용자 WSL2 실행과 제출 아카이브의 출처는 구별해 표현.

## P0 결과

| 항목 | 제출 WSL2 관측 |
|---|---|
| `verdict` 및 `P0_verdict` | `CONTRACT_READY_HUMAN_REVIEW_REQUIRED` |
| 출고 registry 파일 검사 | **42/42** (`files_independently_hashed=42`) |
| Dataset v1 | `c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606` |
| 승인 / 제외 / Family | **18 / 2 / 5** |
| Label | STABLE 13 / UNSTABLE 5 |
| Train | STABLE8 / UNSTABLE3, 11, Family F3/F4 |
| Validation | STABLE2 / UNSTABLE1, 3, Family F1 |
| Test | STABLE3 / UNSTABLE1, 4, Family F2/F5 |
| 고정 split | `preapproved_split_unchanged=true` |
| Test 모델 선택 사용 | **false** |
| Data freeze / A19 | 유지 / **NOT_AUTHORIZED** |
| Production Contact / AI OFF | **HOLD / PROTECTED** |
| ML 학습 승인 | `training_permitted=false` / 실제 training **NOT_RUN** |

## 판정과 다음 경계

- **P0 기술적/파일 무결성 검사 통과**: 종전 `C_P0_HOLD_PRIVATE_42_RECHECK`는 이번 Owner 제출로 해소. 상태 **`C_P0_CONTRACT_PASS_HUMAN_REVIEW_REQUIRED`**.
- **P1 학습 적합성/사용권 검토는 별도**: 승인된 라벨과 Family 근접성 위험, 단일 RGB/고정 +Y 토크 연구 한계, torchvision ImageNet V1 weights의 정확한 버전·전체 SHA/사용권, 실환경 CPU/Torch를 검토하고 C 연구 학습 GO를 명시적으로 봉인해야 함.
- `training_permitted=false`이므로 **P2 실제 ResNet18 학습, P3 독립 Test 개봉, P4 model release는 계속 NOT_RUN/HOLD**. 이 문서나 owner `exit0`만으로 학습 승인 레코드 작성 금지.
- **AI OFF 유지 / 제품 AI ON HOLD / A19 금지 / 추가 데이터 생산·재분할·라벨 변경 금지**. PM CR 없이는 물리 재생산 없음.

교육 포인트: 42/42가 의미하는 것은 **원본 파일/스키마 무결성의 통과**이지 모델의 일반화 성능, 사람의 C 독립 평가 승인, 제품 안전 인증의 통과가 아닙니다. 첫 오류를 남길 수 있는 P1 전용 read-only 점검만 다음 단계로 권장합니다.
