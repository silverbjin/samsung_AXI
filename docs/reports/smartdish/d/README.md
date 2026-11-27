# SmartDish D — 교육용 개발·디버깅 이력 인덱스

원칙: **주니어 개발자가 문서만 읽고 요구→구현→테스트→오류→조치→인계 흐름을 복원**할 수 있도록 각 커밋·검증 종류를 연결합니다. D 브랜치 Draft PR #38은 main으로 병합하지 않았습니다.

| 순서 | 읽을 보고서 | 코드 커밋 | 알아야 할 실무 포인트 |
|---|---|---|---|
| 0 | \`docs/pm/SMARTDISH_D_WBS_RISK_20261123_KO.md\` | S7 main 기준 | MVP 범위·요구 추적·기한 |
| 1 | \`D01_MISSION_FSM_EDU_KO.md\` | 22a78f6d | 코어 FSM과 사용자 초·Nav2 분리 |
| 2 | \`D02_ROS_TRANSPORT_EDU_KO.md\` | e8b559be | pub/sub, JSON 계약, RELIABLE/VOLATILE |
| 3 | \`D03_UI_FLOORPLAN_EDU_KO.md\` | f6aaecbe | UI 도면 좌표 vs map Pose, Tk 이벤트 루프 |
| 4 | \`D_DBG_001_CONTRACT_MISMATCH_EDU_KO.md\` | b3e9bfdb | A↔D 파서 비교, 위험 최소 수정 |
| 5 | \`D04_RELEASE_VERIFICATION_EDU_KO.md\` | 문서 커밋 | 원격 L0/L1와 실제 이동 NOT_RUN 구분 |
| 6 | \`docs/handoff/D_HANDOFF.md\` | PR HEAD 확인 | E 팀에 책임·차단·재현 명령 전달 |

시험 결과와 실제 사용 환경을 혼동하지 않습니다. D FSM 테스트의 3개 \`SUCCEEDED\`는 테스트용 입력이며 Nav2 이동 증거가 아닙니다. S7의 기존 실제 2-leg PASS를 SmartDish 신규 3-leg PASS로 재사용하지 않습니다.

표준 로그 기재: 기준 SHA → 최초 실패 입력/로그 → 불변 조건 → 수정 함수/근거 → 재검 명령·run ID → 사실/미검증·차단사항.

## D05 — Git 작업환경 Fail-Fast 실행기 (2026-11-23)

- [D-DBG-003 사용자 원본 오류/근본 원인](D_DBG_003_GIT_WORKSPACE_COLLISION_EDU_KO.md)
- [D05 원샷 실행기 개발·테스트 보고서](D05_WSL2_FAIL_FAST_RUNNER_EDU_KO.md)
- [WSL2 초심자용 실행 가이드](../../../handoff/D_WSL2_ONE_SHOT_GUIDE_KO.md)
- [D05 Git fixture/L0 CI](https://github.com/silverbjin/samsung_AXI/actions/runs/45124460216)
- [D05 실제 Jazzy 원샷 CI](https://github.com/silverbjin/samsung_AXI/actions/runs/45124624797)

D05는 기존 `~/samsung_AXI`를 보존하며 전용 worktree로 검증합니다. CI 모의 Git/ROS 테스트를 Gazebo 실주행 인수로 승격하지 않습니다.

- [D-DBG-004 CI Git SHA race/고정 원격 수정](D_DBG_004_CI_REMOTE_HEAD_RACE_EDU_KO.md) — 실패한 CI의 최초 로그와 immutable SHA 기반 재검증 방식

## D07 — UI-QA-001 Tkinter 레이아웃 잘림 수정

- [D07 UI 잘림 원인·수정·검증 교육 보고서](D07_UI_LAYOUT_CLIP_DEBUG_EDU_KO.md)
- 코드: `355d12ab807daff986072355d9d733894c47cd09` / UI 입력을 1열 세로 배치하고 Canvas를 동적으로 축소
- 검증 경계: L0/ROS Jazzy L1과 강사 WSLg 화면 시각검수는 별개; WSLg 현장 NOT_RUN

## D 중간 개발 회고 — 도구·ROS 2 연동·실제 UI 승인 (2026-11-23)

- [D 중간 개발 보고서: 도구 선정→코드→FSM/ROS→A 통합](D_INTERIM_DEVELOPMENT_TOOLS_ROS2_INTEGRATION_20261123_KO.md)
- [D07 화면 결함·수정 근거](D07_UI_LAYOUT_CLIP_DEBUG_EDU_KO.md): **사용자 IDLE 화면 시각 QA PASS (2026-11-23)**, 실제 동적 UI와 A+D 주행은 NOT_RUN
- 사용자 제공 `image(20261123-073249).png` (1219×769, SHA-256 `60a0cc670e1a7349cb4306c8f456cfd5dc6a75566674a58c03b22deefa933c08`) — 화면 이미지 원본은 채팅 첨부, GitHub에는 증거 해시·검수 판정만 기록

## 2026-11-27 — D-AION-00~04 C+D AI ON 계약만 검증 (제품 AI ON HOLD)

- [D-AION-00 제품 정책·C→D 인계 읽기 전용 감사](D_AION_00_READ_ONLY_POLICY_AUDIT_20261127_KO.md)
- [D-AION-01 제품 모델 승인 없을 때 Manager/UI Fail-Closed](D_AION_01_PRODUCT_ADMISSION_FAIL_CLOSED_20261127_KO.md)
- [D-AION-02 ID/capture/저신뢰·모델 SHA/5초 deadline](D_AION_02_STABILITY_CONFIDENCE_FRESHNESS_20261127_KO.md)
- [D-AION-03 NEEDS_CONFIRMATION 직원 승인·ABORT](D_AION_03_STAFF_CONFIRMATION_20261127_KO.md)
- [D-AION-04 실제 Jazzy DDS model-less C UNKNOWN, D/E AI OFF 회귀](D_AION_04_MODEL_LESS_DDS_E_REGRESSION_20261127_KO.md)
- [D-DBG-AION-001 CI 최초 Pillow 수집 실패·최소 환경 수정](D_DBG_AION_001_CI_PIL_COLLECTION_20261127_KO.md)
- [CI #45926489996](https://github.com/silverbjin/samsung_AXI/actions/runs/45926489996): L0 **92 PASS**, 실제 Jazzy L1 **3 packages/DDS PASS/NO_GOAL**. 실제 모델/AI ON/WSL2는 NOT_RUN.
- [E 최종 승인 전 인계](../../../handoff/SMARTDISH_D_AI_ON_CONTRACT_ONLY_TO_E_20261127_KO.md) — **D_AI_ON_CONTRACT_ONLY_READY / PRODUCT_AI_ON_NOT_AUTHORIZED**.
