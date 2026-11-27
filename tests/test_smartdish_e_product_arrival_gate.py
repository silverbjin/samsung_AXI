"""L0 simulated futures only: no claim of actual Nav2."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src/smartdish_robot"))
from smartdish_robot.product_navigation import NavigationBoundary
from smartdish_robot.product_contract import PROFILE

class Future:
    def __init__(self,v):self.v=v
    def done(self):return True
    def result(self):return self.v

class Fake:
    def __init__(self,wait=True):
        self.now=0.;self.ready=False;self.events=[];self.results=[];self.cancel=[]
        self.stop=NS(start=0.,last_at=0.,dwell=1.3,verified=lambda _:True)
        handle=NS(accepted=True,goal_id=NS(uuid=bytes(range(1,17))),get_result_async=lambda:Future(NS(status=4)))
        client=NS(server_is_ready=lambda:True,send_goal_async=lambda _:Future(handle))
        self.nav=NavigationBoundary(client,lambda _:object(),self.stop,lambda *a:True,self.results.append,
            self.cancel.append,clock=lambda:self.now,preflight=lambda:True,arrival_verified=lambda _:self.ready,
            wait_arrival_within_stop_deadline=wait)
        self.nav.evidence_hook=lambda kind,body,t,extra:self.events.append((kind,t,body["goal_uuid"]))
        self.nav.start(dict(schema_version=2,profile=PROFILE,request_id="test",leg="TO_HOME",destination_id="HOME"))
        self.nav.tick()
    def tick(self,t,ready):
        self.now=t;self.ready=ready;self.stop.last_at=t;self.nav.tick()

def test_real_terminal_waits_for_fresh_arrival_not_new_goal():
    f=Fake();f.tick(1.4,False)
    assert f.nav.active is not None and not f.results and len(f.events)==2
    f.tick(2.6,True)
    assert f.results[0]["result"]=="SUCCEEDED" and f.nav.active is None
    assert [x[0] for x in f.events]==["accepted","terminal","stop_verified"]
    assert len({x[2] for x in f.events})==1 and f.nav.last_receipt["stop_steady_s"]==2.6

def test_arrival_not_verified_at_original_deadline_fails_even_if_now_fresh():
    f=Fake();f.tick(1.4,False);f.tick(3.,True)
    assert f.results[0]["result"]=="FAILED" and f.results[0]["reason"]=="NAV_ARRIVAL_UNVERIFIED"
    assert f.nav.active is None and f.nav.locked and f.nav.last_receipt is None
    assert f.results[0]["terminal_status"]=="SUCCEEDED" and f.results[0]["stop_verified"]

def test_stop_gap_during_arrival_wait_does_not_qualify():
    f=Fake();f.tick(1.4,False);f.stop.start=1.5;f.tick(2.,True)
    assert not f.results
    f.stop.start=2.8;f.tick(3.,True)
    assert f.results[0]["result"]=="FAILED" and not f.results[0]["stop_verified"]

def test_default_keeps_immediate_failure():
    f=Fake(False);f.tick(1.4,False)
    assert f.results[0]["result"]=="FAILED" and f.nav.locked
