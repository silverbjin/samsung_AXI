"""User-authorized OWNER v1 Gazebo mode; synthetic callbacks, NO_NAV2."""
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src/smartdish_service"),str(ROOT/"src/smartdish_ai")]
from smartdish_service import product_admission as auth
from smartdish_service.mission_manager import MissionManager

class Clock:
    t=10.0
    def __call__(self): return self.t

def prep(conf=.81):
    clock=Clock()
    m=MissionManager(clock=clock,ai_available=True,
        approved_model_sha256=auth.E_OWNER_GAZEBO_MODEL_SHA256,
        owner_manual_confirm_ai=True)
    assert m.handle_request(dict(request_id="R",table_id="T03",
        table_wait_s=10,dropoff_wait_s=5,ai_enabled=True))
    m.drain()
    assert m.on_nav_result(dict(request_id="R",leg="TO_TABLE",result="SUCCEEDED"))
    m.drain();clock.t+=10;m.tick()
    events=m.drain()
    cap=next(v["capture_id"] for k,v in events if k=="/collection/ai_check_request")
    return m,clock,cap

def test_owner_scope_requires_explicit_optin_and_static_pin():
    assert auth.product_ai_on_authorized(True) is False
    assert auth.product_ai_on_authorized(False,owner_gazebo_integration=True) is False
    assert auth.product_ai_on_authorized(True,owner_gazebo_integration=True) is True
    assert auth.approved_model_sha256() is None
    assert auth.approved_model_sha256(owner_gazebo_integration=True)==auth.E_OWNER_GAZEBO_MODEL_SHA256

def test_owner_scope_ignore_environment_forgery(monkeypatch):
    monkeypatch.setenv("SMARTDISH_E_OWNER_APPROVED","true")
    assert auth.product_ai_on_authorized(True) is False
    assert auth.E_APPROVED_PRODUCT_RELEASE_SHA256 is None

def test_owner_scope_requires_same_C_pin(monkeypatch):
    monkeypatch.setattr(auth,"E_OWNER_GAZEBO_MODEL_SHA256","0"*64)
    assert not auth.product_ai_on_authorized(True,owner_gazebo_integration=True)

@pytest.mark.parametrize("status,conf",[
    ("STABLE",.99),("STABLE",.80),("UNSTABLE",.96),("UNKNOWN",None)])
def test_owner_ai_result_never_auto_goal_without_staff(status,conf):
    m,clock,cap=prep()
    version="resnet18-"+auth.E_OWNER_GAZEBO_MODEL_SHA256[:12] if status=="STABLE" else "none"
    assert m.on_stability(dict(request_id="R",capture_id=cap,status=status,
                               confidence=conf,model_version=version))
    assert m.state=="NEEDS_CONFIRMATION"
    assert [v for k,v in m.drain() if k=="/collection/nav_goal"]==[]
    assert m.on_staff_confirm(dict(request_id="R",action="APPROVE_CONTINUE"))
    assert m.state=="TO_RETURN"
    assert len([v for k,v in m.drain() if k=="/collection/nav_goal"])==1
    assert not m.on_staff_confirm(dict(request_id="R",action="APPROVE_CONTINUE"))
    assert not m.drain()

def test_owner_stable_before_gate_or_wrong_sha_no_goal():
    m,clock,cap=prep()
    assert not m.on_stability(dict(request_id="R",capture_id=cap,status="STABLE",
                                   confidence=.99,model_version="resnet18-fake"))
    assert m.state=="AI_CHECK"
    assert not m.drain()

def test_owner_stable_after_5sec_timeout_needs_staff():
    m,clock,cap=prep();clock.t+=5.0
    assert not m.on_stability(dict(request_id="R",capture_id=cap,status="STABLE",
        confidence=.99,model_version="resnet18-"+auth.E_OWNER_GAZEBO_MODEL_SHA256[:12]))
    assert m.state=="NEEDS_CONFIRMATION"
    assert m.reason=="AI_TIMEOUT"
    assert not [e for e in m.drain() if e[0]=="/collection/nav_goal"]

def test_owner_abort_no_nav_goal():
    m,clock,cap=prep()
    assert m.on_stability(dict(request_id="R",capture_id=cap,status="UNKNOWN",
                               confidence=None,model_version="none"))
    m.drain()
    assert m.on_staff_confirm(dict(request_id="R",action="ABORT"))
    assert m.state=="CANCELED"
    assert not [e for e in m.drain() if e[0]=="/collection/nav_goal"]
