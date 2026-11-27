# DBG11 GREEN — 실제 lifecycle 종료 집중 검수 완료

기능 PIN 7d8bf9ec30f88c79ed1035b485a40aa3e7c3b688 / CI 45972717341 / job 140416908803 SUCCESS / Artifact 15185567891.
ZIP SHA256 75b5529c69098f8ef2d4c0c2e4945514f93d4bd468740880ecc7fa6ef99b2286; TAR SHA256 b1f9ca5867bd986b6e85a453ac35c55c153fc0ac5669844a0ab8191ba7fbfefc; 내부 60/60 독립 검수. L0 20/20.
실제 HOME→T03 goal ce8b6aa2d69c4b2993443aa556fa0d63 SUCCEEDED, odom 5.252577m, AMCL error .024795m, terminal stop 1.048041s, ECM 44161 samples 1ms gap-free, positive ground support 전 step, geometric separation .297125m. 실제 registry error max .057424m.
실제 manager startup is_active 응답 3/3 true, shutdown 직전 3/3 true, SHUTDOWN command 4 success 3/3, 종료 뒤 is_active 3/3 false. navigation 2.185873s, localization .268079s, clearance .138418s. 실제 navigation 관리 10개 노드 deactivate/cleanup/shutdown 각 10개 로그, manager complete log, transition failure log 없음. Gazebo pause ACK / clock quiescent true. Launch parent exit0 forced=false, child SIGINT -2 기록, SIGKILL/-9 없음; child all exit0으로 표현하지 않는다.
RED(45970380453)에는 navigation shutdown callback log 없음, 다른 두 ACK. 클라이언트 조기 생성·실제 응답 확인 및 bounded deadline 수정 후 GREEN. 정확한 DDS 내부 원인은 미확정. 변경을 함께 적용했으므로 어느 한 요인 단독 인과를 주장하지 않는다.
무부하 45967974937, 실제 적재 전체 mission 45970380453, 종료 집중 45972717341의 world.before_contact.sdf, transfer_robot.before_contact.sdf, map PGM/YAML, localization PGM/YAML, params, bridge, robot SDF, observer binary와 upstream PIN 일치. 동작 증거 재사용. 세 독립 session의 결합 검수이며 최신 기능 PIN full mission+shutdown 동일 session 증거는 없음. E에서 실제 통합 검수 필요. A 내부 집중 검수 PASS, Owner L3 미실행.
