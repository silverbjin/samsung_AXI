"""L0 action-handle fixtures; no actual Nav2 or motion claim."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_robot"))
from smartdish_robot.product_navigation import NavigationBoundary
from smartdish_robot.product_contract import PROFILE,StopMonitor,ContractError
from smartdish_robot.product_runtime import make_product_runtime

REQ=dict(schema_version=2,profile=PROFILE,request_id="mission",leg="TO_TABLE",destination_id="T03")
class Future:
    def __init__(self,v=None):self.v=v
    def done(self):return self.v is not None
    def result(self):return self.v
class Handle:
    accepted=True
    goal_id=NS(uuid=list(range(1,17)))
    def __init__(self):self.r=Future();self.c=Future();self.cancel_n=0
    def get_result_async(self):return self.r
    def cancel_goal_async(self):self.cancel_n+=1;return self.c
class Client:
    def __init__(self):self.f=Future()
    def server_is_ready(self):return True
    def send_goal_async(self,g):return self.f
def make():
    c=Client();h=Handle();s=StopMonitor();now=[0.];events=[]
    n=NavigationBoundary(c,lambda x:x,s,lambda *a:events.append(("accepted",a)) or True,
        lambda d:events.append(("result",d)),lambda d:events.append(("cancel",d)),
        clock=lambda:now[0],timeout=3.,preflight=lambda:True,arrival_verified=lambda _:True)
    return n,c,h,s,now,events
def settle(n,s,now):
    for i in range(1,13):
        now[0]=round(now[0]+.1,6);s.observe(int(now[0]*1e9),now[0],0.,0.);n.tick()
def test_actual_handle_and_postterminal_stop():
    n,c,h,s,now,e=make();n.start(REQ);c.f.v=h;n.tick()
    assert e[0][1][-1]==bytes(h.goal_id.uuid).hex()
    h.r.v=NS(status=4);n.tick()
    assert n.active is not None and n.last_receipt is None
    settle(n,s,now)
    assert n.last_receipt["stop_verified"] and n.last_receipt["goal_uuid"]==bytes(h.goal_id.uuid).hex()
    assert e[-1][1]["result"]=="SUCCEEDED"
    with pytest.raises(ContractError):n.start(REQ)
def test_late_accept_exact_cancel_and_no_success():
    n,c,h,s,now,e=make();n.start(REQ);now[0]=4.;n.tick()
    assert n.locked and n.active is not None
    c.f.v=h;n.tick()
    assert h.cancel_n==1 and not e
    with pytest.raises(ContractError):n.cancel(dict(REQ,goal_uuid="f"*32))
    h.c.v=NS(goals_canceling=[NS(goal_id=h.goal_id)])
    h.r.v=NS(status=5);n.tick();settle(n,s,now)
    assert n.locked and n.last_receipt is None
    assert e[-1][0]=="cancel" and e[-1][1]["terminal_status"]=="CANCELED"
def test_product_runtime_default_disabled():
    with pytest.raises(ContractError,match="APPROVAL"):
        make_product_runtime(poses=None,scene=None,world_dir=None,evidence_dir=None,source_sha=None,
                             accepted_hook=None,cm_active=None)
