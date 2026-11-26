import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from a14_physics_freshness_contract import evaluate, STEP
TOPICS=["tray","floor"]
def fixture(diag=False):
    return [dict(sim_ns=i*STEP,iteration=i,dt_ns=STEP,topic=t,sensor_id=j+1,
                 collision_id=j+10,present=True,armed=True,
                 post_state="ONE_TIME" if diag and i==2 else "NO_CHANGE",
                 late_control=diag and i==2)
            for i in range(1,5) for j,t in enumerate(TOPICS)]
def check(rows,diag=False):
    return evaluate(rows,TOPICS,0,4*STEP,diagnostic=diag)
def test_zero_contact_refresh_is_not_gt():
    r=check(fixture())
    assert r["refresh_contract_pass"] and r["production_contact_health"]=="HOLD"
    assert r["rule_candidate"]=="UNKNOWN" and not r["human_approved"]
def test_negative_late_control():
    assert check(fixture(True),True)["refresh_contract_pass"]
@pytest.mark.parametrize("field,value",[("armed",False),("present",False),("dt_ns",2*STEP),
                                        ("sensor_id",99),("collision_id",0),("iteration",99),
                                        ("post_state","ONE_TIME"),("late_control",True)])
def test_bad_row(field,value):
    r=fixture();r[2][field]=value
    assert not check(r)["refresh_contract_pass"]
def test_negative_must_survive():
    r=fixture(True);r[2]["post_state"]="NO_CHANGE"
    assert not check(r,True)["refresh_contract_pass"]
def test_missing_control():
    assert not check(fixture(),True)["refresh_contract_pass"]
def test_missing_duplicate():
    r=fixture()
    assert not check(r[1:])["refresh_contract_pass"]
    assert not check(r+[r[-1]])["refresh_contract_pass"]
