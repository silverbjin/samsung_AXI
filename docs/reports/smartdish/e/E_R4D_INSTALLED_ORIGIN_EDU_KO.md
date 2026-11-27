# E-R4d — 실행기·체크아웃·빌드·ROS 엔트리포인트 단일 출처 검수 (교육)
## WHAT/WHY
기존 R1 다운로드 wrapper 외부 비교는 성공했지만 실제 runner에는 자동 cmp가 없었다. 기존 R2 실행 pin 316639a0…에서 후손 PIN으로 전환할 때 이전 코드가 4dbdeca6…만 허용하고 per-PIN install overlay가 아니었다. 이전 작업공간을 보호하면서 새 실행기와 빌드 출처를 단일 SHA로 묶는다.
## HOW
허용된 이전 Owner PIN 2개에서만 clean descendant detached checkout. force/reset/clean 금지. 다운로드 script blob을 commit tree와 비교하고 checkout script와 cmp 후 runtime preflight. 기존 C venv와 모델 검사 그대로 재사용. --run-ui에서 per-PIN build/install 경로 사용, 실제 ROS package prefix/entrypoint shebang, Python installed module bytes, launch bytes 검증 후 실행. 새 PyTorch 설치 없음. 
## TEST
기존 L0/L1 + drift fixture test 및 actual CI colcon overlay 검사. CI model-free이며 private checkpoint load는 기존 R2 증거를 보존하고 최종 Owner에서만 재검증.
## RESULT
작성 시점 신규 CI NOT_RUN. 기존 source SHA의 성공을 새 코드의 PASS로 대체하지 않는다.
