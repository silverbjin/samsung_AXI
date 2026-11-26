# P0–P1 증거 및 ROI 유사도
QA04 accepted SHA와 report SHA를 고정하고 안전 TAR/내부 manifest를 기존 코드로 검증한다. A16 scene ID/trial/layout/family/image/pixel을 QA04 report와 대조; QA04 report는 A15 개별 기록을 포함하지 않아 A15는 고정 inner/image SHA 및 생산 design/verdict에 연결한다. A15/A16 전체 물리 재검수는 반복하지 않는다. 실제 t0 카메라·트레이 pose, SDF visual box의 8개 모서리 투영, dish 보수 bbox union을 crop한다. 화면 밖은 실패, clipping 없음. Full/tray/dish aHash(기존 64bit 문자열), dHash(9x8 bicubic), 64x64 grayscale 비중첩 8x8 block SSIM을 비교. pHash/edge는 추가 의존성/비교 가치 검토 후 보류. 해시 0/4/8/12는 탐색 후보뿐. 66 pair와 대칭 12x12 행렬, QA04 full hash 차이 기록. 신규 실측 NOT_RUN (A16 및 QA04 원본 미확보).

## A15 실제 독립 예비 실측 (4/12, 공식 QA05 실행 아님)
현재 컨테이너의 A15 Owner TAR 828c168...ee05, outer15/inner64와 기존 QA03 Owner 진단 dea580...6e98 내부3/3을 직접 대조. 4 scene/trial/layout/family/file/pixel/aHash 일치, 실제 t0 Pose/CameraInfo/SDF 및 bbox 재계산. Pillow 12.3.0 독립 검토 스크립트(공식 QA05 checkout 실행 아님). 6쌍 Full/Tray/Dish aHash ≤0: 3/0/0, ≤4:6/6/2, ≤8:6/6/5, ≤12:6/6/6. aHash 범위 0–2/1–4/3–9, dHash 1–5/5–10/7–20, block SSIM 0.9393–0.9813 / 0.7612–0.8710 / 0.4645–0.7199. 공통 배경 영향 및 ROI 정규화 효과가 함께 작용할 수 있다. 원본/개별 private 결과/HTML Git 미게시. A16 원본+diag+QA04 진단 미확보이므로 12×12, 신규 shortcut 및 group split 실제 분석 NOT_RUN, 기존 B-Q01 PASS/Q02~07 HOLD 유지.


## 실제 12장면 재검 (2026-11-26)
이 절이 앞선 원본 미확보 상태를 갱신한다. A15/A16 raw와 A16/QA04 diag 네 개 pin 및 sidecar, outer/inner 79+137+57+3=276/276 검증. QA04 report SHA 일치, A15 QA03 4장면 ID/파일/픽셀 별도 대조 일치. 공식 f1d9e803 검수 함수 exit0, 기존 물리 검수 재사용. Full/Tray/Dish aHash ≤0:22/1/0, ≤4:61/25/12, ≤8:66/46/40, ≤12:66/59/60. Full 66쌍 이전 QA04와 동일. Full/Tray/Dish aHash 평균 2.0606/6.6667/7.8485, dHash 평균 5.0606/15.2879/15.7576, block SSIM 평균 .93844/.76066/.56985. 정확한 file/pixel 중복 0. Full aHash0 22쌍 중 다른 물리 관측 13쌍. 배경 및 ROI crop 정규화 영향; 중복 확정 아님. 비교 66쌍, 9개 12x12 CSV, private 결과만 전달.
