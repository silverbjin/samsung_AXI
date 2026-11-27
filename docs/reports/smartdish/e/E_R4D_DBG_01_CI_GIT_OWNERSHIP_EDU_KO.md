# E-R4d DBG-01 — 컨테이너 Git 소유권과 실행 출처
## RED
Run [45937470283](https://github.com/silverbjin/samsung_AXI/actions/runs/45937470283), job 140304105697, SHA 2e7cd5dffcb7eb3e62da4db1d25f42e358e79814. L0 PASS, 실제 colcon 3 packages finished. L1 최초 오류 `fatal: detected dubious ownership in repository at '/__w/samsung_AXI/samsung_AXI'` 다음 E_OWNER_INSTALLED_PIN_DRIFT. 원인은 CI shell의 `$(git rev-parse HEAD)`가 container bind mount의 UID 차이로 실패한 것. Python 검증기는 이미 명시 경로에만 safe.directory를 적용하고 있다.
## 수정
CI shell도 현재 checkout 한 곳만 `git -c safe.directory="$PWD" rev-parse HEAD`로 검증한다. 시스템 전체 safe.directory=* 설정이나 tracked file 검사를 제거하지 않는다. checkout PIN과 설치된 ROS 모듈/entrypoint/launch bytes 검사는 유지.
## 검증
동일 L0/L1 workflow 재실행; 설치 provenance가 통과한 후 모델 없는 fail-closed 및 실제 DDS threshold ACK가 모두 통과해야 한다. 사용자 venv에는 아무 변경도 하지 않는다. 결과는 다음 실제 CI 원장으로 판정한다.
