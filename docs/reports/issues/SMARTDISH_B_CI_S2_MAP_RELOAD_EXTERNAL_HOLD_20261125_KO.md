# SmartDish B 인수 중 발견된 Restaurant CI S2 지도 재로딩 외부 실패 (원인 경계 보고)

- 관측 Run: https://github.com/silverbjin/samsung_AXI/actions/runs/45555957977
- 관련 코드 SHA: `eae0e8553762addafb66fcee4ae8dd39b75d971f`
- **B dataset CI**: https://github.com/silverbjin/samsung_AXI/actions/runs/45555957528 — **74 PASS**.
- **Restaurant Robot MVP CI**: L0 PASS, L1+L2의 `S2-MAP-02 / real restaurant lidar survey and map quality` Job 실패.
- 최초 오류: `RESTAURANT_S2_MAP02_BLOCKED=SERVICE_FAILED_RELOAD_CONFIGURE` → `RuntimeError: SERVICE_FAILED_RELOAD_CONFIGURE`, `scripts/ci_s2_map02.py:258` / `:186`, exit code 1.
- 실패 직전 12/12 survey waypoints 성공, `S2_MAP02_COVERAGE` 기록이 존재함. 지도 저장/reload를 수행하는 ROS lifecycle configure 응답을 얻지 못한 단계가 첫 실패 경계임.
- 이 현상은 B 이미지·TAR·라벨 코드와 별도인 S2/Gazebo/ROS 경로에서 발생. 아직 환경/일시적인 서비스 타임아웃인지, 코드 회귀인지 단정하지 않습니다.
- 이번 B 브랜치에서는 S2/CM/Nav2 코드를 수정하거나 ROS/Gazebo CI 반복 실행을 유발하지 않습니다. 통합 담당 E에게 실패 Run + Job 139008152380 + 최초 오류를 인계하고 원인 조사만 해당 소유자가 진행합니다.

**판정:** B15 사용자 데이터 인수 PASS 및 B 데이터 계약 CI PASS와 **전체 레스토랑 CI FAIL**을 서로 독립 원장으로 기록. 전체 CI를 PASS로 조작하지 않음.
