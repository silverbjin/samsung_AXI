# SmartDish B-QA05 실제 원본 오프라인 인수 원장 (2026-11-26)
- 실행 기준 f1d9e803725caeeeb43e6d2ad2d66c3945d30a99; QA04 인수 5b3f903b183fa17042eebaeae241aea47bad2250, QA04 검수 b36694d8c243e44147f9f32b9c2189deef1e8f9f. Platform b8ef3998973a5e33b67ddd5c5b63c3c89b837840.
- A15 raw 828c1689031f46f9523cdf836eabac9dbd22f8eff6b37860067d2ee328feee05 (79), A16 raw ec3eac2a4af99f0deefa67a44254ea1b07a9fef1ee80cd4a715156105cbb4f15 (137), A16 diag 61cd76bfedd5f3908444e6d6f1bfe9296f5e2a175c0428310812047e26566a65 (57), QA04 diag 6bb16e93a22079c588a63afc9f04e8725154b25313ea133d277d5ba547eea83f (3). 외부4/4 및 내부276/276, QA04 report 8cebb1fbe64de0b5db8acb55aa34f461f7f67c9a7158462cd3ba6289a6ca6eec 일치. A15 QA03 ID/파일/픽셀 4/4 별도 대조.
- Source-only run #45754630853 / artifact15086109925, ZIP SHA 5f70e8a4b501b44456428fce81ab6fceb5a758d74cd4113279c613e3911f9ba5, 5/5 manifest 및 4 Git blobs 일치. Linux x86_64 CPU Python3.13.5 Pillow12.3.0, 공식 audit 함수 직접 실행 exit0 4.046s. GitHub DNS 불가로 full checkout/CLI HEAD gate NOT_RUN, checkout_head=null/checkout_verified=false. 별도 wrapper provenance/diagnostic. 실제 원본 검수 완료, 사용자 WSL2 원샷 인수 별도.
- 진단 SHA 240bfe72317303566a43b0a3e97bd4c042d95ce75e36ce87e0d940808e391371 내부22/22, report SHA 80953ce1bbcca9e1205c8a3fe32c8a4c15a6389f04cec3d4c0a847397fa7808c. 원본과 private 자료 Git 미게시.
- 12 layout/4 families/66 pair, full aHash 이전과 모두 일치; Full/Tray/Dish <=8 66/46/40, exact duplicate0; 20/20 bbox overlaps (not masks), 15/24 cross cells missing; 36 hypothetical family partitions, not released. GT0.
| Gate | Verdict | 이유 |
|---|---|---|
| B-Q01 | PASS | 실제 원본 무결성 및 provenance |
| B-Q02 | HOLD | ROI 기하 PASS, per-scene occlusion 승인 없음 |
| B-Q03 | HOLD | 기존 물리 evidence 재사용, production Contact HOLD, cleanup FAIL |
| B-Q04 | HOLD | GT UNKNOWN_HOLD, 권리/사람 승인0 |
| B-Q05 | HOLD | ROI 중복 후보, offset 크기×부호 결합 및 교차 부족 |
| B-Q06 | HOLD | 미승인 가상 split만, 학습 분할 없음 |
| B-Q07 | HOLD | C real training NOT_RUN, 승인 manifest 없음 |
- 최종: B_QA05_REVIEW_ONLY 실제 core PASS; WSL2 Owner acceptance NOT_RUN. CI f1d9e803 QA05 #45754207560 53 PASS+platform7/pin; B #45754207556 174 PASS; platform #45754207554 SUCCESS. broad Restaurant #45754207547 cancelled after subsequent commit, no claim PASS. 기존 PR46/47/51/52/main 보호. A17 PR53 별도, A18 데이터 요구 제안. 새로운 Gazebo 또는 C 학습 없음.
