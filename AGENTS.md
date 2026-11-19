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
