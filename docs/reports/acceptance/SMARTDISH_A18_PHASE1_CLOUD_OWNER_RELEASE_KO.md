# SmartDish A18 — 1차 실제 클라우드 검수 및 WSL2 인수 출고 (2026-11-26)

## 1. 기준 및 설계 정합성
A17-08 부모 4969446c83cd3f8fa4338265975a34f5b88dab69, 보호 Platform b8ef3998973a5e33b67ddd5c5b63c3c89b837840, main 63e147289e307e0b9900ca365e9c4557c5921804. B-QA05 실제 진단 TAR 240bfe72317303566a43b0a3e97bd4c042d95ce75e36ce87e0d940808e391371 및 22/22 manifest 직접 검수, 내부 report 80953ce1bbcca9e1205c8a3fe32c8a4c15a6389f04cec3d4c0a847397fa7808c, 실제 12행 inventory/15개 공백, REVIEW_ONLY, GT0/WSL2 별도 인수 NOT_RUN. 기존 A15/A16 원본은 재실험하지 않았다.

선행 구현 ae5f6145503635571a18b01039ff42d57bf0e27c CI #45762976928 실제 4/4 성공. 이후 별도 설계 정합성 커밋 fd44ac7e9cca56c774bec810c438382219a786b1이 브랜치에 추가된 것을 실제 확인했다. 기존 기록을 덮어쓰지 않고, 첨부 SMARTDISH_A18_PHYSICAL_LAYOUT_DEVELOPMENT_SPEC_KO.md 및 SMARTDISH_A18_PROPOSED_LAYOUT_REGISTRY.json과 대조했다. 최신 설계는 2~3개 원통 식기, L18-03→04→01→02 순서, L18-07 F5 125×30/95×45mm, L18-08 F6 150×40/115×35/70×35mm이다. 최초 4개 물리 배치는 선행과 동일하나 장면 ID/정규화 물리 signature 및 metadata가 달라졌고, 자동 CI로 최신 SHA 실제 검증이 이루어졌다. 2회 Cloud 실행은 동일 4개 독립 layout이지 신규 8개가 아니다. 이전 4단 지원/다른 F5/F6 설계는 최종 범위에서 제외한다. docs/plans/SMARTDISH_A18_DEVELOPMENT_SPEC_KO.md의 선행 설계는 최신 registry와 이 보고서가 대체한다. 명목 목표 기존 12+신규 8=20/6 family, 현재 신규 Cloud 4개, Owner 신규 0개. 이전 실행의 원본과 진단은 보존한다.

## 2. 최신 실제 CI 및 독립 원본 검수
실행 pin fd44ac7e9cca56c774bec810c438382219a786b1, #45763439864 SUCCESS. 신규 11 + A17 15 + A16 10 + A15 8 + Platform 7 = 51개, 실제 pin 및 보호 경로 검수 PASS. Platform push #45763439865 / PR #45763444881 SUCCESS. 광범위 Restaurant #45763444865는 마지막 조회 당시 진행 중(성공 미확인), 선행 #45762984321 CANCELLED. 제품 통합 게이트로 사용하지 않는다.
Artifact #15090787547 ZIP SHA256 726d7f8ec1d053402fcd64bc5d0be75a73db41d95086247a33de4d382a1a95c6, 실제 다운로드/CRC/sidecar 및 안전한 일반 파일·manifest 집합 확인. 원본 TAR 525549fd7d5e12a0c8c28e397aab555d7ed0a423fc420d20487c8bd74d3674aa, 진단 TAR 71dd06b5f2b0c4a2afd82ac8585701c0f22fb7ab9b6098032a1c284a8a6e9840. 외부 9개/내부 60개/진단 26개, 총 95/95 해시 검수. 독립 JSON 검수 SHA 21a49b8922f93cf453997ac298b1bea49bf28b4f4f6e18b93224a0a1cfafb37b. 실제 t0 2.0s RGB+CameraInfo exact, 4개 pixel hash 고유, approved registry signature/layout/family 일치, 1ms 10,301 sample/entity 구간, 초기 지지 exact ECM 쌍, target registry, 500개 고정 토크 명령/장면 및 상대 변위/누적거리 독립 재계산. 실제 raw pose 213194, ECM 213194, trigger 2000. 실제 17개 owned process rc0, SIGINT only, group gone. L18-03 GUI PASS, 나머지 Cloud headless. Cloud는 inherit, WSL2 GPU profile 미검증.

