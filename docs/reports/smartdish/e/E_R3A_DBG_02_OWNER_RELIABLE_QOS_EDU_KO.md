# E-R3a DBG-02 — 대용량 Image QoS 계약 인수
## RED 증거
Run [45936259166](https://github.com/silverbjin/samsung_AXI/actions/runs/45936259166), SHA 127f43f708bb16cbf5b3c2f10634498d30a87b87, job 140300049285. 원본 artifact 다운로드 및 C 빌드 PASS. artifact download SHA256 4e27f10c7d9a7f64a4bc3bad0bc8db87d9a0848aab54527f0b98f5d90a6fdb53 일치. C 모델 test double/threshold/missing UNKNOWN은 정상. 최초 오류 E_R3A_IMAGE_CACHE_ACK_TIMEOUT stamp=1. 5초 안에 C cache accepted 증거 없음. artifact 15169794905, ZIP SHA256 11284d290137672f7a6d0bbf342b29840c26f79d6387dbe8445e0af5b7be696f (upload log). 
## 근본 원인 분석
A13 DBG-16에서 실제 bridge가 RELIABLE이고 대용량 fragmented RGB가 BEST_EFFORT에서 누락될 수 있음이 기록되었다. A13 capture는 RELIABLE depth10으로 수정되었으나 C ROS adapter는 계속 qos_profile_sensor_data(BEST_EFFORT)를 사용한다. RED1→RED2에서 publisher만 RELIABLE로 바꿔도 C cache ACK가 없다. DDS QoS 호환과 실제 대용량 샘플 전달은 별개다. subscriber RELIABLE로 동일 계약을 적용하고 검증한다. 패킷 단위 원인은 아직 직접 캡처하지 않았다.
## GREEN 후보
Owner Gazebo 모드만 RELIABLE/VOLATILE/depth10. 기존 기본 모드 BEST_EFFORT 유지. 명시적 C_TRAY_IMAGE_QOS 로그 및 L0 분기 테스트. C predictor, model loader, approved SHA, threshold, timeout, staff gate 그대로. 동일 RED artifact PNG 재사용, 별도 capture source pin 유지. 새 CI 결과 전 PASS 금지.
## 교육
QoS compatibility는 delivery guarantee가 아니다. 로그가 UNKNOWN이라는 이유로 AI를 재학습하지 않는다. 원본 PNG→DDS→C cache→predictor를 각각 분리한다. 사후 shutdown traceback은 별도 검증 대상.
