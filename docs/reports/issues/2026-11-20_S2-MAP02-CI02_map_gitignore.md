# S2-MAP02-CI02 — CI 실제 지도 정상 생성 후 Git 후보 게시 실패

- 기록: 2026-11-20 KST
- 선행 실제 GREEN: [PR Actions #44551738811](https://github.com/silverbjin/samsung_AXI/actions/runs/44551738811), source SHA c6271134c86484154b0df02772e03b981724e15a.
- 수집된 관측: 실제 33.3m, 12/12 waypoints, 1850 Scan, Free 24796, Occupied 1352, Known 26148, 약 9.95×8.85m, pickup→table3 connected, Map Saver 및 Map Server reload PASS.
- [Push Run #44551726313](https://github.com/silverbjin/samsung_AXI/actions/runs/44551726313): L0/L1/실제 Gazebo L2 성공; artifact 및 해시 다운로드 검증 PASS.

## 최초 출고 실패
- Job #135660949835의 마지막 `Commit to new maps candidate branch only`에서 git add 실패.
- 오류: `The following paths are ignored by one of your .gitignore files: maps/restaurant_map.pgm maps/restaurant_map.yaml`.
- 원인: `.gitignore`의 `/maps/*.pgm`, `/maps/*.yaml`에 의해 CI 검증된 최종 파일마저 무시됨. SLAM/SaveMap 문제는 아님.
- 성공 단계: `S2_MAP02_RELEASE_HASHES_VERIFIED_CANDIDATE_NOT_MAIN` 원본 로그에서 확인.

## 최소 수정
- `.gitignore`에 정확히 `!/maps/restaurant_map.yaml`, `!/maps/restaurant_map.pgm` 두 예외를 부여. 나머지 미검증 지도는 계속 무시.
- 지도 출고 단계에 해당 파일이 무시되지 않는지 점검하는 단일 게이트 추가.
- ROS/Gazebo/SLAM, 주행/0.40m LiDAR STOP, 맵 품질 임계값은 변경하지 않음.
- 재검 후 candidate branch 생성과 SHA256 manifest를 확인해야 출고 승인. 이 문서 작성 시점은 RELEASE=HOLD.

## 교육용 메시지
지도 생성 PASS와 Git 아티팩트 게시 PASS는 독립된 게이트입니다. 원인 경계를 구분하여 Gitignore 정책만 수정해야 하며, 이미 성공한 SLAM 기능을 다시 개발하면 안 됩니다.

## RESOLVED (2026-11-20 KST)
- Following Gitignore exact allowlist, one-time artifact promotion CI [Run #44557054303](https://github.com/silverbjin/samsung_AXI/actions/runs/44557054303) checked GREEN source commit ancestry, original World checksum, map YAML/PGM SHA256 and routing quality, then pushed maps/s2-map02-44551726313.
- Candidate diff reviewed as exactly four map files, temporary release workflow excluded. PR #8 merged main commit d4fd5f19095d807e5ecee0d6e21a855733557b79.
- No full SLAM re-run required just to fix git add. Issue closed.
