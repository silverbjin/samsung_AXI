# A-PROD-00 — 고정 Seed 및 A 소유 경계 감사
2026-11-27 / 계약 v1.1 / schema 2 / OWNER_PRODUCT_RECOVERY

## WHAT / WHY
공통 Seed 57c5f57b471a92ae11adf1d2432d44aa8640d2ad 확인. PR #66 open/draft/unmerged, E HEAD 동일, main 1d7bbf244143aeb8a9b6c71f9c2605d53ac38b4b. A 브랜치는 지정 SHA로 신규 생성 후 HEAD 재조회 일치. 필수 5개 문서 모두 해당 SHA에서 읽음. A00 읽기 전용 감사 범위 PASS, 새 L0/L1/L2/L3 NOT_RUN.

## HOW / 원본 blob
- scripts/s7_scene.py 0944ed8dce89a4f1f5d21a9c3df0b411abc9e826: world_file opt-in, stacked/empty, static 1 stack / 3 plate visuals+3 rims.
- scripts/s6_scene.py 9ef91c8c504126dcf08577f08c182f9a1478fc55: world T03 (2.65,-3.20), fixture (2.65,-2.91). table top .70m; radius .245m, 일부 overhang. 초기 시각 fixture이지 동적 검증 아님.
- restaurant.sdf 58feef3ce4d3ac9f6881e752ba479cd87e33330c; UserCommands/SceneBroadcaster/Sensors already enabled.
- navigation.launch.py dc50332262053bee063f43ec0c39667b454da288; world.launch.py e25fa0aec8bf9bda186d51da2347e97d525eb104: explicit world/robot/bridge paths, spawn name waffle_pi. 기존 default 수정 불필요.
- smartdish_tray_camera.py 4d03e4270e59eae9da5fcbea13b067fb590f90cc: camera-only prototype. A12 standalone world 9523cc89000042b15d5e293285bdfb71aca7aaf6: dynamic plate inertial/pose design 참고, 독립 world 사용 금지.
- base bridge 59f561775501745a568c2d97165e3910f598231d: clock 1, cmd_vel ROS_TO_GZ. standalone tray bridge 3a8403c9f96d7a807c5dcc7b10cc04957b997ff8: 그대로 병합 시 clock 중복 위험.
- navigation_adapter.py 0a84bb6ed4fa4a0bedeee2f7952b7cfac577ca9f: BasicNavigator, goal/result legacy, interruption cancelTask만 존재. exact UUID/terminal/continuous stop 미구현. table_poses.yaml 3acee3dcd9616a4d9048c73af11a13124ac68656: map HOME/T03/DISH_RETURN. world와 혼용 금지.
- 기존 A tray workflow 51c3f19d16054bc5ea0c18fc212ff470374ff391: push filter old branch. 신규 역할 CI 필요.

## 소유 및 보호
A 신규 product scripts, tests, smartdish_robot 내 opt-in 구현, A 전용 workflow/report만. legacy AI OFF runner, world/map, common contract, C/D/B, E runner, A14~18 연구 변경 금지. E report의 기존 R4/R1/R2/AI OFF는 재사용; 이번 제품 증거로 승격하지 않음. Test4/weight 접근 없음.

## 인터페이스 협의 필요
D/E와 실제 accepted goal UUID 전달 경로(현재 v1.1 명시 안 됨), accepted 이전 timeout lockout, 초기 stack_id manifest를 D에 전달하는 방법, pre-capture ABORT correlation을 합의해야 함. 기존 메시지 확장 금지. S7 접시 지름 .49m가 Waffle footprint를 넘을 가능성이 있어 tray/CM 영향 확인 후 E 승인 전 실제 Nav2 이동 금지. 동적 접시와 고정 attach의 증거 차이 명시. A01부터 신규 실제 CI로 검증하며 L2/Owner 인수 전 PASS 확대 금지.
