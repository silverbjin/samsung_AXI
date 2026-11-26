# P0–P2 증거와 Adapter
안전 TAR exact manifest, source/phase/registry/fingerprint, t0 RGB/FOV/1ms pose/trigger/ECM/Native/ROS는 기존 QA03/04 함수 재사용. A18 GPU 유지 profile은 고정 인수 증거 참조, 별도 GL context 계측 아님. A15/A16 12개 물리 검수 반복 없음. QA05 report 및 원본 scene link 재검. 20 후보 registry. 원본 직접 검수 결과는 후속 원장에 기록.


## 실제 원본 결과
9 archive+sidecar 외부 SHA/내부505/505 PASS (QA05까지276+QA05 진단22+A18 207). 기존12개 물리 검수 재사용, QA05 scene/trial/layout/family/file/pixel link, A18 8개 1ms pose/relative metrics/settle/FOV/contact/trigger/registry/cleanup 재검산. A18 accepted GPU profile 참조, 새로운 GL context 계측 아님. Actual core f9ddc56979626d4a78decb04e7b4ca28c3824b09 exit0, 38.154s Linux CPU Python3.13.5 Pillow12.3.0; full checkout/WSL2 runner NOT_RUN. 자세한 SHA 및 검수 경계는 acceptance ledger 참조.
