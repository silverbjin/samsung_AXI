# E-R3b/R3c — 실제 sensor-C 및 D staff DDS 검증 완료
## R3b 실제 성공
- SHA 7866267c7e743a20ee078c157f0f3bb15741023e, [run 45936589616](https://github.com/silverbjin/samsung_AXI/actions/runs/45936589616) success.
- Artifact 15170892333 SHA256 e6395d55511b04f7235f5b2f240c6311489a16f187b8faa604e6261766bed1c5 직접 재계산 일치.
- ROS domain 84, publisher ros_gz_bridge, A 51 callbacks, witness 53 frames, actual C predictor stamp 600000000, RGB sha dae6f532d0b5e4717c8c174efe0bac19de9bfc9ddcbad9bb3707685e81acc451. No replay. C test double STABLE .75. no Goal/cmd_vel. C exit 0, A exit 0. 중복 rcl shutdown 수정 확인.
- [R3a regression 45936589480](https://github.com/silverbjin/samsung_AXI/actions/runs/45936589480) success, [E L0/L1 45936589474](https://github.com/silverbjin/samsung_AXI/actions/runs/45936589474) success.
## R3c 실제 성공
- SHA 0400e1b109e99d2b9d2267458b13daea8afb6634, [run 45936800169](https://github.com/silverbjin/samsung_AXI/actions/runs/45936800169) success.
- Artifact 15170568492 SHA256 a0f30e4eee97fde78582958f8ae47de6b95c79ef51e5709f141b30c34cd49df8 직접 재계산 일치. Actual D manager DDS; synthetic A/C endpoints only. 5/5 pass: STABLE+approve 3 goal messages, STABLE/UNSTABLE/UNKNOWN/TIMEOUT+ABORT 각각 첫 goal 1개, 후속 0. wrong capture, wrong request, duplicate confirm 차단. D exit 0. 종료 시 rosout context invalid 경고는 후속 진단 항목.
## 기존 회귀 인프라 이슈
7866267c [E A+D PR CI 45936594612](https://github.com/silverbjin/samsung_AXI/actions/runs/45936594612) L0는 apt update Microsoft repo 403로 test 실행 전 exit100. 해당 코드 기능 결함 아님. 다음 SHA의 E A+D L0는 PASS, L1 상태 별도 확인. 보안 서명 검사 비활성화, 패키지 설치 반복 또는 원인 없는 코드 수정 금지. Restaurant 이전 run canceled는 PASS 아님.
## 교육
R3a replay, R3b actual live, R3c real DDS + mock payload의 차이. private v1 inference, robot-mounted tray, actual Nav2 AI ON L3는 미승인.
