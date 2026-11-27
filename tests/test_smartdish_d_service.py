"""Contract tests for D service. All Nav2 results here are MOCK_ONLY."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "smartdish_service"))
from smartdish_service.mission_manager import MissionManager


class Clock:
    def __init__(self):
        self.t = 100.0
    def __call__(self):
        return self.t
    def add(self, seconds):
        self.t += seconds


def request(rid="REQ-1", ai=False, wait=10, dropoff=5):
    return {"request_id": rid, "table_id": "T03", "table_wait_s": wait,
            "dropoff_wait_s": dropoff, "ai_enabled": ai}


def result(rid, leg, outcome="SUCCEEDED", reason=""):
    return {"request_id": rid, "leg": leg, "result": outcome, "reason": reason}


def goals(events):
    return [v for topic, v in events if topic == "/collection/nav_goal"]


def test_ai_off_three_legs_exactly_wait_10_and_5():
    clk = Clock()
    m = MissionManager(clock=clk)
    assert m.handle_request(request())
    assert goals(m.drain()) == [
        {"request_id": "REQ-1", "leg": "TO_TABLE", "destination_id": "T03"}]
    m.tick()
    assert m.state == "TO_TABLE"
    assert m.on_nav_result(result("REQ-1", "TO_TABLE"))
    assert m.state == "WAIT_LOADING"
    assert m._remaining() == 10
    m.drain()
    clk.add(9.9)
    m.tick()
    assert not goals(m.drain())
    clk.add(0.1)
    m.tick()
    assert m.state == "TO_RETURN"
    assert goals(m.drain())[0]["destination_id"] == "DISH_RETURN"
    assert m.on_nav_result(result("REQ-1", "TO_RETURN"))
    assert m._remaining() == 5
    m.drain()
    clk.add(5)
    m.tick()
    assert goals(m.drain()) == [
        {"request_id": "REQ-1", "leg": "TO_HOME", "destination_id": "HOME"}]
    assert m.on_nav_result(result("REQ-1", "TO_HOME"))
    assert m.state == "COMPLETED"
    assert not goals(m.drain())


def test_old_or_wrong_leg_and_duplicate_are_ignored():
    m = MissionManager(clock=Clock())
    m.handle_request(request())
    m.drain()
    assert not m.on_nav_result(result("OLD", "TO_TABLE"))
    assert not m.on_nav_result(result("REQ-1", "TO_RETURN"))
    assert not m.on_nav_result(result("REQ-1", "TO_TABLE", "INVALID"))
    assert m.state == "TO_TABLE"
    assert not goals(m.drain())
    assert not m.handle_request(request())
    statuses = [x for t, x in m.drain() if t == "/collection/status"]
    assert statuses[-1]["reason"] == "BUSY"
    assert m.state == "TO_TABLE"


@pytest.mark.parametrize("bad", [
    {"table_id": "T02"}, {"table_wait_s": 0},
    {"table_wait_s": 121}, {"dropoff_wait_s": 61},
    {"ai_enabled": "false"}, {"request_id": ""},
    {"table_wait_s": True}, {"request_id": " REQ-1 "},
])
def test_invalid_request_fails_closed(bad):
    m = MissionManager(clock=Clock())
    body = request()
    body.update(bad)
    assert not m.handle_request(body)
    assert m.state == "IDLE"
    assert not goals(m.drain())


@pytest.mark.parametrize("outcome,expected", [
    ("FAILED", "ERROR"), ("CANCELED", "CANCELED")
])
def test_failed_or_canceled_nav_never_advances(outcome, expected):
    clk = Clock()
    m = MissionManager(clock=clk)
    m.handle_request(request())
    m.drain()
    assert m.on_nav_result(result("REQ-1", "TO_TABLE", outcome, "NAV2_TEST_ERROR"))
    clk.add(200)
    m.tick()
    assert m.state == expected
    assert not goals(m.drain())


def test_ai_off_no_inference_required_or_published():
    clk = Clock()
    m = MissionManager(clock=clk, ai_available=False)
    m.handle_request(request())
    m.drain()
    m.on_nav_result(result("REQ-1", "TO_TABLE"))
    m.drain()
    clk.add(10)
    m.tick()
    assert all(t != "/collection/ai_check_request" for t, _ in m.drain())


def test_ai_on_unstable_requires_matching_staff_approval():
    clk = Clock()
    m = MissionManager(clock=clk, ai_available=True)
    assert m.handle_request(request(ai=True))
    m.drain()
    m.on_nav_result(result("REQ-1", "TO_TABLE"))
    m.drain()
    clk.add(10)
    m.tick()
    events = m.drain()
    capture = next(v["capture_id"] for t, v in events if t == "/collection/ai_check_request")
    assert m.state == "AI_CHECK"
    assert not m.on_stability({"request_id": "REQ-1", "capture_id": "OLD", "status": "STABLE", "confidence": 0.9, "model_version": "fixture-v1"})
    assert m.on_stability({"request_id": "REQ-1", "capture_id": capture, "status": "UNSTABLE", "confidence": 0.6, "model_version": "fixture-v1"})
    assert m.state == "NEEDS_CONFIRMATION"
    assert not m.on_staff_confirm({"request_id": "OLD", "action": "APPROVE_CONTINUE"})
    assert not goals(m.drain())
    assert m.on_staff_confirm({"request_id": "REQ-1", "action": "APPROVE_CONTINUE"})
    assert goals(m.drain())[0]["destination_id"] == "DISH_RETURN"


def test_ai_timeout_and_abort_never_publish_next_goal():
    clk = Clock()
    m = MissionManager(clock=clk, ai_available=True)
    m.handle_request(request(ai=True))
    m.drain()
    m.on_nav_result(result("REQ-1", "TO_TABLE"))
    m.drain()
    clk.add(10)
    m.tick()
    m.drain()
    clk.add(5)
    m.tick()
    assert m.state == "NEEDS_CONFIRMATION"
    assert m.reason == "AI_TIMEOUT"
    m.drain()
    assert m.on_staff_confirm({"request_id": "REQ-1", "action": "ABORT"})
    assert m.state == "CANCELED"
    assert not goals(m.drain())


def test_stale_ai_and_new_mission_after_completion():
    clk = Clock()
    m = MissionManager(clock=clk, ai_available=True,
                       approved_model_sha256="a"*64)
    assert not m.handle_request(request(ai=True)) is False
    m.drain()
    assert not m.on_stability({"request_id":"REQ-1", "capture_id":"x", "status":"STABLE", "confidence":0.9, "model_version":"fixture-v1"})
    m.on_nav_result(result("REQ-1","TO_TABLE"))
    clk.add(10);m.tick()
    capture = m.capture_id
    m.drain()
    assert m.on_stability({"request_id":"REQ-1", "capture_id":capture, "status":"STABLE", "confidence":0.9, "model_version":"resnet18-aaaaaaaaaaaa"})
    m.drain()
    m.on_nav_result(result("REQ-1","TO_RETURN"))
    clk.add(5);m.tick()
    m.drain()
    m.on_nav_result(result("REQ-1","TO_HOME"))
    assert m.state == "COMPLETED"
    assert m.handle_request(request("REQ-2"))
    assert m.state == "TO_TABLE"
    assert not m.on_nav_result(result("REQ-1","TO_TABLE"))
    assert not m.handle_request(request("REQ-1"))


def test_ai_stable_without_provenance_never_advances():
    clk = Clock()
    m = MissionManager(clock=clk, ai_available=True)
    assert m.handle_request(request(ai=True))
    m.drain()
    m.on_nav_result(result("REQ-1", "TO_TABLE"))
    clk.add(10)
    m.tick()
    capture = m.capture_id
    m.drain()
    assert not m.on_stability({"request_id": "REQ-1", "capture_id": capture,
                              "status": "STABLE"})
    assert not m.on_stability({"request_id": "REQ-1", "capture_id": capture,
                              "status": "STABLE", "confidence": None,
                              "model_version": "none"})
    assert m.state == "AI_CHECK"
    assert not goals(m.drain())
    clk.add(5)
    m.tick()
    assert m.state == "NEEDS_CONFIRMATION"
    assert not goals(m.drain())
