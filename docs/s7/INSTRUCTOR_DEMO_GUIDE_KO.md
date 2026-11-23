# S7 — 강사용 상세 라이브 데모 가이드 (ROS 2 Jazzy / Gazebo Harmonic)

> 범위: 실제 S7 startup-stacked / empty-table 결과를 관찰·분석하는 PBL. **현재 문서는 개발 브랜치 교육 자료이며, 최종 L3 PASS가 아닙니다.** GUI 육안 검수는 강사 담당이고 기능 CI와 분리합니다.

## 1. 수업 목표와 사전 지식
대상은 ROS 2 하드웨어 초심자입니다. 기존 S6의 TABLE_3→Odom 정지→RGB 순간 구독→Vision STACKED→PICKUP_RETURN→LiDAR CM STOP을 재사용합니다. S7에서 **월드 초기 모델 로드**와 **빈 테이블의 안전 차단**만 추가합니다. 학습자는 SDF/world, ROS launch, topic, subscriber, Nav2 Action, Odom, Vision inference, safety action, hash를 연결해서 설명해야 합니다.

## 2. 환경과 저장소 준비
Windows 11 WSL2 Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic + Python3 + GitHub CLI/네트워크가 필요합니다. 초기 실행 전 WSL2에서 다음을 점검합니다.

```bash
cat /etc/os-release | grep VERSION_ID
source /opt/ros/jazzy/setup.bash
ros2 --help >/dev/null && gz sim --version
git clone https://github.com/silverbjin/samsung_AXI.git
cd samsung_AXI
git fetch origin feature/s7-startup-dishes-negative-teaching-20261123
git switch --detach origin/feature/s7-startup-dishes-negative-teaching-20261123
git rev-parse HEAD
```

**중요:** 개발 브랜치 HEAD는 가변입니다. 최종 인수에 사용할 불변 SHA 및 원샷은 CI L0/L1/L2 완료 후 공식 S7 인수 가이드에서 고정합니다. 운영자 TTY에서 `YES-S5-LIVE-GOALS`를 입력하기 전 Goal 자동 발행 금지. 교재만 읽을 경우 ROS/Gazebo 실행 불필요.

## 3. 아키텍처와 데이터 흐름
```text
restaurant.sdf (S5 original; plates ABSENT)
       |
scripts/s7_scene.py (scenario=stacked|empty)
       | generates + SHA256
generated/s7/restaurant_stacked.sdf / restaurant_empty.sdf
       |
world.launch.py (world_file opt-in)
       v
Gazebo server: dishes at startup if STACKED
       |
Navigation (Nav2/AMCL + scan-only costmap + CM)
       |
NavigateToPose TABLE_3 -> Odom physically settled
       |
temporary /restaurant/rgbd/image subscriber -> real RGB PPM
       |
S6 two-prototype ML STACKED / NOT_STACKED / UNKNOWN
       |
STACKED -> NavigateToPose PICKUP_RETURN -> LiDAR CM STOP
NOT_STACKED / UNKNOWN / missing frame -> HOLD (NO RETURN GOAL)
```

**설계 이유:** S7에서는 접시를 **Nav2 도착 후 재생성하지 않습니다**. 원본 world·지도·CM 영역을 바꾸지 않고, 생성된 S7 opt-in 월드만 선택합니다. `lazy:true`는 ROS 브리지 구독 제어이며 카메라 물리적 OFF 증거가 아닙니다.

## 4. 시연 A — S7 초기 접시의 정상 배달·복귀 (20~30분 권장 분량)
최종 CI 통과 후 [공식 인수 가이드](S7_OWNER_L3_GUIDE_KO.md)의 **하나의 고정 SHA 블록**을 사용합니다. 임의의 HEAD나 과거 S6 실행기를 섞지 마십시오. 실행 전 `--self-test` 및 `S7_OWNER_PREFLIGHT_PASS_NO_GOAL`를 확인하고, 프롬프트가 나타나면 실습자에게 예측 질문을 던진 뒤 강사가 TTY 승인합니다.

