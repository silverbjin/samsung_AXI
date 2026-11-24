# SmartDish A-11~A-13 — 인수 상태 및 증거 규칙

**기준선** main `cc66b66a16ffc8020498d973ebe31a5c4ca439e0` (AI OFF PR #44 병합). 신규 A tray 브랜치는 Draft로 유지, main 변경 금지.

| 요구 ID | 완료 근거 | 현재 상태 |
|---|---|---|
| G-A11-01 | 실 Gazebo 카메라 `gz.msgs.Image` | NOT_RUN |
| G-A11-02 | ROS Image RGB/encoding/size/stamp/연속 | NOT_RUN |
| G-A11-03 | B 기존 save_unlabelled_frame PNG 실저장 | NOT_RUN |
| G-A12-01 | 4개 독립 동적 SDF 시나리오 물리 실행 | NOT_RUN |
| G-A12-02 | 안정 유지 2건, 낙하 2건 실제 Pose 대비 | NOT_RUN |
| G-A12-03 | 실제 Pose 시계열 독립 JSONL | NOT_RUN |
| G-A13-01 | GUI 기본 데모/수집 runner 실실행 | NOT_RUN |
| G-A13-02 | 시험 별 원본 격리와 덮어쓰기 차단 | L0 정적 검사 이후 갱신 |
| G-A13-03 | SHA256+원본 이미지/물리 근거/metadata/tar.gz | NOT_RUN |
| G-REG-01 | 기존 AI OFF 보호 소스 diff 0 | GitHub compare 확인 예정 |
| G-CI-01 | L0/L1 실제 워크플로 성공 | CI 재검 후 갱신 |
| G-L3-01 | 사용자 WSL2 GUI 실제 4개 시험 | NOT_RUN |
| G-DOC-01 | 계획서/A-11~A-13/디버깅/인계 | GitHub 게시 후 갱신 |
| G-PR-01 | Draft PR | 생성 후 갱신 |

판정 계층: `PASS`, `FAIL`, `NOT_RUN`, `BLOCKED`, `MOCK_ONLY_PASS`, `READY_FOR_WSL2_ACCEPTANCE`. 실제 센서와 물리 확인 없는 `PASS` 승격 금지. CI가 Gazebo 렌더링/동적 pose 브리지를 실행할 수 없는 경우 L2는 `BLOCKED` 및 WSL2 경계에 명시합니다.

학습 데이터 라벨은 A 자동 관측을 B 정답 라벨로 승격하지 않습니다. 식기 물성값은 실험값이고 실제 식기 안전 인증 아님.
