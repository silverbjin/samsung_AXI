"""D-AION-01~03 RED specification; synthetic-only, never actual AI ON or Nav2."""
from pathlib import Path
import os
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src/smartdish_service"), str(ROOT/"src/smartdish_ai")]
from smartdish_service.mission_manager import MissionManager

class Clock:
    def __init__(self):
        self.t = 100.0
    def __call__(self):
        return self.t
    def add(self, seconds):
        self.t += seconds

def request(ai=True, rid="REQ-AION-TEST"):
    return {"request_id":rid, "table_id":"T03", "table_wait_s":10,
            "dropoff_wait_s":5, "ai_enabled":ai}

def go(m, clock, rid="REQ-AION-TEST"):
    assert m.handle_request(request(rid=rid))
    m.drain()
    assert m.on_nav_result({"request_id":rid,"leg":"TO_TABLE","result":"SUCCEEDED"})
    m.drain()
    clock.add(10)
    m.tick()
    events = m.drain()
    cap = next(v["capture_id"] for k,v in events if k=="/collection/ai_check_request")
    assert m.state=="AI_CHECK"
    assert not [v for k,v in events if k=="/collection/nav_goal"]
    return cap

def goals(m):
    return [v for k,v in m.drain() if k=="/collection/nav_goal"]

def stability(cap, status="STABLE", confidence=0.99, version="fake-model", rid="REQ-AION-TEST"):
    return dict(request_id=rid,capture_id=cap,status=status,
                confidence=confidence,model_version=version)

def test_D_AION_01_product_gate_denies_unapproved_cli_and_environment(monkeypatch):
    from smartdish_service import product_admission as p
    assert p.E_APPROVED_PRODUCT_RELEASE_SHA256 is None
    assert p.E_APPROVED_MODEL_SHA256 is None
    monkeypatch.setenv("E_AI_ON_GO","true")
    monkeypatch.setenv("SMARTDISH_APPROVED_MODEL_SHA256","a"*64)
    assert p.product_ai_on_authorized(False) is False
    assert p.product_ai_on_authorized(True) is False
    assert p.approved_model_sha256() is None

def test_D_AION_01_manager_and_ui_both_call_product_gate():
    manager = (ROOT/"src/smartdish_service/smartdish_service/manager_node.py").read_text()
    ui = (ROOT/"src/smartdish_service/smartdish_service/ui_app.py").read_text()
    assert "product_ai_on_authorized" in manager
    assert "product_ai_on_authorized" in ui
    assert "AI_ON_PRODUCT_NOT_AUTHORIZED" in manager

def test_D_AION_01_ai_enabled_request_first_goal_denied_without_receipt():
    m=MissionManager(ai_available=False)
    assert not m.handle_request(request())
    assert m.state=="IDLE"
    events=m.drain()
    assert not any(k=="/collection/nav_goal" for k,_ in events)
    assert any(v.get("reason")=="AI_NOT_AVAILABLE" for k,v in events if k=="/collection/status")

def test_D_AION_02_forged_STABLE_does_not_trigger_return_goal():
    clock=Clock();m=MissionManager(clock=clock,ai_available=True)
    cap=go(m,clock)
    assert not m.on_stability(stability(cap,confidence=0.99,version="fake-model"))
    assert m.state=="AI_CHECK"
    assert not goals(m)

@pytest.mark.parametrize("conf", [None,0.0,0.1,0.799999,float("nan"),float("inf"),True])
def test_D_AION_02_low_or_invalid_confidence_never_autoadvances(conf):
    clock=Clock();m=MissionManager(clock=clock,ai_available=True,
        approved_model_sha256="a"*64)
    cap=go(m,clock)
    assert not m.on_stability(stability(cap,confidence=conf,version="resnet18-aaaaaaaaaaaa"))
    assert m.state=="AI_CHECK"
    assert not goals(m)

