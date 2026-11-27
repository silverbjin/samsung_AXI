# A-PROD-03 교육용 개발 보고서 — 실제 적재/하역 및 capture ACK 후보
2026-11-27 / 공통 Seed 57c5f57b471a92ae11adf1d2432d44aa8640d2ad / Draft PR #67

## 구현 및 책임 분리
- product_contract.py: schema/profile/ID, 정지 연속성, 실제 관측 수량·pose·속도, RGB stride/encoding canonicalization, epoch/freshness, 영속 transaction journal, 중복 요청 및 crash lock.
- product_gazebo_backend.py: 실제 Gazebo UserCommands create/remove/scene 서비스, S6 식기 visual 재사용 및 독립 동적 collision 모델, 실제 entity ID 및 상대 pose 계산.
- smartdish_product_transfer_probe.py: CI 전용, 동일 restaurant world 안에서 정지 로봇에 초기 정적 식기 제거 및 실제 동적 식기 3개 생성, 관측 ID/pose/velocity/dwell, 새 RGB 저장, 동일 ID 제거 및 부재 확인. 빈 식탁 무변경 경로. 실제 Nav2 이동/반납 위치 도착/제품 ACK 검수가 아님. fixture 제거 후 생성 중 오류의 자동 복구나 성공 위조 금지.
- product_capture.py / product_capture_node.py: 실제 LOAD 증거 파일/해시와 ID 일치 조건, 정확한 fresh frame, 원본 RGB/PNG 및 receipt hash, 중복 방지, DDS 요청/응답 후보. 기본 비활성, 런치 연결/설치 executable 등록은 아직 하지 않음. 이미지 누락 시 null 필드는 D/E 합의 전 제안에 불과. 모델 권리/AI OFF 보호.

## 검수 이력
RED 테스트 921092b7d063e8b89e7e6e0b37bedd4cd4668590 및 구현 3271c61... 시점에 CI YAML 오류가 존재하여 독립 RED 실측 불가. RED PASS 기록 금지. 교정 후 071816e7a57d012ff2430eaa151721f19f89239a / [45947221157](https://github.com/silverbjin/samsung_AXI/actions/runs/45947221157)에서 18개 누적 L0 테스트 PASS. Artifact 15174654057 sha256 7e240b19ae7e21377a22e409890fb8316f59bad968d1ef5e5e0fc0c025709508. 이후 journal 증거 검증, Gazebo backend와 3개 fixture 테스트, 실제 물리 probe, capture 구현 추가. 신규 전체 SHA는 이 18 PASS의 범위 밖. [45947546973](https://github.com/silverbjin/samsung_AXI/actions/runs/45947546973), [45947577212](https://github.com/silverbjin/samsung_AXI/actions/runs/45947577212)는 조회 당시 대기 상태. 실제 물리 적재/하역, capture ACK, build/DDS PASS 미확인. A02 실제 L2 empty timeout 선행 실패는 A_PROD_02_EDU_KO.md 참조.

## E/D 합의 및 통합 HOLD
[E PR #66 논의](https://github.com/silverbjin/samsung_AXI/pull/66#issuecomment-7210766429)에 실제 accepted Goal UUID/terminal/cancel, stop, 초기 stack_id 공유, pre-capture ABORT, tray footprint 승인 요청 등록. D 담당도 동일 계약 조율 필요 사항을 게시. E 승인 미확인. 기존 navigation_adapter 미수정. 실제 D request와 연결된 제품 dish transfer controller, Nav2 exact cancel, 실제 반납 위치/주행 검증, capture 노드 package entrypoint/build/launch/DDS 및 실패 ACK 계약 확정은 남아 있음. CI 전용 probe로 제품 ACK를 대체하지 않는다. 최종 인수 전 WSL2 요청 금지.

## 다음 작업
1. 8e2baff... 진단 수정 이후 empty RGB/clock 최초 실패를 확인하고 수정 범위만 GREEN 검수. 기존 성공 stacked 증거 재사용 원칙.
2. 최신 L0 결과/물리 probe artifact 검수 및 최초 실패 수정. 정지 적재/하역이 확인되어도 실제 이동 및 제품 ACK PASS 아님.
3. E/D 승인 계약에 맞춰 A 소유 어댑터/transfer/capture를 실제 런치에 통합, UUID terminal/cancel/stop proof 및 fresh capture ACK를 CI에서 검증.
4. E 승인 전 main/E merge 금지. 판정: PARTIAL_IMPLEMENTATION / HOLD.
