# Samsung AXI 공통 개발·디버깅 지침

이 저장소의 모든 AI 개발 에이전트와 기여자에게 적용합니다. 상세 규칙: [`docs/REPORTING_POLICY.md`](docs/REPORTING_POLICY.md).

1. **각 작업 단위 종료 시** `docs/reports/tasks/`에 Markdown 경과 보고서를 1건 작성하고 해당 코드/설정 변경과 **같은 커밋**에 포함합니다. PASS, PARTIAL, BLOCKED, NOT_RUN을 실제 증거와 구분합니다.
2. **디버깅 이슈가 발생하면** `docs/reports/issues/`에 Markdown 문제 해결 보고서 1건을 작성합니다. 반드시 **현상 → 재현/로그 → 첫 실패 지점 → 원인 가설 → 근거 확인 → 최소 수정 → 동일 경계 재검 → 판정**을 기록합니다. 미해결이면 `HOLD`/`OPEN`으로 남기고, 해결한 것으로 꾸미지 않습니다.
3. 각각의 보고서에는 **왜 이 순서/도구/수정을 선택했는가**, 대안 중 무엇을 하지 않았는가를 2~4문장으로 설명하여 훈련생이 개발자의 의사결정을 따라갈 수 있도록 합니다.
4. GitHub PR/Actions Run URL, 해당 commit SHA, 실행 명령, 첫 실패 메시지, 실제 ROS/Gazebo/WSL2의 검증 경계를 기재합니다. 실행하지 않은 부분은 반드시 `NOT_RUN`으로 씁니다.
5. 보고서 본문은 짧게 유지합니다(경과 1쪽 내외, 문제 해결은 필요한 만큼). 대형 로그·영상·ROS bag을 Git에 넣지 않고 URL 또는 간략한 발췌와 재현 명령만 보존합니다.
6. 테스트를 문서 때문에 불필요하게 반복하거나 CI를 늘리지 않습니다. **최종 GUI 인수는 강사 WSL2에서 단 한 번** 수행하는 MVP 원칙을 유지합니다.
7. 새 작업의 시작 시 이전 보고서의 `남은 과제/미검증`을 먼저 읽고 중복 개발을 피합니다. `docs/DEVELOPMENT_LOG.md`에는 한 줄짜리 색인만 추가합니다.

**경과 보고 템플릿:** `docs/reports/templates/TASK_PROGRESS_TEMPLATE.md`  
**디버깅 보고 템플릿:** `docs/reports/templates/DEBUG_RESOLUTION_TEMPLATE.md`

## 새 최우선 운영 정책: Agent-first / WSL2 final-only (2026-11-27)

**기본은 에이전트가 개발·검수·GitHub CI·보고서를 끝까지 처리하는 것입니다.** 강사 WSL2의 개발·디버깅 반복을 기본 작업 방식으로 삼지 않습니다. 기존 공통 원칙보다 이 섹션을 우선 적용합니다.

1. 새 개발은 Agent가 저장소 HEAD/과거 PASS 원장 조회 → 독립 feature branch → RED/GREEN 최소 수정 → 공개 CI L0/L1 및 가능한 L2 → 교육 보고·인수 원장 → 원격 HEAD 재조회 순으로 완결합니다. Owner에게 개발용 복수 명령·환경 확인 출력을 요구하기 전에 **이미 제출한 TAR·SHA·Actions·기존 자료로 진단**합니다.
2. WSL2 실행을 요청하는 유일한 사유는 **공개 CI/Agent 도구로 증명할 수 없는 비공개 자산·사용자 하드웨어·GUI·실물 데이터**, 또는 **최종 Owner L3 인수**입니다. 단순 코드 컴파일·fixture unit test·Git 조작·문서·라이선스·로그 분석은 Agent가 합니다.
3. Owner에게 불가피한 명령은 원칙적으로 **Immutable 40자리 SHA 고정 one-shot 1개**로 제시합니다. 런처 내부에서 필요 환경 자동 활성화, 깔끔한 작업 트리 검사, 의존성·PIN·증거 SHA·정량 조건 사전 진단, fail-fast, 최소 TAR+sidecar SHA 생성, 프라이빗 모델/데이터 비포함을 수행합니다. 별도의 환경 확인·pip·source·2개 이상 수동 스텝을 요구하지 않습니다.
4. **성공 증거 재사용**: P0 42/42, P1 CPU/weight, P2 학습, P3 pretest checkpoint 봉인 등을 다시 실행시키지 않습니다. 새로운 Gate만 최소 1회 실행하며, 실패 시 원본 증거를 먼저 읽고 **에이전트에서 최초 실패 지점을 수정한 뒤** 정말 필요한 경우에만 동일 Owner 경계를 재검합니다. 무한 재시도/10·15회 반복/WSL2 성공 확인 요구 금지.
5. 새 실환경 진단이 불가피하면 `scripts/smartdish_c_v1_owner_diagnostics_once.sh`를 **필요 시 단 1회** 사용하거나 최종 인수 런처에 그 모듈을 내장합니다. 이 스크립트는 비공개 이미지·Test·훈련·Gazebo를 실행하지 않으며 C 가상환경만 사용합니다. **현재 C P3 pretest는 이미 PASS이므로 재실행 요청하지 않습니다.**
6. `CI PASS ≠ WSL2 Owner PASS ≠ 연구 모델 성능 PASS ≠ 제품 안전/AI ON PASS`를 구분합니다. 새로운 승인 없이 P3 Test4 개봉, 추가 P2 학습, B Data Freeze 변경, A19, Contact HOLD 해제, E 제품 AI ON, Draft PR의 main 병합 금지.

상세 적용·역할 분담·예외 처리: [Owner WSL2 최소 실행 정책](docs/policies/SMARTDISH_AGENT_FIRST_WSL2_FINAL_ONLY_POLICY_KO.md).
