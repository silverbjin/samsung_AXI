# P2–P3 물리 및 Shortcut
SDF/실제 t0 상대 pose로 반경/두께/색상/질량/마찰/높이/상단 중심거리/오프셋/명목 지지여유를 기록한다. 보수 bbox overlap은 가시 픽셀/segmentation이 아님. World-Y torque와 signed x offset은 관측 교차이지 인과 증명 아님. 중심 0.05m, offset 0.03m 등 탐색 bin은 제품 기준 아님. 범주별 관측 분포, 순수 cell/in-sample purity 및 family×center×signed-offset 빈 조합을 기록. 고정 환경은 검증 불가. 12개뿐이므로 통계 일반화/분류기 훈련 금지. 물리 변수는 진짜 원인 후보, 배경/색/버전은 nuisance 또는 proxy. 이전 QA04 집계는 8 유지/4 큰 변위, 새 ROI/교차표 실제 결과 NOT_RUN.


## 실제 12장면 결과 (기존 NOT_RUN 갱신)
4 Family 모두 유지/큰 변위 관측 존재, 총 8/4. nominal center 3 유지/1 큰 변위, eccentric 5/3; 2 dishes 5/3, 3 dishes 3/1; A15 2/2, A16 6/2. signed support offset x>0:5 유지/4 큰 변위, x<0:3/0. 탐색 offset 0.03m 기준 small + 5/0, small - 1/0, large + 0/4, large - 2/0. 결합 규칙 in-sample 12/12 관측 구분이지만 인과/모델 성능 아님. nominal margin positive 6/0, nonpositive 2/4. 20/20 conservative bbox pair overlap, 실제 가시 픽셀 미측정. 높이 .07–.095m, 질량 .22kg, mu .65, 동일 camera/background/environment/world-Y .12Nm 500ms. brightness bin, height bin 고정은 연속값 동일 아님. 24 nominal family×center×signed offset cells 중 15 미확보. 실제 결과는 A18 데이터 설계 근거이며 승인 GT 아님.
