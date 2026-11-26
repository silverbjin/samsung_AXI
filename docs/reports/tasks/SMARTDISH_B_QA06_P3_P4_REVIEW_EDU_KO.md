# P3–P4 품질·사람 검토
QA05 고정 artifact의 66 pair 재사용, 동일 ROI 알고리즘 124 신규. 보수 bbox는 segmentation 아님. 190 pair/geometry/shortcut/가상 family split. 20행 workbook: RGB/overlay/top-view/변위/물리 metric/near pair. 사람 필드는 공란, 100ms 표시용 그래프. 누적 경로는 정량 metric에 기록. 관측값은 GT 아님. 실제 결과 후속 기록.


## 실제 20장면 결과
20 layout/6 family, file/pixel exact duplicate0. 66 기존 pair reuse+124 신규=190. Full/Tray/Dish aHash<=8 190/120/146, distance0 50/1/0, near union167. Avg SSIM .9354/.7522/.5837. 기존 4 family nominal center×signed offset cells9→13/24. 작은 offset +5/-2/zero1 모두 유지; 큰 + 5 large/1 other; 큰 - 5 유지/1 other. 총13/5/2 descriptive not labels. 34/34 conservative bbox pair overlap (not occlusion). 224 center crop bbox 20/20 in frame; not human observability. 540 family assignments, all3 observations every split0, two broad observation types every split324 (not labels, not approved). Actual 20 blank review rows and 167 blank near pair review rows. No automatic A19.
