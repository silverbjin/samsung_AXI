"""Focused wait heartbeat and raw continuity tests; no actual evidence claim."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_e_product_qa_adapter import wait_review

def make():
    rows=[];events=[]
    for state,op,duration,start in (("WAIT_LOADING","LOAD",10,10),("WAIT_UNLOADING","UNLOAD",5,40)):
        for i in range(duration*10+2):
            rows.append(dict(steady_ns=start*10**9-100_000_000+i*100_000_000,duplicate=False,linear=[0.,0.,0.],angular=[0.,0.,0.]))
        for i in range(duration*5):
            events.append(dict(topic="/collection/status",steady_ns=start*10**9+i*200_000_000,body=dict(request_id="rid",state=state)))
        end=(start+duration)*10**9
        events.append(dict(topic="/collection/status",steady_ns=end,body=dict(request_id="rid",state="LOADING" if op=="LOAD" else "UNLOADING")))
        events.append(dict(topic="/collection/dish_transfer_request",steady_ns=end,body=dict(request_id="rid",operation=op)))
    return rows,events

def test_repeat_status_not_new_wait():
    rows,events=make()
    result=wait_review(rows,events,"rid")
    assert [r["wait_s"] for r in result]==[10,5]
    assert [r["status_heartbeats"] for r in result]==[50,25]
def test_odom_gap_and_motion_are_not_hidden():
    rows,events=make()
    with pytest.raises(ValueError,match="CONTINUITY"):wait_review([r for r in rows if not 11*10**9<=r["steady_ns"]<=12*10**9],events,"rid")
    rows[10]["angular"]=[0,0,.03]
    with pytest.raises(ValueError,match="CONTINUITY"):wait_review(rows,events,"rid")
