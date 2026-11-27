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
from smartdish_e_product_nav2 import screen_map, apply_product_footprint

def test_actual_map_static_screen_not_motion():
    data=screen_map(ROOT/"maps/restaurant_map.yaml",ROOT/"src/smartdish_robot/config/table_poses.yaml")
    assert data["width"]==201 and data["height"]==180
    assert data["all_connected"] and not data["motion_authorized"]
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
