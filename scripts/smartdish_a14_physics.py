#!/usr/bin/env python3
"""A14 opt-in REAL Gazebo tray-relative physics evidence; NEVER human GT.

Only STATIC_GRAVITY can generate candidates. ROBOT_MOTION requires measured
time-aligned dynamic tray transforms and is HOLD by construction.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

PROFILE="STATIC_GRAVITY"
RULE="A14_DACON_CANDIDATE_V0_NONBINDING"
DA_CON_COMPARE_M=0.015  # reference candidate, NOT product threshold
MAX_POSE_GAP_NS=350_000_000  # accepts observed A13 0.23-0.29 s gaps
MAX_CAPTURE_SKEW_NS=250_000_000
FRAME_WORLD="world"
FRAME_TRAY="tray_platform/body"
CONTACT_PREFIX="/smartdish/tray/contact/"

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""): h.update(chunk)
    return h.hexdigest()

def write_json(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n")

def configure_sdf(sdf, config):
    """Opt-in contact sensors on tray, floor and EACH dynamic dish collision.

    Does not touch camera pose, AI OFF world or legacy A13 (disabled by default).
    """
    root=ET.parse(sdf).getroot()
    world=root.find("./world[@name='smartdish_tray']")
    if world is None: raise ValueError("A14_WORLD_MISSING")
    if world.find("./plugin[@name='gz::sim::systems::Contact']") is None:
        ET.SubElement(world,"plugin",filename="gz-sim-contact-system",
                      name="gz::sim::systems::Contact")
    names=["tray_platform","tray_test_floor"]+[x["name"] for x in config["initial_dishes"]]
    for model_name in names:
        model=world.find("./model[@name='%s']"%model_name)
        link=model.find("link") if model is not None else None
        collision=link.find("collision") if link is not None else None
        if collision is None: raise ValueError("A14_CONTACT_COLLISION_MISSING_"+model_name)
        name=collision.attrib["name"]
        if link.find("./sensor[@name='a14_contact']") is not None:
            raise ValueError("A14_DUPLICATE_CONTACT_SENSOR")
        sensor=ET.SubElement(link,"sensor",{"name":"a14_contact","type":"contact"})
        ET.SubElement(sensor,"always_on").text="true"
        ET.SubElement(sensor,"update_rate").text="50"
        ET.SubElement(sensor,"topic").text=CONTACT_PREFIX+model_name
        ET.SubElement(ET.SubElement(sensor,"contact"),"collision").text=name
    content='<?xml version="1.0"?>\n'+ET.tostring(root,encoding="unicode")+"\n"
    Path(sdf).write_text(content)
    config["world_sha256"]=hashlib.sha256(content.encode()).hexdigest()
    config["a14_profile"]=PROFILE
    config["a14_contact_topics"]=[CONTACT_PREFIX+n for n in names]
    config["a14_static_tray_pose_sdf"]="0 0 0.55 0 0 0"
    write_json(Path(sdf).with_suffix(".scenario.json"),config)
    bridge=[]
    for name in names:
        bridge.append({"ros_topic_name":CONTACT_PREFIX+name,
                       "gz_topic_name":CONTACT_PREFIX+name,
                       "ros_type_name":"ros_gz_interfaces/msg/Contacts",
                       "gz_type_name":"gz.msgs.Contacts",
                       "direction":"GZ_TO_ROS"})
    # A second bridge, scoped to A14 only, preserves original camera bridge.
    path=Path(sdf).with_name("a14_contact_bridge.yaml")
    import yaml
    path.write_text(yaml.safe_dump(bridge,sort_keys=False))
    layout={"schema":2,"physics_profile":PROFILE,"scene_id":config["scene_id"],
            "trial_id":config["trial_id"],"seed":config["seed"],
            "camera_configuration_unchanged":True,
            "static_tray_model":"tray_platform",
            "tray_frame_id":FRAME_TRAY,
            "world_frame_id":FRAME_WORLD,
            "geometry":{"tray_width_m":config["platform"]["width_m"],
                        "tray_depth_m":config["platform"]["depth_m"],
                        "tray_top_z_m":config["platform"]["top_z_m"]},
            "dishes":[{"name":d["name"],"radius_m":d["radius_m"],
                       "thickness_m":d["thickness_m"],"mass_kg":d["mass_kg"]}
                      for d in config["initial_dishes"]],
            "contact_bridge_config_sha256":digest(path),
            "world_sdf_sha256":config["world_sha256"],
            "layout_id_basis":"EXACT_SCENE_SDF_SHA_NOT_INDEPENDENT_GEOMETRY_FAMILY",
            "geometry_family_id":None,
            "physical_layout_id":None,
            "environment_profile_id":"STATIC_GRAVITY_GAZEBO_A14"}
    write_json(Path(sdf).with_name("geometry_layout.json"),layout)
    return {"topics":config["a14_contact_topics"],"bridge":str(path)}

def finite(*values):
    return all(isinstance(x,(float,int)) and math.isfinite(float(x)) for x in values)

def norm_q(q):
    if len(q)!=4 or not finite(*q):raise ValueError("A14_QUATERNION_NONFINITE")
    n=math.sqrt(sum(float(v)*float(v) for v in q))
    if not .98<=n<=1.02:raise ValueError("A14_QUATERNION_NOT_NORMALIZED")
    return tuple(float(v)/n for v in q)

def q_conjugate(q):return (-q[0],-q[1],-q[2],q[3])
def q_mul(a,b):
    x,y,z,w=a;X,Y,Z,W=b
    return (w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z)
def rotate(q,v):
    p=q_mul(q_mul(q,(v[0],v[1],v[2],0.0)),q_conjugate(q))
    return p[:3]
def transform_relative(tray,dish):
    """T_tray_dish = inverse(T_world_tray) * T_world_dish."""
    qt=norm_q([tray[k] for k in ("qx","qy","qz","qw")])
    qd=norm_q([dish[k] for k in ("qx","qy","qz","qw")])
    inv=q_conjugate(qt)
    translation=rotate(inv,tuple(dish[k]-tray[k] for k in ("x","y","z")))
    orientation=norm_q(q_mul(inv,qd))
    return {"translation_m":{"x":translation[0],"y":translation[1],"z":translation[2]},
            "quaternion":{"x":orientation[0],"y":orientation[1],
                          "z":orientation[2],"w":orientation[3]},
            "quaternion_norm":math.sqrt(sum(v*v for v in orientation))}

def static_tray_pose(sdf):
    root=ET.parse(sdf).getroot()
    model=root.find("./world/model[@name='tray_platform']")
    if model is None or model.findtext("static")!="true":
        raise ValueError("A14_STATIC_TRAY_UNVERIFIED")
    parts=[float(x) for x in model.findtext("pose","").split()]
    if len(parts)!=6 or not finite(*parts):raise ValueError("A14_TRAY_POSE_INVALID")
    x,y,z,roll,pitch,yaw=parts
    cr,sr=math.cos(roll/2),math.sin(roll/2)
    cp,sp=math.cos(pitch/2),math.sin(pitch/2)
    cy,sy=math.cos(yaw/2),math.sin(yaw/2)
    q=(sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,
       cr*cp*sy-sr*sp*cy,cr*cp*cy+sr*sp*sy)
    return {"x":x,"y":y,"z":z,"qx":q[0],"qy":q[1],"qz":q[2],"qw":q[3]}

def contact_category(a,b):
    a=str(a);b=str(b)
    dish1="dish_" in a;dish2="dish_" in b
    if dish1 and dish2:return "DISH_DISH"
    if (dish1 or dish2) and ("tray_platform" in a or "tray_platform" in b):
        return "TRAY_DISH"
    if (dish1 or dish2) and ("tray_test_floor" in a or "tray_test_floor" in b):
        return "FLOOR_DISH"
    return "OTHER"

def contact_messages_to_events(messages,topics):
    """Contact status is a sensor-evidence claim, never a guess from silence.

    A real EMPTY message can close a previously observed pair. A silent
    unobserved topic cannot assert NO_CONTACT or CONTACT_ENDED.
    """
    counts={t:0 for t in topics}
    hit_counts={t:0 for t in topics}
    last_t={t:None for t in topics}
    active={t:{} for t in topics}
    events=[];unreliable=0
    for row in sorted(messages,key=lambda z:(z.get("sim_time_ns",0),z.get("topic",""))):
        topic=row.get("topic")
        if topic not in counts:continue
        counts[topic]+=1
        t=row.get("sim_time_ns")
        if (not isinstance(t,int) or t<=0 or
            row.get("timestamp_source") not in ("ROS_CONTACT_HEADER_STAMP",None) or
            (last_t[topic] is not None and t<last_t[topic])):
            unreliable+=1
            continue
        last_t[topic]=t
        current={}
        for hit in row.get("contacts",[]):
            c1=str(hit.get("collision1",""));c2=str(hit.get("collision2",""))
            if not c1 or not c2:
                unreliable+=1
                continue
            pair=tuple(sorted((c1,c2)))
            current[pair]=(c1,c2)
            hit_counts[topic]+=1
        for pair,(c1,c2) in current.items():
            events.append({"sim_time_ns":t,"collision1":c1,"collision2":c2,
                           "category":contact_category(c1,c2),"topic":topic,
                           "source":"ROS_BRIDGED_GAZEBO_CONTACT_SENSOR",
                           "timestamp_source":row.get("timestamp_source"),
                           "event":"CONTACT_STARTED" if pair not in active[topic]
                                   else "CONTACT_OBSERVED"})
        for pair,(c1,c2) in active[topic].items():
            if pair not in current:
                # END requires another REAL, valid message on same sensor.
                events.append({"sim_time_ns":t,"collision1":c1,"collision2":c2,
                               "category":contact_category(c1,c2),"topic":topic,
                               "source":"ROS_BRIDGED_GAZEBO_CONTACT_SENSOR",
                               "timestamp_source":row.get("timestamp_source"),
                               "event":"CONTACT_ENDED"})
        active[topic]=current
    missing=sorted(t for t,v in counts.items() if v==0)
    started=[e for e in events if e["event"]=="CONTACT_STARTED"]
    status=("CONTACT_SENSOR_UNAVAILABLE" if sum(counts.values())==0 else
            "CONTACT_DATA_INCOMPLETE" if missing or unreliable else
            "CONTACT_OBSERVED" if started else "NO_CONTACT_OBSERVED")
    # Never manufacture a support-loss event from a missing contact topic.
    support_loss="UNDETERMINED"
    tray_end=[x for x in events if x["event"]=="CONTACT_ENDED" and
              x["category"]=="TRAY_DISH"]
    floor_start=[x for x in started if x["category"]=="FLOOR_DISH"]
    if any(e["sim_time_ns"]<=f["sim_time_ns"] and
           ("dish_" in e["collision1"] or "dish_" in e["collision2"])
           for e in tray_end for f in floor_start):
        support_loss="OBSERVED_TRAY_END_THEN_FLOOR_CONTACT"
    return {"status":status,"topic_callbacks":counts,"topic_contact_counts":hit_counts,
            "topic_unobserved":missing,
            "unreliable_stamp_or_collision_count":unreliable,"events":events,
            "heartbeat_coverage":"ALL_SENSOR_TOPICS" if not missing else "INCOMPLETE",
            "contact_end_coverage":"ONLY_EXPLICIT_SUBSEQUENT_SENSOR_MESSAGES",
            "support_loss":support_loss,
            "no_contact_inference_allowed":bool(not missing and not unreliable)}
def get_pose(row):
    pose=row["pose"]
    return {k:float(pose[k]) for k in ("x","y","z","qx","qy","qz","qw")}

def velocity_from(prev,cur,dt):
    if dt<=0:raise ValueError("A14_TIME_NONMONOTONIC")
    a=prev["translation_m"];b=cur["translation_m"]
    v={k:(b[k]-a[k])/dt for k in ("x","y","z")}
    qa=norm_q([prev["quaternion"][k] for k in ("x","y","z","w")])
    qb=norm_q([cur["quaternion"][k] for k in ("x","y","z","w")])
    dq=norm_q(q_mul(q_conjugate(qa),qb))
    if dq[3]<0:dq=tuple(-x for x in dq)
    axis=math.sqrt(sum(x*x for x in dq[:3]))
    angle=2*math.atan2(axis,abs(dq[3]))
    omega=(tuple((x/axis)*angle/dt for x in dq[:3])
           if axis>1e-12 else (0.,0.,0.))
    return {"linear_m_s":v,"angular_rad_s":dict(zip(("x","y","z"),omega)),
            "frame_id":FRAME_TRAY,"provenance":"DERIVED_POSE_FINITE_DIFFERENCE",
            "dt_seconds":dt}

def build_v2(directory,config,state,contact_topics,source_sha):
    """Analyze only measured ROS TF header-stamped traces and actual Contacts."""
    root=Path(directory)
    original=root/"physics_observations.jsonl"
    lines=[json.loads(x) for x in original.read_text().splitlines()]
    # Do not alter/rebuild the authenticated A11 camera. Copy SDF pose
    # configuration and hash as metadata; dynamic camera TF is NOT measured.
    world_sdf=root/"scenario.sdf"
    sensor=ET.parse(world_sdf).getroot().find(
        ".//model[@name='smartdish_tray_observer']//sensor[@type='camera']")
    if sensor is None:
        raise ValueError("A14_CAMERA_SDF_METADATA_MISSING")
    camera_meta={
        "schema":2,"source":"EXISTING_A11_GAZEBO_SDF_SENSOR_CONFIGURATION",
        "world_sdf_sha256":digest(world_sdf),
        "camera_frame_id":sensor.findtext("gz_frame_id"),
        "camera_topic":sensor.findtext("topic"),
        "camera_pose_configuration":sensor.findtext("pose"),
        "static_sensor_sdf_pose_present":bool(sensor.findtext("pose")),
        "dynamic_camera_tf_status":"NOT_MEASURED_STATIC_CONFIG_ONLY",
        "source_git_sha":source_sha,
    }
    write_json(root/"camera_pose_metadata.json",camera_meta)
    # Append-only A14 header-stamped source; legacy A13 clock-callback trace
    # is preserved separately and NEVER relabeled exact sensor-time evidence.
    raw=state.get("a14_poses",[])
    q_tray=static_tray_pose(root/"scenario.sdf")
    start_ns=int(state["a14_observation_start_ns"])
    end_ns=int(state["a14_observation_end_ns"])
    cap_ns=int(state["a14_capture_ns"])
    expected=[x["name"] for x in config["initial_dishes"]]
    tray_path=root/"tray_pose_timeline.jsonl"
    pose_path=root/"physics_observations_v2.jsonl"
    contact_path=root/"contact_events.jsonl"
    per={n:[] for n in expected}
    invalid_reasons=[]
    for row in raw:
        n=row.get("entity");t=row.get("sim_time_ns")
        if n not in per or not isinstance(t,int) or t<=0:continue
        try:relative=transform_relative(q_tray,get_pose(row))
        except (ValueError,KeyError) as exc:
            invalid_reasons.append(str(exc));continue
        per[n].append({"sim_time_ns":t,"entity":n,"pose":get_pose(row),
                       "relative":relative,"stamp_source":row.get("stamp_source")})
    trays=[]
    out=[]
    metrics={}
    for n,samples in per.items():
        samples.sort(key=lambda x:x["sim_time_ns"])
        prev=None
        total=0.;maxgap=0
        for record in samples:
            t=record["sim_time_ns"]
            if prev is not None:
                dt_ns=t-prev["sim_time_ns"]
                if dt_ns<=0:invalid_reasons.append("A14_TIME_REPEATED_"+n);continue
                maxgap=max(maxgap,dt_ns)
                a=prev["relative"]["translation_m"];b=record["relative"]["translation_m"]
                total+=math.sqrt(sum((b[k]-a[k])**2 for k in ("x","y","z")))
                velocity=velocity_from(prev["relative"],record["relative"],dt_ns/1e9)
            else: velocity={"provenance":"UNAVAILABLE_FIRST_SAMPLE","linear_m_s":None,
                            "angular_rad_s":None,"frame_id":FRAME_TRAY}
            trays.append({"sim_time_ns":t,"world_frame_id":FRAME_WORLD,
                          "tray_frame_id":FRAME_TRAY,"pose":q_tray,
                          "transform_mode":"STATIC_TRAY",
                          "source":"AUTHENTICATED_GAZEBO_WORLD_SDF_FIXED_MODEL",
                          "world_sdf_sha256":config["world_sha256"]})
            record.update({"world_frame_id":FRAME_WORLD,"tray_frame_id":FRAME_TRAY,
                           "dish_frame_id":n,"transform_source":"ROS_GZ_POSE_TF_HEADER",
                           "transform_mode":"DYNAMIC_DISH_VS_STATIC_TRAY",
                           "velocity":velocity,
                           "contact_status":"SEE_contact_events.jsonl",
                           "cumulative_tray_relative_path_m":total})
            out.append(record)
            prev=record
        if len(samples)<2:invalid_reasons.append("A14_POSE_TRACE_TOO_SHORT_"+n);continue
        first=samples[0];last=samples[-1]
        a=first["relative"]["translation_m"];b=last["relative"]["translation_m"]
        net=math.sqrt(sum((b[k]-a[k])**2 for k in ("x","y","z")))
        planar=math.hypot(b["x"]-a["x"],b["y"]-a["y"])
        if maxgap>MAX_POSE_GAP_NS:invalid_reasons.append("A14_POSE_GAP_"+n)
        if abs(first["sim_time_ns"]-cap_ns)>MAX_CAPTURE_SKEW_NS:
            invalid_reasons.append("A14_T0_POSE_NOT_ALIGNED_"+n)
        if last["sim_time_ns"]<end_ns-MAX_POSE_GAP_NS:
            invalid_reasons.append("A14_TRACE_TRUNCATED_"+n)
        qfirst=norm_q([first["relative"]["quaternion"][k] for k in ("x","y","z","w")])
        qlast=norm_q([last["relative"]["quaternion"][k] for k in ("x","y","z","w")])
        dq=norm_q(q_mul(q_conjugate(qfirst),qlast))
        tilt_change=2*math.acos(min(1.,abs(dq[3])))
        dz=a["z"]-b["z"]
        egress=(abs(b["x"])>float(config["platform"]["width_m"])/2 or
                abs(b["y"])>float(config["platform"]["depth_m"])/2)
        metrics[n]={"samples":len(samples),"max_sample_gap_ns":maxgap,
                    "relative_drop_m":dz,"relative_rotation_rad":tilt_change,
                    "relative_tray_egress":egress,
                    "cumulative_relative_distance_m":total,"net_relative_displacement_m":net,
                    "net_relative_planar_m":planar,
                    "first_sim_time_ns":first["sim_time_ns"],
                    "last_sim_time_ns":last["sim_time_ns"],
                    "final_center_below_tray":b["z"]<0.0,
                    "source":"TIME_STAMPED_REAL_POSE_BRIDGED_FROM_GAZEBO"}
    status=contact_messages_to_events(state.get("a14_contacts",[]),contact_topics)
    contact_path.write_text("".join(json.dumps(row,sort_keys=True)+"\n" for row in
                                    status["events"]))
    # Contact events may be empty: an explicit sensor-status record still exists.
    write_json(root/"contact_sensor_status.json",
               {k:v for k,v in status.items() if k!="events"})
    out.sort(key=lambda x:(x["sim_time_ns"],x["entity"]))
    # Annotate each dish frame with the most recent proven sensor event.
    # Unknown until the first matching real contact; no future label leakage.
    by_dish={n:[] for n in expected}
    for event in status["events"]:
        for n in expected:
            if n in event["collision1"] or n in event["collision2"]:
                by_dish[n].append(event)
    for record in out:
        past=[e for e in by_dish[record["entity"]] if
              e["sim_time_ns"]<=record["sim_time_ns"]]
        latest=past[-1] if past else None
        record["contact_status"]=(
            "CONTACT_OBSERVED" if latest and latest["event"]!="CONTACT_ENDED" else
            "NO_CONTACT_OBSERVED" if latest and latest["event"]=="CONTACT_ENDED"
            and status["no_contact_inference_allowed"] else
            "CONTACT_DATA_INCOMPLETE")
        record["contact_pair_source"]=(latest["topic"] if latest else None)
    pose_path.write_text("".join(json.dumps(row,sort_keys=True)+"\n" for row in out))
    trays.sort(key=lambda x:x["sim_time_ns"])
    tray_path.write_text("".join(json.dumps(row,sort_keys=True)+"\n" for row in trays))
    if end_ns-start_ns<9_000_000_000:invalid_reasons.append("A14_SHORT_OBSERVATION")
    if not raw:invalid_reasons.append("A14_TF_HEADER_POSES_MISSING")
    if any(x.get("stamp_source")!="ROS_TF_HEADER_STAMP" for x in out):
        invalid_reasons.append("A14_POSE_SOURCE_NOT_EXACT")
    if status["status"] in ("CONTACT_SENSOR_UNAVAILABLE","CONTACT_DATA_INCOMPLETE"):
        invalid_reasons.append("A14_CONTACT_NOT_VERIFIED")
    if state.get("a14_contact_overflow"):
        invalid_reasons.append("A14_CONTACT_BUFFER_OVERFLOW")
    observation=state.get("a14_observation","INDETERMINATE")
    if observation not in ("HELD_OBSERVED","FALL_OBSERVED","INDETERMINATE"):
        observation="INDETERMINATE"
    # 0.015m is a NONBINDING comparison field. No automatic GT approval.
    threshold_boundary=any(abs(d["cumulative_relative_distance_m"]-DA_CON_COMPARE_M)<.001
                           for d in metrics.values())
    if threshold_boundary:invalid_reasons.append("A14_NONBINDING_THRESHOLD_BOUNDARY")
    if state.get("a14_initial_collapse",False):
        invalid_reasons.append("A14_COLLAPSE_BEFORE_T0")
    if invalid_reasons or len(metrics)!=len(expected):
        suggested="UNKNOWN"
    else:
        falling=any(d["relative_drop_m"]>.12 or d["final_center_below_tray"]
                    for d in metrics.values())
        held=all(abs(d["relative_drop_m"])<.08 and not d["relative_tray_egress"]
                 for d in metrics.values())
        # Independent trace features must agree with legacy observed motion:
        # A13's label and the scenario hint alone cannot vote for A14 GT.
        suggested=("UNSTABLE" if falling and observation=="FALL_OBSERVED" else
                   "STABLE" if held and observation=="HELD_OBSERVED" else "UNKNOWN")
    # Sensor metric gate is independent from suggestion/label; UNKNOWN is normal.
    qa={"schema":2,"source_sha":source_sha,"original_a13_physics_sha256":digest(original),
        "camera_pose_metadata_sha256":digest(root/"camera_pose_metadata.json"),
        "scene_id":config["scene_id"],"stack_id":config["stack_id"],
        "trial_id":config["trial_id"],"seed":config["seed"],"physics_profile":PROFILE,
        "observation":observation,"rule_candidate":suggested,
        "rule_version":RULE,"comparison_threshold_m":DA_CON_COMPARE_M,
        "threshold_is_product_policy":False,
        "label_status":"REVIEW_REQUIRED","human_approved":False,
        "ground_truth":"NOT_OPERATOR_APPROVED",
        "observation_start_ns":start_ns,"observation_end_ns":end_ns,
        "rgb_t0_sim_time_ns":cap_ns,
        "rgb_topic":"/smartdish/tray/image_raw","rgb_image_sha256":digest(root/"tray_rgb.png"),
        "world_sdf_sha256":digest(root/"scenario.sdf"),
        "frame_contract":"world -> tray_platform/body -> dish_XX",
        "tray_pose_mode":"STATIC_TRAY","velocity_provenance":"DERIVED",
        "contact_status":status["status"],"contact_callback_counts":status["topic_callbacks"],
        "contact_event_count":len(status["events"]),
        "contact_end_support_loss":status["support_loss"],
        "contact_sensor_unobserved_topics":status["topic_unobserved"],
        "unsupported_dynamic_tray":"ROBOT_MOTION_REQUIRES_MEASURED_T_WORLD_TRAY",
        "measured_pose_source":"ROS_TF_HEADER_STAMP",
        "per_dish":metrics,"invalid_reasons":sorted(set(invalid_reasons)),
        "quality_verdict":"PASS" if not invalid_reasons else "HOLD",
        "evidence_sha256":{"tray_pose_timeline":digest(tray_path),
            "physics_observations_v2":digest(pose_path),
            "contact_events":digest(contact_path)}}
    write_json(root/"a14_gt_candidate.json",qa)
    return qa
