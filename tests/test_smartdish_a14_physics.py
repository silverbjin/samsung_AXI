"""A14 P0 offline physical evidence tests: never let a candidate approve GT."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_tray_world import write_trial
from smartdish_a14_physics import (
    configure_sdf,static_tray_pose,norm_q,q_mul,transform_relative,
    velocity_from,contact_category,contact_messages_to_events,build_v2,
    retain_contact_sample,
)

def scene(tmp_path,scene="ST-01"):
    sdf=tmp_path/"scenario.sdf"
    cfg=write_trial(scene,113,sdf,"A14_01")
    old=sdf.read_text()
    info=configure_sdf(sdf,cfg)
    assert old!=sdf.read_text()
    assert "gz-sim-contact-system" in sdf.read_text()
    assert len(info["topics"])==2+len(cfg["initial_dishes"])
    assert Path(info["bridge"]).exists()
    assert cfg["world_sha256"]==hashlib.sha256(sdf.read_bytes()).hexdigest()
    return sdf,cfg,info

def test_quaternion_inverse_rotated_tray_frame():
    tray={"x":1., "y":2.,"z":.5,"qx":0.,"qy":0.,
          "qz":2**-.5,"qw":2**-.5}
    dish={"x":1., "y":3.,"z":1.,"qx":0.,"qy":0.,"qz":0.,"qw":1.}
    p=transform_relative(tray,dish)
    assert p["translation_m"]["x"]==pytest.approx(1)
    assert p["translation_m"]["y"]==pytest.approx(0)
    assert p["translation_m"]["z"]==pytest.approx(.5)
    assert p["quaternion_norm"]==pytest.approx(1)
    with pytest.raises(ValueError,match="A14_QUATERNION_NOT_NORMALIZED"):
        norm_q((0,0,0,0))
    with pytest.raises(ValueError,match="A14_QUATERNION_NONFINITE"):
        norm_q((0,0,float("nan"),1))

def test_static_tray_is_sdf_authentic_and_contact_instrumentation_optin(tmp_path):
    sdf,cfg,info=scene(tmp_path)
    pose=static_tray_pose(sdf)
    assert pose["z"]==pytest.approx(.55)
    assert pose["qw"]==pytest.approx(1.)
    txt=sdf.read_text()
    assert "sensor name=\"a14_contact\"" in txt
    import xml.etree.ElementTree as ET
    parsed=ET.parse(sdf).getroot()
    sensors=parsed.findall(".//sensor[@type='contact']")
    assert len(sensors)==2+len(cfg["initial_dishes"])
    for sensor in sensors:
        assert sensor.find("topic") is None
        assert sensor.find("contact/topic") is not None
        assert sensor.findtext("contact/topic").startswith("/smartdish/tray/contact/")
    assert "smartdish_tray_rgb" in txt
    assert "/smartdish/tray/contact/tray_platform" in txt
    assert "ros_gz_interfaces/msg/Contacts" in Path(info["bridge"]).read_text()
    assert "CONTACT" not in (tmp_path/"tray_rgb.png").name
    # The unchanged legacy builder must stay without A14 sensors.
    from smartdish_tray_world import build_world
    import xml.etree.ElementTree as ET
    old, _=build_world("ST-01",113)
    assert old.find(".//sensor[@name='a14_contact']") is None

def test_contact_absence_vs_sensor_outage_and_collision_categories():
    topics=["/contact/tray","/contact/dish","/contact/floor"]
    assert contact_messages_to_events([],topics)["status"]=="CONTACT_SENSOR_UNAVAILABLE"
    partial=[{"topic":topics[0],"sim_time_ns":100,"contacts":[]}]
    assert contact_messages_to_events(partial,topics)["status"]=="CONTACT_DATA_INCOMPLETE"
    empty=[{"topic":t,"sim_time_ns":100,"contacts":[]} for t in topics]
    assert contact_messages_to_events(empty,topics)["status"]=="NO_CONTACT_OBSERVED"
    hit=[{"topic":t,"sim_time_ns":100,"contacts":[]} for t in topics]
    hit[0]["contacts"]=[{"collision1":"dish_01::body::collision",
                         "collision2":"tray_platform::body::collision"}]
    r=contact_messages_to_events(hit,topics)
    assert r["status"]=="CONTACT_OBSERVED"
    assert r["events"][0]["category"]=="TRAY_DISH"
    assert r["events"][0]["event"]=="CONTACT_STARTED"
    assert contact_category("dish_01::collision","dish_02::collision")=="DISH_DISH"
    assert contact_category("dish_01::collision","tray_test_floor::collision")=="FLOOR_DISH"
    hit[0]["sim_time_ns"]=0
    assert contact_messages_to_events(hit,topics)["status"]=="CONTACT_DATA_INCOMPLETE"
    # A real explicit empty heartbeat can CLOSE a previously active contact.
    hit[0]["sim_time_ns"]=100
    follow={"topic":topics[0],"sim_time_ns":200,"contacts":[]}
    ends=contact_messages_to_events(hit+[follow],topics)
    assert "CONTACT_ENDED" in [e["event"] for e in ends["events"]]

def test_velocity_provenance_units_and_nonmonotonic_guard():
    a={"translation_m":{"x":0,"y":0,"z":0},
       "quaternion":{"x":0,"y":0,"z":0,"w":1}}
    b={"translation_m":{"x":.2,"y":0,"z":0},
       "quaternion":{"x":0,"y":0,"z":0,"w":1}}
    x=velocity_from(a,b,.2)
    assert x["linear_m_s"]["x"]==pytest.approx(1.)
    assert x["angular_rad_s"]["z"]==pytest.approx(0.)
    assert x["provenance"]=="DERIVED_POSE_FINITE_DIFFERENCE"
    with pytest.raises(ValueError,match="A14_TIME_NONMONOTONIC"):
        velocity_from(a,b,0)

def fixtures(tmp_path,observation="HELD_OBSERVED",drop=False,empty=False,
             poses_gap_ns=200_000_000):
    sdf,cfg,info=scene(tmp_path)
    (tmp_path/"tray_rgb.png").write_bytes(b"real_png_test_fixture_not_sensor_capture")
    (tmp_path/"physics_observations.jsonl").write_text(
        '{"sim_ns":600000000,"entity":"dish_01","pose":{"x":0}}\n')
    raw=[];topics=info["topics"]
    end=10_600_000_000
    for name in [d["name"] for d in cfg["initial_dishes"]]:
        for i,t in enumerate(range(600_000_000,10_800_000_001,poses_gap_ns)):
            z=.65-(.8*(i*poses_gap_ns/(10_000_000_000))) if drop else .65
            raw.append({"entity":name,"sim_time_ns":t,
                "stamp_source":"ROS_TF_HEADER_STAMP",
                "pose":{"x":0.,"y":0.,"z":z,
                        "qx":0.,"qy":0.,"qz":0.,"qw":1.}})
    contacts=[{"topic":t,"sim_time_ns":600_000_000,"contacts":[]} for t in topics]
    if not empty:
        contacts[0]["contacts"]=[{"collision1":"dish_01::body::collision",
            "collision2":"tray_platform::body::collision"}]
    state={"a14_poses":raw,"a14_contacts":contacts,
           "a14_observation_start_ns":600_000_000,
           "a14_observation_end_ns":end,"a14_capture_ns":600_000_000,
           "a14_observation":observation,"a14_initial_collapse":False}
    return cfg,info,state

def test_real_schema_with_synthetic_stable_fixture_is_review_only(tmp_path):
    cfg,info,state=fixtures(tmp_path)
    qa=build_v2(tmp_path,cfg,state,info["topics"],"a"*40)
    assert qa["rule_candidate"]=="STABLE"
    assert qa["quality_verdict"]=="PASS"
    assert qa["label_status"]=="REVIEW_REQUIRED"
    assert qa["human_approved"] is False
    assert qa["ground_truth"]=="NOT_OPERATOR_APPROVED"
    assert qa["comparison_threshold_m"]==.015
    assert qa["threshold_is_product_policy"] is False
    assert qa["contact_status"]=="CONTACT_OBSERVED"
    assert qa["per_dish"]["dish_01"]["max_sample_gap_ns"]==200_000_000
    rows=[json.loads(x) for x in
          (tmp_path/"physics_observations_v2.jsonl").read_text().splitlines()]
    assert rows[0]["velocity"]["provenance"]=="UNAVAILABLE_FIRST_SAMPLE"
    assert rows[2]["velocity"]["provenance"]=="DERIVED_POSE_FINITE_DIFFERENCE"
    assert rows[0]["tray_frame_id"]=="tray_platform/body"
    camera=json.loads((tmp_path/"camera_pose_metadata.json").read_text())
    assert camera["world_sdf_sha256"]==hashlib.sha256((tmp_path/"scenario.sdf").read_bytes()).hexdigest()
    assert camera["static_sensor_sdf_pose_present"] is True
    assert camera["dynamic_camera_tf_status"]=="NOT_MEASURED_STATIC_CONFIG_ONLY"
    assert qa["camera_pose_metadata_sha256"]==hashlib.sha256(
        (tmp_path/"camera_pose_metadata.json").read_bytes()).hexdigest()
    assert (tmp_path/"tray_pose_timeline.jsonl").is_file()
    assert (tmp_path/"contact_sensor_status.json").is_file()
    assert not (tmp_path/"approval_ledger.jsonl").exists()

def test_unstable_and_unknown_always_review_required(tmp_path):
    cfg,info,state=fixtures(tmp_path,observation="FALL_OBSERVED",drop=True)
    qa=build_v2(tmp_path,cfg,state,info["topics"],"b"*40)
    assert qa["rule_candidate"]=="UNSTABLE"
    assert qa["human_approved"] is False
    # simulated sample loss induces hold instead of assuming valid.
    state["a14_poses"]=[x for x in state["a14_poses"]
                       if x["sim_time_ns"]<1_000_000_000 or x["sim_time_ns"]>1_800_000_000]
    qa=build_v2(tmp_path,cfg,state,info["topics"],"b"*40)
    assert qa["quality_verdict"]=="HOLD"
    assert qa["rule_candidate"]=="UNKNOWN"
    assert any("A14_POSE_GAP" in x for x in qa["invalid_reasons"])

def test_missing_contact_or_preexisting_collapse_no_gt(tmp_path):
    cfg,info,state=fixtures(tmp_path,empty=True)
    state["a14_contacts"]=[]
    state["a14_initial_collapse"]=True
    qa=build_v2(tmp_path,cfg,state,info["topics"],"c"*40)
    assert qa["quality_verdict"]=="HOLD"
    assert qa["rule_candidate"]=="UNKNOWN"
    assert not qa["human_approved"]
    assert "A14_CONTACT_NOT_VERIFIED" in qa["invalid_reasons"]
    assert "A14_COLLAPSE_BEFORE_T0" in qa["invalid_reasons"]
    assert not (tmp_path/"approval_ledger.jsonl").exists()

def test_only_optin_run_keeps_a13_trusted_pipeline():
    live=(ROOT/"scripts/smartdish_a_tray_live.py").read_text()
    assert "args.a14_static" in live
    assert "configure_sdf(sdf,config)" in live
    assert "build_v2(directory,config,state" in live
    assert "a14_contact_cb" in live
    assert "A13_REAL_CAMERA_BRIDGE_WARMUP_NO_TWO_IMAGES" in live
    assert "A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED" in live
    assert 'ground_truth":"NOT_OPERATOR_APPROVED"' in live
    assert 'approval_ledger.jsonl' not in live


def test_high_rate_contact_stream_preserves_real_edges_and_reduces_redundancy():
    state={"a14_contacts":[],"a14_contact_overflow":False}
    topic="/smartdish/tray/contact/dish_01"
    pair={"collision1":"dish_01::body::collision",
          "collision2":"tray_platform::body::collision",
          "collision1_id":11,"collision2_id":22}
    for i in range(25_000):
        state_contacts=([pair] if 2_000<=i<18_000 else [])
        retain_contact_sample(state,{
            "topic":topic,"sim_time_ns":i*500_000+1,
            "timestamp_source":"ROS_CONTACT_HEADER_STAMP",
            "contacts":state_contacts},interval_ns=50_000_000)
    assert state["a14_contact_raw_callback_total"]==25_000
    assert state["a14_contact_redundant_suppressed"]>20_000
    assert len(state["a14_contacts"])<1_000
    assert not state["a14_contact_overflow"]
    events=contact_messages_to_events(state["a14_contacts"],[topic])["events"]
    assert [e["event"] for e in events].count("CONTACT_STARTED")==1
    assert [e["event"] for e in events].count("CONTACT_ENDED")==1
    starts=[e for e in events if e["event"]=="CONTACT_STARTED"]
    assert starts[0]["collision1_id"]==11
    assert starts[0]["collision2_id"]==22
    # It must still FAIL on an artificially tiny evidence buffer.
    tiny={"a14_contacts":[],"a14_contact_overflow":False}
    retain_contact_sample(tiny,{"topic":topic,"sim_time_ns":1,"contacts":[]},
                          interval_ns=0,limit=1)
    retain_contact_sample(tiny,{"topic":topic,"sim_time_ns":2,"contacts":[]},
                          interval_ns=0,limit=1)
    assert tiny["a14_contact_overflow"] is True
