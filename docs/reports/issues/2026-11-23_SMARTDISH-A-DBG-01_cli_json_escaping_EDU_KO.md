# SMARTDISH-A-DBG-01 — 교육용 토픽 발행 예제의 JSON 이스케이프 오류

- 날짜: 2026-11-23 KST
- 환경/경계: 교육 문서의 Bash single-quoted ROS 2 YAML 입력 → `std_msgs/String.data`의 JSON
- 상태: **RESOLVED — 동일 CLI YAML→JSON 경계 신규 회귀 테스트 L0 PASS**; 물리 ROS 주행과 무관한 *문서 입력* 결함
- 최초 확인 SHA: `e069a134117fbc52718260a56eb7ac2ebd7d7885`
- 연결 개발 보고서: [A-03](../tasks/2026-11-23_SMARTDISH-A-03_ci_handoff_EDU_KO.md)

## 1. 현상·기대·최초 실패

`docs/handoff/A_HANDOFF.md` 수동 `ros2 topic pub` 예제는 JSON 안의 `"` 앞에 백슬래시가 **3개** 들어 있었습니다. Bash 따옴표 뒤 YAML 파서는 한 번만 해제해 실제 `String.data`에 `{\"request_id\"...}` 문자열이 남습니다. 기대는 `{"request_id":"REQ-A-01", ...}`입니다.

실제 진단용 Python (ROS가 없어도 동일 계층을 재현할 수 있음):

```python
import yaml, json
bad = r'data: "{\\\"request_id\\\":\\\"REQ-A-01\\\"}"'
print(yaml.safe_load(bad)["data"])
json.loads(yaml.safe_load(bad)["data"])
# JSONDecodeError: Expecting property name enclosed in double quotes
```

이 진단은 **문자열 변환 L0**에서 확인한 것이며 ROS 토픽 발행이나 Gazebo 실행의 실패 기록으로 바꾸지 않습니다.

## 2. 원인 분석: 세 겹의 인코딩 경계

1. 셸의 작은따옴표는 내부 `\`를 보존합니다.
2. ROS CLI가 받는 `data: "..."`는 YAML이며, YAML 큰따옴표에서 `\"`가 `"`로 바뀝니다.
3. 원본의 여분의 `\\`가 JSON 본문에 남아 `json.loads`가 키를 읽지 못합니다.

**확정 원인:** 문서 작성 시 Bash 문자열/JS 작성 도구/YAML/JSON의 이스케이프를 중복 적용했습니다. 로봇의 Nav2/AMCL이나 QoS 문제로 진단하면 안 됩니다.

## 3. 최소 수정과 의사결정

- `A_HANDOFF.md`의 정확히 **한 명령 줄**만 올바른 한 겹 YAML escaping으로 바꿨습니다.
- `tests/test_smartdish_a_package.py`에 **실제 문서 줄을 읽어서** YAML → JSON 순으로 검사하는 회귀 테스트를 추가했습니다.
- Robot Adapter, Nav2, World, 기존 S7, 합격 게이트는 변경하지 않았습니다.

## 4. 재검 증거 및 판정

```bash
python3 -m pytest -q tests/test_smartdish_a_contract.py tests/test_smartdish_a_package.py
```

수정 전: 로컬 순수 Python 변환에서 `JSONDecodeError` 확인. 수정 후: [GitHub Actions #45119133312](https://github.com/silverbjin/samsung_AXI/actions/runs/45119133312), SHA `bae0c36bff32e50abd818711bca8c13737d835ec`: 새 문서 파싱 테스트 포함 `26 passed in 0.04s` **L0 PASS / RESOLVED**. 이 문제 때문에 실제 Gazebo L2를 불필요하게 반복하지 않습니다.

## 5. 교육 포인트

CLI 예제도 테스트 가능한 소스 코드입니다. 따옴표 오류는 실행 환경/ROS 네트워크에 진입하기 전에 YAML과 JSON의 **가장 좁은 변환 경계**를 검사하는 것이 빠릅니다. 이번 사례는 단순 문서 변경에도 재현용 단위 테스트가 유용한 이유를 보여줍니다.
