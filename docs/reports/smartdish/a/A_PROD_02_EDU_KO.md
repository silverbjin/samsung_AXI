# A-PROD-02 교육용 개발 보고서 — 장착 트레이 및 실제 RGB
2026-11-27 / 공통 Seed 57c5f57b471a92ae11adf1d2432d44aa8640d2ad / PR #67

## 목표와 설계
기존 Waffle 모델을 수정하지 않고 생성형 SDF 오버레이에 540×540×30mm 트레이, 지지대, 질량/관성, collision, fixed joint, 실제 하향 RGB(640×480, 5Hz)를 추가한다. 0.47kg은 후보 모델의 합성 질량이지 HW 측정값이 아니다. 기존 브리지에 이미지/정보만 추가하며 clock 중복 금지. 기존 S7 world/launch와 AI OFF 보존. 490mm 접시 지름 때문에 footprint/CM 검수와 E 승인 전 실제 주행 금지.

## RED → GREEN
- RED d4329406c7340c48c2d5ddb83d211fdfd42527c5: [45946889408](https://github.com/silverbjin/samsung_AXI/actions/runs/45946889408), 신규 모듈 미구현; artifact 15175385388, sha256 a0918b2950c69088cfa7d4ab109650ce260b34b08ee3d0085f44daaa2e05835b.
- GREEN e18c5eab09af3c927c53f0ac57136094cd6cae02: [45946917577](https://github.com/silverbjin/samsung_AXI/actions/runs/45946917577), 12 passed; artifact 15174838578, sha256 10ebd9a41e6cf83705b96f166e4639c467f559101cc39b31bf95ef57e13cb5d3.
- REVIEW 441d155b966e802462c0b9bf7905e089da69eaa6: 지지대 간섭 후보 제거.
- CI 설정 갱신 중 JS replacement 오류로 YAML 일부 중복 삽입(5d4abb91...). 071816e7a57d012ff2430eaa151721f19f89239a에서 교정, PR 역할 CI 실제 실행 확인. [45947221157](https://github.com/silverbjin/samsung_AXI/actions/runs/45947221157), L0 18 passed, artifact 15174654057, sha256 7e240b19ae7e21377a22e409890fb8316f59bad968d1ef5e5e0fc0c025709508.

## 실제 L2 원본 분석
같은 Run의 실제 Gazebo job 140334672558은 FAIL. [Artifact 15175306969](https://github.com/silverbjin/samsung_AXI/actions/runs/45947221157/artifacts/15175306969) ZIP을 다운로드하여 SHA256 b6f7a0565a9d382fe613c576c7f8580a3771875a722a6a4c7df925a742f82acf 일치 확인. stacked/evidence.json: fixture ID 73, robot ID 92, clock/tray publishers 각각 1, 종료 코드 모두 0/forced=false. table/tray 실제 RGB stamp 1119000000,1200000000,1400000000 ns. PNG 640×480 RGB를 decode하여 원본 RGB hash 일치 확인: table 2736c0408b7bb56e9249cb73b90d56531e12673b94addbc43748104df0e146b0; tray d0280262f2cae66a5bfd45c4d58b5dd5cd289829ad0c5e21fb29e60c128e8be4. stacked 한정 실제 no-goal 시작 PASS. 독립 station이 아닌 동일 world에 CI 전용 식탁 관측 카메라를 추가했으며 제품 AI 입력과 분리.
empty/evidence.json: 초기 fixture count 0, 정상 종료, ACTUAL_RGB_OR_CLOCK_TIMEOUT. 로그상 카메라 광고와 bridge 생성 확인; 이전 증거는 수신/거부 카운터가 없어 근본 원인 미확정. 빈 식탁 단색 RGB가 다양성 검사에 걸릴 수 있는 후보를 찾아 8e2baff814c9f0b8511430f1d34460d2e1880a9c에서 empty table에 한하여 nonblack 저다양성 수신 허용, 다른 영상 검수 유지, per-topic 수신/거부/clock 진단 추가. 수정 후 GREEN 미확인. 반복 재실행으로 성공을 선별하지 않는다.

## 판정
L0 PASS (해당 검증 SHA에 한함), stacked L2 부분 PASS, 전체 L2 FAIL/HOLD, 후속 수정 검증 대기. 주행/동적 적재/제품 ACK/Owner L3 PASS 아님. 기존 A13 독립 검증 증거는 제품 신규 검증으로 전용 금지.
