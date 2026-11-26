import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from a14_r02_production_collect import cross_check,expected_sensors,instrument_runtime
import xml.etree.ElementTree as ET
import hashlib,json
def test_metadata_only_runtime(tmp_path):
    runtime=tmp_path/"sensor_preflight.sdf";runtime.write_text('<sdf><world name="test"><model name="tray"/></world></sdf>')
    plugin=tmp_path/"plugin.so";plugin.write_bytes(b"fixture")
    original=ET.tostring(ET.parse(runtime).getroot())
    manifest={}
    instrument_runtime(runtime,manifest,plugin,tmp_path)
    root=ET.parse(runtime).getroot();w=root.find("./world")
    p=w.find("plugin");assert p.findtext("late_control")=="false"
    w.remove(p);assert ET.tostring(root)==original
    assert manifest["sensor_preflight_sha256"]==hashlib.sha256(runtime.read_bytes()).hexdigest()
def test_same_stamp_pair_and_silent_channel():
    expected={"tray":{"model":"tray","sensor":"a14_contact","collision":"c"},
              "floor":{"model":"floor","sensor":"a14_contact","collision":"c"}}
    rows=[dict(topic=t,sim_ns=2,**v,present=True,collision_id=10+i,
               pairs=[[10,20]] if i==0 else [],count=1 if i==0 else 0)
          for i,(t,v) in enumerate(expected.items())]
    raw=[dict(topic="tray",sim_time_ns=2,timestamp_source="ROS_CONTACT_HEADER_STAMP",
              contacts=[dict(collision1_id=10,collision2_id=20)])]
    ok,stats=cross_check(expected,rows,raw,1,2)
    assert ok and stats["floor"]["empty_steps"]==1 and stats["floor"]["matched_positive_steps"]==0
    raw[0]["sim_time_ns"]=3
    assert not cross_check(expected,rows,raw,1,2)[0]
    rows[0]["model"]="wrong"
    with pytest.raises(ValueError): cross_check(expected,rows,raw,1,2)
