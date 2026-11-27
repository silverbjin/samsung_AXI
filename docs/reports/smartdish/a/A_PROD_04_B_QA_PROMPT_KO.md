# B 담당 독립 물리 증거 QA — A 개발 완료 후
당신은 B 데이터·물리 증거 QA 담당이다. silverbjin/samsung_AXI, A #67 기능 PIN 7d8bf9ec30f88c79ed1035b485a40aa3e7c3b688, E #66 @2dc70622d8dc8b718366e5533cbbc320fd5dbc51. A_PROD_04_E_HANDOFF_KO.md 및 DBG10/11/11_GREEN 읽기. B 전용 브랜치만 수정.
1. 실제 artifacts 15178590920,15178773153,15184188608,15185112687,15185567891 다운로드. ZIP/TAR/내부 SHA256, source/upstream PIN, same configuration hashes 확인. 세 독립 session이며 앞 두 CI 전체 RED와 검증된 성공 구간 구분.
2. 실제 ECM raw ticks/pairs를 독립 분석하여 timestamp/iteration gap, entity identity, world→tray transform, relative center/tilt, geometry separation, mast separation, expected contact pair 및 positive support 증거 검수. contact silence를 무충돌로 해석 금지.
3. actual action UUID/terminal stop, load/unload same IDs, 10/5s wait, 20/20 deadline, journal receipt/hash, RGB event order 및 실제 종료 ACK 검수. 실제 물리 증거를 AI GT/human approved label과 구분. 기존 B 연구 파이프라인 보존.
4. B QA report/코드/테스트를 커밋. E 최종 통합에서 사용할 PASS/HOLD ledger와 정확한 실패 경계 제공. A/E/main 무단 변경 금지. E final single-session test 및 Owner L3 별도.
