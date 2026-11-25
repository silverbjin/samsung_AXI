# A-12-DBG-01 — Python XML helper 키워드 이름 충돌 (실제 CI RED→최소 수정)

- 최초 실패: [GitHub Actions #45306406046](https://github.com/silverbjin/samsung_AXI/actions/runs/45306406046), L0 `6 failed, 18 passed`, L1/L2 실행 안 됨.
- 실제 첫 오류: `TypeError: el() got multiple values for argument 'name'` (`scripts/smartdish_tray_world.py:121`).
- 재현: `build_world("ST-02",117)`에서 `el(root,"world",name=WORLD)` 호출.
- 확인된 원인: 공용 XML helper의 두 번째 *함수 인자 이름*이 `name`이었고, SDF XML 속성 `name=WORLD`와 파이썬 키워드 인자가 충돌. `ET.SubElement`나 Gazebo 물리 엔진 문제가 아니므로 기존 ROS/Gazebo를 다시 설치하거나 전체 S7 인수를 반복하지 않음.
- 최소 변경: `def el(parent,tag,text=None,**attrs)`로 인자 이름만 변경, 태그와 XML `name` 속성 별도 취급. 기존 네 시나리오·질량/마찰/좌표 및 소비자 계약 불변.
- L0 새 실행에서 동일 6개 테스트 PASS 확인 후 GREEN으로 갱신. GREEN 전에 이 문서의 상태는 **RED_FIX_COMMITTED_RETEST_PENDING**.
- 동시 선제 보완(별도 근거): CI 컨테이너 Git checkout UID가 다른 A-과거 이슈를 반복하지 않도록 exact `git -c safe.directory=<current_root>` 단일 명령으로 소스 SHA 조회; 전역 Git 보안 완화 없음. `demo`/`single`을 실제 4개 시나리오 L3 PASS로 오판하지 않도록 성공 메시지 스코프 분리.