관측 순서와 설명:
1. Gazebo 초기 시점 TABLE_3에 원통형 3단 식기 모델이 있는 것은 S7의 의도입니다. 시각적 표현 품질은 강사 육안 평가이며 자동 게이트가 아닙니다.
2. Nav2 TABLE_3 Action `status=4` SUCCEEDED는 Goal에 도달했다는 뜻이고, Odom 정지 유지 확인은 별도입니다.
3. 정지 후에만 이미지 ROS 구독을 시작하여 최신 RGB 3프레임과 PPM 해시를 수집합니다.
4. 학습된 **고정 시점의 2-prototype RGB 모델**에서 STACKED를 판정할 때에만 복귀 Goal을 보냅니다. 일반물체 YOLO라고 과장하지 마십시오.
5. LiDAR 장애물 29점(이전 S6 참고) 및 Collision Monitor STOP에서 downstream `/cmd_vel`≈0, 실제 Odom≈0을 검증합니다. 정확한 S7 실측치는 S7 L2/L3 JSON을 사용합니다.

## 5. 시연 B — 실제 빈 테이블 반례 (15~20분)
일반 운영자 주행용 원샷은 STACKED만 실행합니다. 빈 테이블은 **GitHub CI의 독립 실제 Gazebo negative job**에서 자동 재현합니다. `generated/s7/empty_vision_evidence.json`과 `logs/s7_empty_console.log`를 해설하십시오.

예상: 첫 TABLE_3 성공, RGB 프레임 수신, 예측 NOT_STACKED 또는 UNKNOWN, `S6_VISION_HOLD_NO_RETURN_GOAL`, `s6_return_goal_sent=false`, **PICKUP_RETURN Goal 없음**. 음성 테스트의 원래 runner 종료코드는 비영(0이 아님)이어도 정상적인 차단 증거를 모두 검증해야 PASS입니다. 오류 코드만으로 PASS 처리 금지.

## 6. 장애 대응과 흔한 실수
- 시작할 때 식기가 보이지 않을 경우 S7 world_file이 실제 사용됐는지, `s7_scene.scenario`, Gazebo SDF 파일의 모델 수를 확인합니다. 과거 S6 late-spawn과 혼동하지 마십시오.
- TABLE_3 도착 전 이미지가 시작되면 arrival gate가 잘못 연결됐을 수 있습니다. 기존 성공 관측을 임의로 PASS 승격하지 마십시오.
- 빈 테이블에서 복귀 Goal이 발행되면 즉시 FAIL이며 일시적으로 Vision gate를 무시하는 우회 방법을 사용하지 않습니다.
- RGB 프레임 없음/불확실·Vision UNKNOWN은 목표 실패가 아니라 안전 HOLD입니다.
- Gazebo/ RViz 영상 육안 확인은 사용자 영역입니다. RTF 90%는 현재 별도 HOLD.
- 전체 ROS/Gazebo 프로세스를 글로벌 pkill하지 말고 공식 실행기의 소유 PID 정리 경로를 사용합니다.

## 7. 강사용 채점 체크리스트
| 항목 | 관측 증거 | 점수 예시 |
|---|---|---:|
| 원본과 S7 월드 구별 | scene manifest SHA·model count | 15 |
| ROS/Action/Odom 파이프라인 설명 | Goal 2개와 도착 후 정지 | 20 |
| Vision AI 근거 | 실제 PPM SHA·고정 모델 제한 | 20 |
| 빈 테이블 안전 | 1개 Goal + HOLD + no-return | 20 |
| LiDAR STOP | cmd_vel/Odom 실제 데이터 | 15 |
| 오류·버전 추적 | 불변 Git SHA, CI/L3 독립 | 10 |

## 8. 산출물·참고
- [학생 실습 가이드](STUDENT_LAB_GUIDE_KO.md)
- [강사용 코드 정답·해설](INSTRUCTOR_SOLUTIONS_KO.md)
- `education/s7/student/s7_evidence_todo.py`, `education/s7/instructor/s7_evidence_solution.py`
- [S6 G11 확정 원본](../debug/s6/20261123_G11_FINAL_WSL2_L3_ACCEPTANCE_EDU_KO.md)
- [S7 개발 사이클 교육 보고서](../reports/s7/)
