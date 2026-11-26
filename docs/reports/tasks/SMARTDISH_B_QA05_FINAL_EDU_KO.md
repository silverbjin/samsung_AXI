# B-QA05 개발 보고 — 구현/실측 범위 분리
부모 QA04 인수 5b3f903b183fa17042eebaeae241aea47bad2250, 실행 b36694d8c243e44147f9f32b9c2189deef1e8f9f. 기존 12 layout/4 family, 66 full aHash 후보, 8 유지/4 큰 변위는 QA04 기록이며 새 QA05 결과 아님. 현재 컨테이너에 A15 원본만 존재, A16 raw/diag 및 QA04 diag 접근 불가. GitHub DNS 차단으로 직접 clone 불가; connector로 코드/CI 제출. 실제 12장면 ROI/Workbook 실행 NOT_RUN. 신규 fixture CI 결과는 PR Actions에서 확인. 정상/예외 진단 TAR+sidecar, checkout HEAD/버전 기록. 이전 Q01 PASS 보존, 새 직접 검수 HOLD, Q02–Q07 HOLD, GT UNKNOWN_HOLD, Contact HOLD, cleanup FAIL, C NOT_RUN. 변경 범위 신규 B 코드·테스트·CI·문서; main/다른 PR 변경 금지. A17 종료 장애 독립. 원본 확보 후 동일 SHA CPU 원샷 1회, Gazebo 없음. 검수 제품 PASS와 데이터셋 출고 분리.

## A15 실제 독립 예비 실측 (4/12, 공식 QA05 실행 아님)
현재 컨테이너의 A15 Owner TAR 828c168...ee05, outer15/inner64와 기존 QA03 Owner 진단 dea580...6e98 내부3/3을 직접 대조. 4 scene/trial/layout/family/file/pixel/aHash 일치, 실제 t0 Pose/CameraInfo/SDF 및 bbox 재계산. Pillow 12.3.0 독립 검토 스크립트(공식 QA05 checkout 실행 아님). 6쌍 Full/Tray/Dish aHash ≤0: 3/0/0, ≤4:6/6/2, ≤8:6/6/5, ≤12:6/6/6. aHash 범위 0–2/1–4/3–9, dHash 1–5/5–10/7–20, block SSIM 0.9393–0.9813 / 0.7612–0.8710 / 0.4645–0.7199. 공통 배경 영향 및 ROI 정규화 효과가 함께 작용할 수 있다. 원본/개별 private 결과/HTML Git 미게시. A16 원본+diag+QA04 진단 미확보이므로 12×12, 신규 shortcut 및 group split 실제 분석 NOT_RUN, 기존 B-Q01 PASS/Q02~07 HOLD 유지.

## 리뷰 보강
초기 CI #45753723933 (43 passed=33 이전+10 QA05, common7, pin), B dataset #45753723931 (174 passed) SUCCESS. 기존 성공은 보존. 후속 리뷰에서 실패 입력 receipt, Layout/Family 충돌 및 exact-pixel cross-family split 제한, nominal center 교차, 그래프 축 자동화와 실제 스키마 유사 양성 fixture를 보강했다. 이는 새로운 합성 테스트이며 실제 12장면 실측이 아니다. 새 SHA CI는 별도 PR 로그로 확인한다. 외부 SIGKILL, clone/환경 실패 또는 출력 디렉터리 생성 실패에서 CLI 진단은 보장되지 않는다.

## 산출물 통합 검수
중간 보강 CI #45754040613 50 passed (33 이전+17 신규), platform 7 및 pin PASS, B dataset #45754040658 174 passed. 최종 기능 보강: seed0 계약과 물리 signature 중복 차단, 원본/overlay 비교, 상대 xyz 표시 CSV, actual missing-cross 기반 next_a_requirements.json, 12-scene 합성 연결 시험. 모든 실행은 리뷰 전용이며 A16 원본 미확보로 실제 12장면은 NOT_RUN. 최종 CI는 신규 SHA/PR 로그를 참조한다.