| 장면 | Family | signed X mm | 상단 최대 상대 변위 m | 누적 경로 m | 관측 | 데이터/종료 |
|---|---|---:|---:|---:|---|---|
| L18-03 | F3 | -97 | 0 | 0 | 위치 유지 | PASS/PASS |
| L18-04 | F4 | +87 | 1.0004537607729 | 1.166514545765118 | 큰 변위 | PASS/PASS |
| L18-01 | F1 | -92 | 0 | 0 | 위치 유지 | PASS/PASS |
| L18-02 | F2 | -112 | 0 | 0 | 위치 유지 | PASS/PASS |

개별 원본 SHA: 01 07e297d90ec46a8e3e1f6343c4b01663b078c6f5558f8e5aaca6bb0fed798dc4; 02 9bb6e586fb7dcc2f957d435a8b8ea1079c0eda1467c6332f76bd3477c0d4da63; 03 e8bc7f90a930fa63017ef6bc9c44fe9d9001d4c4ca944561a455af30a4844b5a; 04 99176691c5c897f82618ab2840f0e1ad4ab6492f4f35f5dab1921d68c367a028. 선행 CI #45762976928 ZIP 477c8a4424c3677d1fd7e4a3ed06418aad53ac7ed4d6a03d5ae341c3e2a3fc33, raw a47d7dc6f5bc7e0259462f2330d359deaf95bdc0ca6d0e1e1704ab158cad3dfe, diag 3e2ce642a625a8ce331b280ce78c984e7b63de383f550b835b4c5f100388e475, 동일 물리 집합의 다른 식별자/실행 기록으로 보존(독립 신규 수 증가 없음).

## 3. 물리 해석 및 경계
기존 + 신규 Cloud 조건에서 명목 교차 cell 9→12/24, 미확보 15→12 설계 및 유효 초기 계약 기준; 최종 B 실제 Owner 재검수 전 데이터 품질 승인 아님. 신규 3 유지/1 큰 변위, 기존 관측 8/4와 합치면 참고용 11/5이나 Owner/Cloud 환경 차이 존재. 고정 +Y 토크에서 큰 양의 offset과 큰 변위 관계가 여전히 관측됨. 방향성 편향 해소 또는 일반화 성능 입증 아님. 결과를 맞추기 위해 scene 수정·선별·재시도하지 않는다. Contact 진단 t0 이후 ECM positive 142653/empty32447, native ECM exact intersection142653, native/ROS intersection101078, native-only41575, ROS-only0. publisher sequence가 아니므로 전달율/손실률 주장 금지, production Contact HOLD. GT UNKNOWN_HOLD, human false, training false. A15/A16 과거 종료 FAIL 그대로, A17-08 실제 생산 종료 인수 아직 NOT_RUN.

## 4. WSL2 1차 인수
실제 검증된 pin만 사용. ROS Jazzy/Harmonic8.15.0, 기존 GPU/Mesa/WSL 라이브러리 allowlist drift HOLD. GUI 기본, 시각 확인은 사용자, 데이터/GUI/cleanup/GT/Contact 별도. 첫 L18-03에서 A17-08 실제 생산 GPU 프로파일 및 실제 종료 게이트를 처음 확인한다. 4개 신규 장면만, 이전 데이터/GDB 재실험 없음. 2차는 이 실행기에서 차단한다. 실패 시 부분 증거 제출, 무조건 재실행 금지.
```bash
(
set -Eeuo pipefail
PIN=fd44ac7e9cca56c774bec810c438382219a786b1
curl -fsSLo "$HOME/a18_pilot_bootstrap.sh" "https://raw.githubusercontent.com/silverbjin/samsung_AXI/$PIN/scripts/a18_pilot_bootstrap.sh"
SMARTDISH_A18_SOURCE_SHA="$PIN" bash "$HOME/a18_pilot_bootstrap.sh" --phase 1 --gui
)
```
제출: generated_a18/a18_pilot_evidence.tar.gz, .sha256 및 a18_pilot_diagnostics.tar.gz, .sha256. 초기 checkout 실패는 bootstrap diagnostic+sidecar. 실제 Owner 정상 종료 및 새 장면 승인 전 P5/생산 GT/Contact 승격 금지. 1차 인수 후 신규 05~08만 조건부 확대, 현재 2차는 설계/fixture만 완료. B 후속 adapter와 QA/GT/권리/그룹 분할, C 실제 학습, E 통합은 별도. main/Platform/E 및 다른 담당 브랜치 변경 없음. PR56 Draft 유지.
