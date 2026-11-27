"""E-only L0 fixtures; no live ROS or Gazebo evidence."""
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_e_product_boundary import OwnerMailbox, accepted_hook, verify_ready
from smartdish_e_product_nav2 import screen_map, apply_product_footprint, prepare
from PIL import Image
import yaml

def test_actual_map_static_screen_not_motion():
    data=screen_map(ROOT/"maps/restaurant_map.yaml",ROOT/"src/smartdish_robot/config/table_poses.yaml")
    assert data["width"]==201 and data["height"]==180
    assert not data["all_connected"] and not data["motion_authorized"]
    assert data["static_gate"]=="HOLD_UNKNOWN_OR_CLEARANCE"
    assert data["map_classes"]=={"free":24811,"unknown":9781,"occupied":1588}
    assert all(x["path_exists"] for x in data["occupied_only_diagnostic"]["legs"])
    assert not any(x["path_exists"] for x in data["legs"])
    assert data["screening_radius_m"]>.44

def test_footprint_preserve_cm_chain_and_expand():
    p={n:{n:{"ros__parameters":{"robot_radius":.22}}} for n in ("local_costmap","global_costmap")}
    p["collision_monitor"]={"ros__parameters":{"cmd_vel_in_topic":"cmd_vel_smoothed","cmd_vel_out_topic":"cmd_vel",
        "polygons":["S4ForwardStop","FootprintApproach"],"S4ForwardStop":{"action_type":"stop","enabled":True,"min_points":4}}}
    apply_product_footprint(p)
    assert "robot_radius" not in p["global_costmap"]["global_costmap"]["ros__parameters"]
    assert json.loads(p["local_costmap"]["local_costmap"]["ros__parameters"]["footprint"])[2]==[.28,.28]
    assert p["collision_monitor"]["ros__parameters"]["S4ForwardStop"]["min_points"]==4

def test_ready_bytes_and_scope(tmp_path):
    # Fixture only; no actual startup claim.
    scene=dict(scenario="stacked",run_id="test",stack_id="test:T03",world_sha256="a"*64)
    raw=dict(kind="ACTUAL_STARTUP_ENTITY_AND_STOP",source_sha="b"*40,run_id="test",world_sha256="a"*64,
             observation=dict(stack_id="test:T03",robot_entity_id=1,fixture_entity_id=2,table_count=3,tray_count=0))
    path=tmp_path/"ready.json";path.write_text(json.dumps(raw))
    receipt=raw|{"receipt_sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    assert verify_ready(receipt,path,scene,"b"*40)=="test:T03"
    with pytest.raises(RuntimeError,match="DIGEST"):verify_ready(receipt|{"receipt_sha256":"0"*64},path,scene,"b"*40)
    with pytest.raises(RuntimeError,match="PROVENANCE"):verify_ready(receipt,path,scene,"c"*40)

def test_mailbox_serialized_hook_and_late_timeout():
    mailbox=OwnerMailbox()
    out=[]
    def call():out.append(mailbox.call(threading.get_ident))
    thread=threading.Thread(target=call);thread.start()
    until=time.monotonic()+1
    while thread.is_alive() and time.monotonic()<until:
        mailbox.drain();thread.join(.01)
    assert out==[threading.get_ident()]
    # No owner drain: timed out job must not be executed later.
    effects=[]
    with pytest.raises(RuntimeError,match="D_HOOK_TIMEOUT"):mailbox.call(effects.append,1,timeout=.01)
    mailbox.drain()
    assert not effects
    mailbox.close()
    with pytest.raises(RuntimeError,match="CLOSED"):mailbox.call(effects.append,2)


def test_unknown_class_blocks_and_free_fixture_connects(tmp_path):
    pgm=tmp_path/"map.pgm"
    config=tmp_path/"map.yaml"
    poses=tmp_path/"poses.yaml"
    config.write_text(yaml.safe_dump(dict(image="map.pgm",mode="trinary",negate=0,
        origin=[0,0,0],resolution=.05,free_thresh=.196,occupied_thresh=.65)))
    poses.write_text(yaml.safe_dump(dict(frame="map",poses={
        "HOME":{"x":1,"y":1},"T03":{"x":2,"y":1},"DISH_RETURN":{"x":2,"y":2}})))
    Image.new("L",(80,80),254).save(pgm)
    assert screen_map(config,poses)["all_connected"]
    Image.new("L",(80,80),205).save(pgm)
    result=screen_map(config,poses)
    assert result["map_classes"]["unknown"]==6400
    assert not result["all_connected"] and not result["motion_authorized"]

def test_actual_map_hold_refuses_overlay_and_preserves_receipt(tmp_path):
    source=tmp_path/"source.yaml"
    source.write_text("untouched\n")
    output=tmp_path/"out.yaml"
    receipt=tmp_path/"screen.json"
    with pytest.raises(RuntimeError,match="PRODUCT_STATIC_CLEARANCE_FAILED"):
        prepare(source,output,ROOT/"maps/restaurant_map.yaml",
                ROOT/"src/smartdish_robot/config/table_poses.yaml",receipt)
    assert not output.exists()
    assert source.read_text()=="untouched\n"
    assert json.loads(receipt.read_text())["static_gate"]=="HOLD_UNKNOWN_OR_CLEARANCE"
