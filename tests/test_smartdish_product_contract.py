"""A-PROD-03 pure safety contract tests. Fixture data never means actual Gazebo PASS."""
import hashlib
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_robot"))
from smartdish_robot.product_contract import (
    PROFILE, ContractError, parse_transfer, parse_capture, canonical_rgb,
    FrameCache, StopMonitor, TransactionJournal, verify_transfer_observation,
)

COMMON={"schema_version":2,"profile":PROFILE,"request_id":"mission","stack_id":"run:T03","transfer_id":"load-1"}
LOAD=dict(COMMON,operation="LOAD",destination_id="T03")
CAP=dict(COMMON,capture_id="capture-1",min_sim_stamp_ns=100)

def test_schema_and_ids_fail_closed():
    assert parse_transfer(json.dumps(LOAD))==LOAD
    assert parse_capture(json.dumps(CAP))==CAP
    for bad in (dict(LOAD,profile="legacy"),dict(LOAD,schema_version=True),dict(LOAD,operation="UNLOAD"),dict(LOAD,stack_id=""),dict(LOAD,transfer_id="x"*129)):
        with pytest.raises(ContractError):parse_transfer(json.dumps(bad))
    for bad in (dict(CAP,min_sim_stamp_ns=True),dict(CAP,min_sim_stamp_ns=-1),dict(CAP,min_sim_stamp_ns=float("nan"))):
        with pytest.raises(ContractError):parse_capture(json.dumps(bad))

def test_packed_rgb_stride_and_bgr():
    row=bytes([4,3,2])*640+bytes([99,99])
    data=row*480
    out=canonical_rgb(640,480,"bgr8",1922,data)
    assert out==bytes([2,3,4])*(640*480)
    with pytest.raises(ContractError):canonical_rgb(640,480,"rgb8",1922,data[:-1])

def test_capture_strict_post_load_and_staleness():
    c=FrameCache()
    data=bytes([1,2,3])*(640*480)
    c.observe(100,"smartdish_tray_optical",640,480,"rgb8",1920,data,1.0)
    assert c.select(100,1.1) is None
    c.observe(101,"smartdish_tray_optical",640,480,"rgb8",1920,data,1.2)
    f=c.select(100,1.3)
    assert f.stamp_ns==101 and f.rgb_sha256==hashlib.sha256(data).hexdigest()
    assert c.select(100,3.21) is None
    with pytest.raises(ContractError):c.observe(99,"smartdish_tray_optical",640,480,"rgb8",1920,data,3.22)
    with pytest.raises(ContractError):c.select(100,3.23)

def test_stop_dwell_and_gap():
    s=StopMonitor()
    for i in range(6):
        s.observe(100+i,1+i*.2,0.,0.)
    assert s.verified(2.1)
    assert not s.verified(2.4)
    s.observe(107,2.5,.02,0.)
    assert not s.verified(2.5)
    with pytest.raises(ContractError):s.observe(99,2.6,0.,0.)

def test_transaction_journal_idempotency_and_crash_lock(tmp_path):
    j=TransactionJournal(tmp_path)
    assert j.begin(LOAD) is None
    assert j.locked
    with pytest.raises(ContractError):TransactionJournal(tmp_path).begin(LOAD)
    j.finish(LOAD,dict(COMMON,operation="LOAD",status="ACK",reason="",entity_ids=[11,12,13],location="ON_ROBOT",tray_count=3,table_count=0,event_sim_ns=123))
    same=TransactionJournal(tmp_path)
    assert same.begin(LOAD)["status"]=="ACK"
    with pytest.raises(ContractError):same.begin(dict(LOAD,request_id="different"))

def test_transfer_observation_requires_real_counts_and_samples():
    observation={"stack_id":"run:T03","location":"ON_ROBOT","entity_ids":[11,12,13],"table_count":0,"tray_count":3,"event_sim_ns":200,
                 "samples":[{"sim_ns":100+i*500_000_000,"entity_ids":[11,12,13],"relative_xy_m":[0.,0.,0.],"relative_z_error_m":[0.,0.,0.],"relative_speed_mps":[0.,0.,0.]} for i in range(3)]}
    observation["event_sim_ns"]=observation["samples"][-1]["sim_ns"]
    assert verify_transfer_observation(LOAD,observation,3)
    for bad in (dict(observation,tray_count=2),dict(observation,entity_ids=[11,11,12]),dict(observation,samples=[]),dict(observation,table_count=1)):
        with pytest.raises(ContractError):verify_transfer_observation(LOAD,bad,3)