def test_D_AION_02_fixture_approved_model_with_080_confidence_is_contract_only():
    clock=Clock();m=MissionManager(clock=clock,ai_available=True,
        approved_model_sha256="a"*64)
    cap=go(m,clock)
    assert m.on_stability(stability(cap,confidence=0.80,version="resnet18-aaaaaaaaaaaa"))
    assert m.state=="TO_RETURN"
    assert goals(m)==[{"request_id":"REQ-AION-TEST",
                       "leg":"TO_RETURN","destination_id":"DISH_RETURN"}]

def test_D_AION_02_expired_STABLE_must_not_beat_timer():
    clock=Clock();m=MissionManager(clock=clock,ai_available=True,
        approved_model_sha256="a"*64)
    cap=go(m,clock);clock.add(5.1)
    assert not m.on_stability(stability(cap,confidence=0.99,version="resnet18-aaaaaaaaaaaa"))
    assert m.state=="NEEDS_CONFIRMATION"
    assert m.reason=="AI_TIMEOUT"
    assert not goals(m)

def test_D_AION_02_wrong_capture_or_request_no_return_goal():
    clock=Clock();m=MissionManager(clock=clock,ai_available=True,
        approved_model_sha256="a"*64)
    cap=go(m,clock)
    assert not m.on_stability(stability("WRONG",version="resnet18-aaaaaaaaaaaa"))
    assert not m.on_stability(stability(cap,rid="OLD",version="resnet18-aaaaaaaaaaaa"))
    assert m.state=="AI_CHECK" and not goals(m)

@pytest.mark.parametrize("reason",["UNKNOWN","UNSTABLE"])
def test_D_AION_03_manual_confirmation_boundary(reason):
    clock=Clock();m=MissionManager(clock=clock,ai_available=True)
    cap=go(m,clock)
    assert m.on_stability(stability(cap,status=reason,confidence=None,version="none"))
    assert m.state=="NEEDS_CONFIRMATION"
    assert not goals(m)
    assert not m.on_staff_confirm({"request_id":"OLD","action":"APPROVE_CONTINUE"})
    assert not goals(m)
    assert m.on_staff_confirm({"request_id":"REQ-AION-TEST","action":"APPROVE_CONTINUE"})
    assert m.state=="TO_RETURN"
    assert len(goals(m))==1
    assert not m.on_staff_confirm({"request_id":"REQ-AION-TEST","action":"APPROVE_CONTINUE"})
    assert not goals(m)

def test_D_AION_03_abort_does_not_publish_goal():
    clock=Clock();m=MissionManager(clock=clock,ai_available=True)
    cap=go(m,clock)
    assert m.on_stability(stability(cap,status="UNKNOWN",confidence=None,version="none"))
    m.drain()
    assert m.on_staff_confirm({"request_id":"REQ-AION-TEST","action":"ABORT"})
    assert m.state=="CANCELED" and not goals(m)
    assert not m.on_staff_confirm({"request_id":"REQ-AION-TEST","action":"APPROVE_CONTINUE"})
    assert not goals(m)

def test_D_AION_03_timeout_remains_manual_only():
    clock=Clock();m=MissionManager(clock=clock,ai_available=True)
    go(m,clock);clock.add(5)
    m.tick()
    assert m.state=="NEEDS_CONFIRMATION" and m.reason=="AI_TIMEOUT"
    assert not goals(m)

def test_D_AION_04_C_model_less_unknown_and_duplicate_suppression():
    from smartdish_ai.inference_core import InferenceCore
    import json
    c=InferenceCore()
    req=json.dumps({"request_id":"REQ-AION-TEST","capture_id":"REQ-AION-TEST-AI-1"})
    assert c.handle_request(req)=={
       "request_id":"REQ-AION-TEST","capture_id":"REQ-AION-TEST-AI-1",
       "status":"UNKNOWN","confidence":None,"model_version":"none"}
    assert c.handle_request(req) is None

def test_D_AION_04_C17_source_remains_unapproved():
    from smartdish_ai.model_runtime import PRODUCT_APPROVED_CHECKPOINT_SHA256
    assert PRODUCT_APPROVED_CHECKPOINT_SHA256 is None
    assert not list((ROOT/"src").glob("**/*.pt"))
