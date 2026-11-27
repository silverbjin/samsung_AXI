"""L0 bounded no-send gate; actual ROS proof belongs to L2."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src/smartdish_robot"))
from smartdish_robot.product_goal_gate import DeferredGoal

REQ=dict(request_id="r",leg="TO_HOME",destination_id="HOME")
def test_post_unload_recovery_exactly_one_dispatch():
    gate=DeferredGoal(5.)
    assert gate.submit(REQ,10.)
    assert not gate.submit(REQ,11.)
    assert gate.deadline==15.
    assert gate.poll(11.,allowed=lambda:True,ready=lambda:False)=="WAIT"
    assert gate.poll(12.,allowed=lambda:True,ready=lambda:True)=="SEND"
    assert gate.poll(12.1,allowed=lambda:True,ready=lambda:True)=="EMPTY"
def test_expiry_cannot_send_even_if_ready():
    gate=DeferredGoal(5.);gate.submit(REQ,10.)
    assert gate.poll(15.,allowed=lambda:True,ready=lambda:True)=="EXPIRED"
    assert gate.request is None
def test_closed_request_cannot_send():
    gate=DeferredGoal(5.);gate.submit(REQ,10.)
    assert gate.poll(11.,allowed=lambda:False,ready=lambda:True)=="CLOSED"
    assert gate.request is None
def test_conflict_never_replaces_pending():
    gate=DeferredGoal(5.);gate.submit(REQ,10.)
    with pytest.raises(ValueError,match="CONFLICT"):gate.submit(REQ|{"request_id":"other"},11.)
    assert gate.request==REQ and gate.deadline==15.
def test_default_disabled_and_invalid_budget():
    with pytest.raises(ValueError,match="DISABLED"):DeferredGoal(0.).submit(REQ,1.)
    for value in (6.,-1.,True,float("nan")):
        with pytest.raises(ValueError,match="BUDGET"):DeferredGoal(value)
