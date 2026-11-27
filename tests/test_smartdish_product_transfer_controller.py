"""L0 controller fixtures; these temporary receipts are NOT actual runtime evidence."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_robot"))
from smartdish_robot.product_transfer import ProductTransferController
from smartdish_robot.product_contract import PROFILE,ContractError

LOAD=dict(schema_version=2,profile=PROFILE,request_id="fixture",stack_id="fixture:T03",
          transfer_id="load-1",operation="LOAD",destination_id="T03")
UNLOAD=dict(LOAD,transfer_id="unload-1",operation="UNLOAD",destination_id="DISH_RETURN")
class FixturePhysics:
    def __init__(self,clock):
        self.guard=lambda:None;self.clock=[100];self.calls=[];self.t=clock;self.delay=0
    def initial_observation(self,services,scene):
        return {"robot_entity_id":1,"fixture_entity_id":2,"table_count":3,"tray_count":0}
    def wait_stop(self):self.guard()
    def load(self,out,scene,services,fixture):
        self.calls.append("LOAD")
        assert fixture==2
        (services.root/"gazebo_service_calls.jsonl").write_text("L0 FIXTURE ONLY")
        self.t[0]+=self.delay;self.guard()
        return {"entity_ids":[11,12,13],"event_sim_ns":100},self.delay
    def unload(self,services,ids):
        self.calls.append("UNLOAD")
        (services.root/"gazebo_service_calls.jsonl").write_text("L0 FIXTURE ONLY")
        self.t[0]+=self.delay;self.guard()
        return {"removed_entity_ids":ids,"event_sim_ns":200},self.delay
def arrival(dest,when,uuid):
    return {"request_id":"fixture","destination_id":dest,"goal_uuid":uuid,
            "terminal_status":"SUCCEEDED","stop_verified":True,"stop_steady_s":when}
def make(tmp_path):
    now=[10.];nav=NS(active=None,locked=False,last_receipt=None)
    physics=FixturePhysics(now)
    ctl=ProductTransferController(nav,physics,{"run_id":"fixture","stack_id":"fixture:T03",
        "world_sha256":"a"*64,"scenario":"stacked"},tmp_path,tmp_path/"evidence","b"*40,
        clock=lambda:now[0])
    ctl.arm_verified()
    nav.last_receipt=arrival("T03",0.,"1"*32)
    ctl.note_arrival()
    return ctl,nav,physics,now
def test_load_unload_exact_once_and_id_preservation(tmp_path):
    ctl,nav,phy,now=make(tmp_path)
    assert not ctl.can_start_leg(dict(LOAD,leg="TO_RETURN"))
    a=ctl.run(LOAD)
    assert a["status"]=="ACK" and a["entity_ids"]==["11","12","13"]
    assert ctl.run(LOAD)==a and phy.calls==["LOAD"]
    assert ctl.can_start_leg(dict(LOAD,leg="TO_RETURN"))
    nav.last_receipt=arrival("DISH_RETURN",10.,"2"*32)
    now[0]=15.;ctl.note_arrival()
    b=ctl.run(UNLOAD)
    assert b["status"]=="ACK" and b["entity_ids"]==a["entity_ids"]
    assert b["tray_count"]==0 and phy.calls==["LOAD","UNLOAD"]
    assert ctl.run(UNLOAD)==b
    assert ctl.can_start_leg(dict(LOAD,leg="TO_HOME"))
def test_before_wait_no_mutation_and_lock(tmp_path):
    ctl,nav,phy,now=make(tmp_path)
    now[0]=9.
    a=ctl.run(LOAD)
    assert a["status"]=="FAILED" and "TRANSFER_BEFORE_WAIT" in a["reason"]
    assert phy.calls==[] and ctl.locked and ctl.journal.locked
    assert not ctl.can_start_leg(dict(LOAD,leg="TO_RETURN"))
def test_deadline_after_partial_effect_no_ack(tmp_path):
    ctl,nav,phy,now=make(tmp_path)
    phy.delay=6.
    a=ctl.run(LOAD)
    assert a["status"]=="FAILED" and "TRANSFER_DEADLINE" in a["reason"]
    assert phy.calls==["LOAD"] and ctl.locked and ctl.journal.locked
    with pytest.raises(ContractError):ctl.run(LOAD)
def test_active_nav_no_mutation(tmp_path):
    ctl,nav,phy,now=make(tmp_path)
    nav.active=object()
    a=ctl.run(LOAD)
    assert a["status"]=="FAILED" and phy.calls==[]
