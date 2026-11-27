"""A-PROD capture store fixture tests; no Nav2 or physical claims."""
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_robot"))
from smartdish_robot.product_contract import (
    PROFILE, FrameCache, TransactionJournal, ContractError, digest,
)
from smartdish_robot.product_capture import CaptureStore

REQ=dict(schema_version=2,profile=PROFILE,request_id="fixture-mission",
         stack_id="fixture:T03",transfer_id="fixture-load",capture_id="fixture-cap",
         min_sim_stamp_ns=100)

class FixtureLoad:
    """Deliberately test-only journal dependency, never product runtime."""
    def load_receipt(self,request_id,stack_id,transfer_id):
        assert (request_id,stack_id,transfer_id)==tuple(REQ[k] for k in ("request_id","stack_id","transfer_id"))
        return {"event_sim_ns":100,"receipt_sha256":"a"*64},{"kind":"L0_FIXTURE"}

def sample(stamp=101,received=1.):
    cache=FrameCache()
    raw=bytes([22,33,44])*(640*480)
    cache.observe(stamp,"smartdish_tray_optical",640,480,"rgb8",1920,raw,received)
    return cache.select(stamp-1,received)

def test_capture_ack_and_exact_duplicate(tmp_path):
    store=CaptureStore(tmp_path,FixtureLoad())
    assert store.reserve(REQ) is None
    frame=sample()
    result=store.complete(REQ,frame,1.1)
    assert result["status"]=="ACK" and result["rgb_sha256"]==digest(frame.rgb)
    assert result["image_stamp_ns"]==101
    assert store.reserve(REQ)==result
    with pytest.raises(ContractError):store.reserve(dict(REQ,capture_id="second"))
    d=next(tmp_path.iterdir())
    (d/"frame.rgb").write_bytes(b"bad")
    with pytest.raises(ContractError):store.reserve(REQ)

def test_stale_preload_and_failure_no_image(tmp_path):
    store=CaptureStore(tmp_path,FixtureLoad())
    with pytest.raises(ContractError):store.reserve(dict(REQ,min_sim_stamp_ns=99))
    store.reserve(REQ)
    for f,now in [(sample(100),1.1),(sample(101),3.1)]:
        with pytest.raises(ContractError):store.complete(REQ,f,now)
    result=store.fail(REQ,"CAMERA_TIMEOUT")
    assert result["status"]=="FAILED" and result["rgb_sha256"] is None
    assert store.reserve(REQ)==result
    assert not list(tmp_path.glob("*/frame.png"))

def test_production_requires_actual_load_receipt(tmp_path):
    j=TransactionJournal(tmp_path/"transfers")
    req={k:v for k,v in REQ.items() if k not in ("capture_id","min_sim_stamp_ns")}
    req.update(operation="LOAD",destination_id="T03")
    j.begin(req)
    result={k:req[k] for k in ("schema_version","profile","request_id","stack_id","transfer_id","operation")}
    result.update(status="ACK",reason="",entity_ids=[1,2,3],location="ON_ROBOT",
                  tray_count=3,table_count=0,event_sim_ns=100)
    j.finish(req,result,{"kind":"L0_FIXTURE_NOT_ACTUAL"})
    with pytest.raises(ContractError,match="LOAD_RECEIPT_SCOPE"):
        CaptureStore(tmp_path/"capture",j).reserve(REQ)
