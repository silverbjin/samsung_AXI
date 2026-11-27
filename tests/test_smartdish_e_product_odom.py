"""L0 fixtures only. No actual robot assertion."""
import sys,json,hashlib
from pathlib import Path
from types import SimpleNamespace as N
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_e_product_odom import RawOdomTrace,audit,sha,LEGS

PIN="a"*40
def message(stamp,v=0.):
    xyz=lambda x=0.:N(x=x,y=0.,z=0.)
    return N(header=N(stamp=N(sec=stamp//10**9,nanosec=stamp%10**9),frame_id="odom"),
        child_frame_id="base_footprint",twist=N(twist=N(linear=xyz(v),angular=xyz())),
        pose=N(pose=N(position=xyz(),orientation=N(x=0.,y=0.,z=0.,w=1.))))

def make(root,mode="ok"):
    trace=RawOdomTrace(root,PIN,"test")
    for i,leg in enumerate(LEGS):
        t=10+i*20
        body=dict(request_id="mission",leg=leg,goal_uuid=str(i+1)*32)
        trace.nav("accepted",body,t-1,{})
        trace.nav("terminal",body,t,dict(terminal_status="SUCCEEDED"))
        for j in range(13):
            if mode=="gap" and i==1 and 3<=j<=7:continue
            v=.03 if mode=="motion" and i==1 and j==8 else 0.
            trace.odom(message((t*10+j)*100_000_000,v),t+j/10)
        trace.nav("stop_verified",body,t+1.21,dict(terminal_status="SUCCEEDED"))
    trace.close()

def test_all_three_raw_dwells(tmp_path):
    make(tmp_path)
    r=audit(tmp_path,PIN,"test")
    assert len(r["legs"])==3 and all(x["continuous_stop_s"]>=1 for x in r["legs"])
@pytest.mark.parametrize("mode",["gap","motion"])
def test_missing_or_moving_tail_fails(tmp_path,mode):
    make(tmp_path,mode)
    with pytest.raises(ValueError,match="CONTINUOUS_NOT_PROVEN"):audit(tmp_path,PIN,"test")
def test_tamper_and_mixed_session(tmp_path):
    make(tmp_path)
    with pytest.raises(ValueError,match="SESSION"):audit(tmp_path,PIN,"wrong")
    p=tmp_path/"odom_full.jsonl";p.write_text(p.read_text()+"\n")
    with pytest.raises(ValueError,match="TRACE_SHA"):audit(tmp_path,PIN,"test")
def test_duplicate_cannot_renew(tmp_path):
    make(tmp_path)
    p=tmp_path/"odom_full.jsonl";rs=[json.loads(x) for x in p.read_text().splitlines()]
    for r in rs[3:13]:
        r.update(sim_ns=rs[2]["sim_ns"],duplicate=True)
    p.write_text("".join(json.dumps(r)+"\n" for r in rs))
    m=tmp_path/"odom_manifest.json";d=json.loads(m.read_text());d["odom_sha256"]=sha(p);m.write_text(json.dumps(d))
    with pytest.raises(ValueError,match="CONTINUOUS_NOT_PROVEN"):audit(tmp_path,PIN,"test")
