"""B-QA04: independent A16 Owner schema v2 audit. Review only, never train."""
from __future__ import annotations
import csv,hashlib,io,json,math,re,tarfile
from pathlib import PurePosixPath
from collections import defaultdict,Counter
import xml.etree.ElementTree as ET
from PIL import Image
from audit_b_a15 import (QAError,sha,json_bytes,verify_sidecar,relative,norm_q,angle,rotate,q_inv,xyz,pair,ahash,read_contact,read_trigger,validate_sdf,STEP_NS,T0_NS,END_NS,TRIGGER_NS,PULSE_STEPS,TORQUE_NM,PLATFORM_SHA,audit_owner as audit_a15,read_tar as read_a15_tar,OWNER_SHA as A15_OWNER_SHA,INNER_SHA as A15_INNER_SHA)
PIN="bacc1af4b47b6d1b2d4eb43b2d0223f578d1244e"
OWNER="ec3eac2a4af99f0deefa67a44254ea1b07a9fef1ee80cd4a715156105cbb4f15"
DIAG="61cd76bfedd5f3908444e6d6f1bfe9296f5e2a175c0428310812047e26566a65"
SCENES=tuple(f"L16-{i:02d}" for i in range(1,9))
INNER=dict(zip(SCENES,[
"bbfc454756694ec419529287ab8221290642eb07cbfc1eb56d8a82f9a69945f0","3e0af448b77e2499a69f4e1497b257adaaf28541ca270a891ddcb704f453a449","5e864809300b9cf50ea8e7286c750bfd2a53a5ee51d221b3b4f1607d57622a85","f32be47d21094f396dbc9119a49a0751262309c616bc980309f8ebb444839142","beb2a593ff791d8b44cea3dae31ee020fe297920734e08681b89108a9188546c","2aa246c68c428e4ce0d2ce3236994c81f471bb41408e815ac87e78c23fb52a95","04400023a10b920368649827ce0d909ab4e2764aaa5ce57ec15428bd98b4e28a","9a33ee580fdebe154bc20386ef13c7be751d5c1a73c728698e54433f8dcafa5a"]))
RAW={"a14_contact_bridge.yaml","a16_design.json","capture.json","clock_rgb_trace.json","ecm_contact_steps.tsv","entity_registry.tsv","initial_validity.json","native_contacts.tsv","poses.tsv","ros_contacts.jsonl","scenario.sdf","topic_qos.json","tray_rgb_t0.png","trigger.tsv","verdict.json"}
OUTER={"batch_status.json"}|{f"{s}/{n}" for s in SCENES for n in ("a16_raw.tar.gz","a16_raw.tar.gz.sha256")}
DIAGNOSTICS={"batch_status.json","build_health.log","build_pose.log","cleanup_probe.json","cleanup_probe.sdf","cleanup_probe_bridge.log","cleanup_probe_server.log","contrast.json","preflight.json"}|{s+".log" for s in SCENES}|{f"{s}/{n}.log" for s in SCENES for n in ("contact_bridge","gui","native_contact","rgb_bridge","server")}
def need(ok,reason):
    if not ok:raise QAError("B_A16_"+reason)
def j(data):return json_bytes(data,"A16_JSON")
def canonical(value):return sha(json.dumps(value,sort_keys=True,separators=(",",":")).encode())
def rows(data):return csv.DictReader(io.StringIO(data.decode("utf8")),delimiter="\t")
def hold(v):
    need(v.get("human_approved") is False and v.get("training_eligible") is False and v.get("ground_truth")=="UNKNOWN_HOLD","GT_AUTO_APPROVAL")

def read_tar(data:bytes,expected:str, *, allowed):
    """Bounded secure tar read + exact internal manifest. No extractall or links."""
    need(len(data)<400*1024*1024,'COMPRESSED_SIZE_LIMIT')
    need(sha(data)==expected,'ARCHIVE_SHA_MISMATCH')
    files={}; size=0
    try:
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
            for member in tar:
                name=member.name
                p=PurePosixPath(name)
                need(name and not p.is_absolute() and p.as_posix()==name
                     and not any(seg in ('','..','.') for seg in name.split('/'))
                     and '\\' not in name and '\x00' not in name and ':' not in name.split('/')[0], 'TAR_PATH_UNSAFE')
                need(member.isfile() and name not in files and 'approval_ledger.jsonl' not in name.lower(), 'TAR_LINK_DUPLICATE_OR_APPROVAL')
                need(member.size>=0 and member.size<=300*1024*1024,'TAR_MEMBER_LIMIT')
                size+=member.size
                need(size<=800*1024*1024 and len(files)<60,'TAR_TOTAL_LIMIT')
                reader=tar.extractfile(member)
                need(reader is not None,'TAR_READ')
                body=reader.read(member.size+1)
                need(len(body)==member.size,'TAR_SIZE_MISMATCH')
                files[name]=body
    except (tarfile.TarError,OSError,EOFError) as e:
        raise QAError('B_A15_TAR_CORRUPT') from e
    need('SHA256SUMS' in files,'TAR_SHA256SUMS_MISSING')
    manifest=files.pop('SHA256SUMS')
    try:lines=manifest.decode('utf8').splitlines()
    except UnicodeError as e:raise QAError('B_A15_MANIFEST_ENCODING') from e
    hashes={}
    for line in lines:
        m=re.fullmatch(r'([0-9a-f]{64})  (.+)',line)
        need(m is not None,'MANIFEST_FORMAT')
        filename=m.group(2)
        need(filename not in hashes,'MANIFEST_DUPLICATE')
        hashes[filename]=m.group(1)
    need(hashes=={name:sha(content) for name,content in files.items()},'MANIFEST_CONTENT_SHA')
    need(set(files)==set(allowed),"MANIFEST_ALLOWLIST")
    return files

def read_pose_grid(tsv:bytes,initial:dict,t0=T0_NS,end=END_NS):
    names=tuple(initial["expected_entities"])
    try:fp=io.StringIO(tsv.decode('utf8'))
    except UnicodeError as e:raise QAError('B_A15_POSE_ENCODING') from e
    tracks=defaultdict(dict);ids={}
    for i,r in enumerate(csv.DictReader(fp,delimiter='\t')):
        need(i<100000,'POSE_ROW_LIMIT')
        try:
            t=int(r['sim_ns']); name=r['entity']; eid=int(r['entity_id']); iteration=int(r['iteration'])
            pos={k:float(r[k]) for k in ('x','y','z','qx','qy','qz','qw')}
        except (KeyError,TypeError,ValueError) as e:raise QAError('B_A15_POSE_SCHEMA') from e
        need(name in names and t>0 and t%STEP_NS==0 and eid>0 and t not in tracks[name],'POSE_TIME_ENTITY_DUPLICATE')
        need(all(math.isfinite(v) for v in pos.values()),'POSE_NONFINITE')
        norm_q(pos)
        need(ids.setdefault(name,eid)==eid,'POSE_ENTITY_ID_DRIFT')
        tracks[name][t]=(iteration,pos)
    need(set(tracks)==set(names) and len(set(ids.values()))==len(names),'POSE_ENTITY_SET')
    for t in range(t0-200_000_000,end+1,STEP_NS):
        need(all(t in tracks[name] for name in names),'POSE_1MS_GRID_GAP')
        iterations={tracks[name][t][0] for name in names}
        need(len(iterations)==1,'POSE_ITERATION_SKEW')
        if t>t0-200_000_000:
            need(tracks['tray_platform'][t][0]==tracks['tray_platform'][t-STEP_NS][0]+1,'POSE_ITERATION_GAP')
    tray0=tracks['tray_platform'][t0][1]
    for t in range(t0,end+1,STEP_NS):
        need(all(abs(tracks['tray_platform'][t][1][k]-v)<1e-8 for k,v in tray0.items()),'TRAY_MOVED_WRONG_PROFILE')
    result={}
    for dish in sorted(set(names)-{'tray_platform','camera'}):
        p0,q0=relative(tray0,tracks[dish][t0][1])
        settle_max=0.;settle_rotate=0.
        for t in range(t0-200_000_000,t0+1,STEP_NS):
            p,q=relative(tracks['tray_platform'][t][1],tracks[dish][t][1])
            settle_max=max(settle_max,math.dist(p,p0))
            settle_rotate=max(settle_rotate,angle(q,q0))
        need(settle_max<=.002+1e-9 and settle_rotate<=.05+1e-8,'PRE_T0_NOT_SETTLED')
        meta=next(x for x in initial['initial_dishes'] if x['name']==dish)
        rad=math.hypot(meta['radius_m'],meta['thickness_m']/2)
        need(abs(p0[0])+rad<=initial['platform']['width_m']/2+1e-8 and
             abs(p0[1])+rad<=initial['platform']['depth_m']/2+1e-8,'INITIAL_OUTSIDE_TRAY')
        prev=None;prev_q=None;max_v=0.;max_w=0.;cum=0.;m=0.;a=0.;min_z=1e9;last=None;onset=None
        for t in range(t0,end+1,STEP_NS):
            p,q=relative(tracks['tray_platform'][t][1],tracks[dish][t][1])
            if prev is not None:
                dp=math.dist(p,prev);cum+=dp;max_v=max(max_v,dp/(STEP_NS/1e9));max_w=max(max_w,angle(q,prev_q)/(STEP_NS/1e9))
            d=math.dist(p0,p);m=max(m,d)
            a=max(a,angle(q0,q));min_z=min(min_z,p[2]);last=p
            if onset is None and t>=TRIGGER_NS and d>.002:onset=t
            prev=p;prev_q=q
        result[dish]={'samples':(end-t0)//STEP_NS+1,'settle_max_displacement_m':settle_max,
                      'settle_max_rotation_rad':settle_rotate,'cumulative_relative_path_m':cum,
                      'max_relative_displacement_m':m,'net_relative_displacement_m':math.dist(p0,last),
                      'max_rotation_rad':a,'min_z_m':min_z,'observed_motion_onset_diagnostic_ns':onset,
                      'final_relative_xyz_m':last,'max_derived_linear_speed_m_s':max_v,'max_derived_angular_speed_rad_s':max_w,'velocity_scope':'DERIVED_FINITE_DIFFERENCE_NOT_MEASURED'}
    return result,tracks,ids

def visibility_geometry(pose_bytes:bytes,design:dict,validity:dict,info:dict,t0=T0_NS):
    """Independently recompute conservative cuboid frustum; not an occlusion mask."""
    observations={}
    for row in csv.DictReader(io.StringIO(pose_bytes.decode('utf8')),delimiter='\t'):
        if int(row['sim_ns'])==t0 and row['entity'] in ({'camera'}|{d['name'] for d in design['initial_dishes']}):
            observations[row['entity']]={k:float(row[k]) for k in ('x','y','z','qx','qy','qz','qw')}
    need(len(observations)==len(design['initial_dishes'])+1,'CAMERA_EXACT_T0_POSES_MISSING')
    cam=observations['camera'];cq=q_inv(norm_q(cam));origin=xyz(cam)
    fx,fy,cx,cy=(info['k'][0],info['k'][4],info['k'][2],info['k'][5])
    out={}
    for d in design['initial_dishes']:
        rad=math.hypot(d['radius_m'],d['thickness_m']/2)
        pos=xyz(observations[d['name']]);pixels=[]
        for dx in (-rad,rad):
            for dy in (-rad,rad):
                for dz in (-rad,rad):
                    local=rotate(cq,tuple(pos[i]+v-origin[i] for i,v in enumerate((dx,dy,dz))))
                    need(local[0]>.05,'CAMERA_DEPTH_NOT_POSITIVE')
                    pixels.append((cx-fx*local[1]/local[0],cy-fy*local[2]/local[0]))
        bounds=[min(x for x,y in pixels),min(y for x,y in pixels),max(x for x,y in pixels),max(y for x,y in pixels)]
        need(0<=bounds[0]<=bounds[2]<640 and 0<=bounds[1]<=bounds[3]<480,'CAMERA_FOV_OUTSIDE')
        recorded=validity.get('dishes',{}).get(d['name'],{}).get('conservative_projected_bbox_px',[])
        need(len(recorded)==4 and all(abs(x-y)<1e-4 for x,y in zip(recorded,bounds)),'CAMERA_FOV_RECALC_MISMATCH')
        out[d['name']]=bounds
    return out


def geometry(d,sdf):
    ds=d["initial_dishes"];names=[x["name"] for x in ds]
    need(len(ds) in (2,3) and names==[f"dish_{i+1:02d}" for i in range(len(ds))],"DISH_SET")
    need(set(d["expected_entities"])=={"tray_platform","camera",*names} and len(d["expected_entities"])==len(ds)+2,"ENTITY_SET")
    dims=[[x["radius_m"],x["thickness_m"]] for x in ds]
    basis={"shape":"cylinder_stack","dimensions_m":dims,"mass_kg_per_dish":ds[0]["mass_kg"],"friction_mu":ds[0]["friction_mu"],"inertia":"UNIFORM_SOLID_CYLINDER"}
    poses=[[x[k] for k in ("x","y","z","roll","pitch","yaw")] for x in ds]
    need(d["family_basis"]==basis and d["layout_basis"]==poses,"GEOMETRY_BASIS")
    need(all(x["mass_kg"]==.22 and x["friction_mu"]==.65 for x in ds),"MATERIAL_DRIFT")
    fam=canonical({"version":"A16_FAMILY_V1","geometry":basis})
    lay=canonical({"version":"A16_LAYOUT_V1","family":fam,"world_poses_m_rad":poses})
    fp=canonical({"geometry":basis,"world_poses_m_rad":poses})
    need(d["geometry_family_id"]==fam and d["physical_layout_id"]==d["stack_id"]==lay and d["physical_fingerprint"]==fp,"GEOMETRY_HASH")
    root=ET.fromstring(sdf);world=root.find("world")
    need(world is not None and world.findtext("physics/max_step_size")=="0.001" and world.findtext("gravity")=="0 0 -9.81","WORLD_PROFILE")
    models={m.get("name"):m for m in world.findall("model")}
    need({n for n in models if n.startswith("dish_")}==set(names),"SDF_DISH_SET")
    for x,p in zip(ds,poses):
        m=models[x["name"]];link=m.find("link")
        need(m.findtext("static")=="false" and m.find(".//joint") is None and all(abs(a-b)<1e-8 for a,b in zip(map(float,m.findtext("pose").split()),p)),"SDF_POSE")
        need(float(link.findtext("inertial/mass"))==x["mass_kg"],"SDF_MASS")
        for typ in ("collision","visual"):
            g=link.find(typ+"/geometry/cylinder")
            need(float(g.findtext("radius"))==x["radius_m"] and float(g.findtext("length"))==x["thickness_m"],"SDF_DIMENSIONS")
        need(float(link.findtext("collision/surface/friction/ode/mu"))==x["friction_mu"] and float(link.findtext("collision/surface/friction/ode/mu2"))==x["friction_mu"],"SDF_FRICTION")
    plugin=world.find("plugin[@name='smartdish::A16Pilot']")
    need(plugin is not None and plugin.findtext("target_model")==names[-1] and int(plugin.findtext("trigger_ns"))==TRIGGER_NS and int(plugin.findtext("duration_ns"))==500_000_000 and float(plugin.findtext("torque_nm"))==TORQUE_NM,"SDF_TRIGGER")
    need(models["tray_platform"].findtext("static")=="true","TRAY_STATIC")
    return {"family":fam,"layout":lay,"fingerprint":fp,"dimensions_m":dims,"pose_basis":poses}

def contacts(f,d,iv,v,ids,tracks):
    topics=d["contact_topics"];ec=defaultdict(Counter);identity={};support=set();by_model={}
    for r in rows(f["ecm_contact_steps.tsv"]):
        t=int(r["sim_ns"]);topic=r["topic"]
        if t==T0_NS:
            by_model[r["model"]]=int(r["collision_id"])
            need(r["present"]=="1" and r["armed"]=="1","T0_COMPONENT")
            support.update(pair(*x.split(":")) for x in r["pairs"].split(";") if x)
        if not T0_NS<t<=END_NS:continue
        key=(int(r["sensor_id"]),int(r["collision_id"]),r["model"],r["sensor"],r["collision"])
        need(identity.setdefault(topic,key)==key,"REGISTRY_DRIFT")
        ps=tuple(sorted({pair(*x.split(":")) for x in r["pairs"].split(";") if x}))
        need(int(r["iteration"])==tracks["tray_platform"][t][0],"ECM_POSE_ITERATION")
        if ps:ec[topic][(t,ps)]+=1
    chain=["tray_platform"]+[x["name"] for x in d["initial_dishes"]]
    for a,b in zip(chain,chain[1:]):
        rec=iv["support"][a+"__"+b]
        need(pair(by_model[a],by_model[b]) in support and rec["exact_t0_positive"] is True and rec["last_positive_ns"]==T0_NS,"SUPPORT_EXACT_T0")
    registry=list(rows(f["entity_registry.tsv"]));reg={int(x["entity_id"]):x for x in registry}
    need(len(reg)==len(registry) and all(int(x["sim_ns"])==T0_NS for x in registry),"REGISTRY_TIME_ID")
    for topic,(s,c,m,sn,cn) in identity.items():
        sr,cr=reg[s],reg[c];link=reg[int(sr["parent_id"])];model=reg[int(link["parent_id"])]
        need(sr["kind"]=="contact_sensor" and cr["kind"]=="collision" and sr["parent_id"]==cr["parent_id"] and link["kind"]=="link" and model["kind"]=="model" and model["name"]==m and sr["name"]==sn and cr["name"]==cn,"REGISTRY_MAPPING")
        if m in ids:need(int(model["entity_id"])==ids[m],"POSE_MODEL_ID")
    tr=list(rows(f["trigger.tsv"]));link=reg[int(tr[0]["link_id"])]
    need(link["kind"]=="link" and link["name"]=="body" and reg[int(link["parent_id"])]["name"]==chain[-1],"TRIGGER_TARGET_ID")
    need(all(int(x["iteration"])==tracks["tray_platform"][int(x["sim_ns"])][0] for x in tr),"TRIGGER_POSE_ITERATION")
    def receive(seq,is_ros):
        counts=defaultdict(Counter);last={};order=Counter();duplicates=Counter()
        for r in seq:
            t=int(r["sim_time_ns"] if is_ros else r["sim_ns"]);topic=r["topic"]
            need(topic in topics,"RECEIVER_TOPIC")
            if not T0_NS<t<=END_NS:continue
            ps=tuple(sorted({pair(x["collision1_id"],x["collision2_id"]) for x in r["contacts"]})) if is_ros else tuple(sorted({pair(*x.split(":")) for x in r["pairs"].split(";") if x}))
            recv=int(r["receive_monotonic_ns"]);need(recv>0 and (not is_ros or r["timestamp_source"]=="ROS_CONTACT_HEADER_STAMP"),"RECEIVER_STAMP")
            if topic in last:
                order[topic]+=int(t<last[topic][0])
                need(recv>=last[topic][1],"RECEIPT_MONOTONIC")
            last[topic]=(t,recv);duplicates[topic]+=int(counts[topic][(t,ps)]>0);counts[topic][(t,ps)]+=1
        return counts,order,duplicates
    native,no,nd=receive(rows(f["native_contacts.tsv"]),False)
    ros,ro,rd=receive((j(x) for x in f["ros_contacts.jsonl"].splitlines()),True)
    stats={}
    for t in topics:
        a,b= native[t],ros[t];r=v["contact_diagnostic"]["topics"][t]
        s={"ecm_positive":sum(ec[t].values()),"native":sum(a.values()),"ros":sum(b.values()),"ecm_native_match":sum((ec[t]&a).values()),"ecm_only":sum((ec[t]-a).values()),"native_not_ecm":sum((a-ec[t]).values()),"native_ros_match":sum((a&b).values()),"native_only":sum((a-b).values()),"ros_only":sum((b-a).values()),"native_duplicates":nd[t],"ros_duplicates":rd[t],"native_order_reversal":no[t],"ros_order_reversal":ro[t]}
        need(s["native_ros_match"]==r["observed_exact_stamp_pair_multiset_intersection"] and s["native_only"]==r["native_observed_not_ros_observed"] and s["ros_only"]==r["ros_observed_not_native_observed"],"TRANSPORT_RECOMPUTE")
        stats[t]=s
    legacy=read_contact(f["ecm_contact_steps.tsv"],f["ros_contacts.jsonl"],topics)
    need(legacy["ros_callbacks"]==v["raw_ros_callbacks"],"ROS_CALLBACK_TOTAL")
    for t,s in legacy["positive_same_stamp_subset_stats"].items():
        need(all(s[k]==v["transport"][t][k] for k in s),"ECM_ROS_RECOMPUTE")
    return {"topics":stats,"component_refresh_rows":legacy["component_refresh_rows"],"initial_support_pairs":len(chain)-1,"production_contact_health":"HOLD","scope":"SUBSCRIBER_OBSERVED_MATCH_NOT_SYSTEM_LOSS_RATE","engine_geometry_registration_proven":False,"full_ros_delivery_proven":False}

def cleanup(v):
    p=v["processes"];roles={x["role"]:x for x in p}
    need(set(roles)=={"gui","server","native_contact","rgb_bridge","contact_bridge"} and len(p)==5,"PROCESS_ROLES")
    need(v["all_owned_stopped"] is True and all(x["stopped"] and not x["process_group_remaining"] for x in p),"RESIDUAL_PROCESS")
    need(v["cleanup"]=="FAIL" and roles["server"]["returncode"]==-11 and roles["server"]["signals"]==[2] and all(x["returncode"]==0 for n,x in roles.items() if n!="server"),"CLEANUP_SEPARATE")
    return {"gui":v["gui"],"cleanup":"FAIL","server_rc":-11,"all_owned_stopped":True}

def scene(f,name,expected):
    d,c,iv,v,clock=[j(f[n]) for n in ("a16_design.json","capture.json","initial_validity.json","verdict.json","clock_rgb_trace.json")]
    hold(d);hold(v)
    need(d["schema"]==2 and d["producer_version"]==v["producer_version"]=="SMARTDISH_A16_V1" and d["source_sha"]==v["source_sha"]==PIN and d["source_class"]=="OWNER_WSL2" and d["platform_sha"]==v["platform_sha"]==PLATFORM_SHA and d["scene_id"]==v["scene_id"]==name,"SOURCE_IDENTITY")
    need(d["rule_candidate"]=="UNKNOWN" and v["production_contact_health"]=="HOLD" and v["data_verdict"]=="PASS" and v["gui"]=="PASS","PRODUCER_BOUNDARY")
    need(d["world_sha256"]==sha(f["scenario.sdf"]),"WORLD_SHA")
    geom=geometry(d,f["scenario.sdf"]);validate_sdf(f["scenario.sdf"],d)
    need(d["t0_ns"]==T0_NS and d["end_ns"]==END_NS and d["step_ns"]==STEP_NS and d["physics_profile"]=="STATIC_TRAY_COMMON_TORQUE_PILOT" and d["trigger_profile"]=="A16_UPPERMOST_WORLD_Y_012NM_500MS_V1" and d["environment_profile_id"]=="A15_STATIC_TRAY_OVERHEAD_V1" and d["seed"]==0,"PROFILE")
    need(d["trigger"]=={"target":d["initial_dishes"][-1]["name"]+"/body","frame":"world","torque_nm":[0,TORQUE_NM,0],"start_ns":TRIGGER_NS,"duration_ns":500_000_000},"TRIGGER_DESIGN")
    info=c["camera_info"]
    need(c["stamp_ns"]==info["stamp_ns"]==T0_NS and c["frame_id"]==info["frame_id"]=="smartdish_tray_optical" and c["encoding"]=="rgb8" and c["width"]==info["width"]==640 and c["height"]==info["height"]==480 and len(info["k"])==9 and all(math.isfinite(x) for x in info["k"]) and info["k"][0]>0 and info["k"][4]>0,"CAPTURE")
    need(c["image_sha256"]==sha(f["tray_rgb_t0.png"]) and T0_NS in clock["frame_stamps"] and max(clock["frame_stamps"])>TRIGGER_NS and not clock["overflow"],"IMAGE_TRACE")
    with Image.open(io.BytesIO(f["tray_rgb_t0.png"])) as im:
        im.load();need(im.format=="PNG" and im.mode=="RGB" and im.size==(640,480) and sha(im.tobytes())==c["pixel_sha256"],"PNG_PIXEL")
        perceptual=ahash(im)
    metrics,tracks,ids=read_pose_grid(f["poses.tsv"],d)
    bounds=visibility_geometry(f["poses.tsv"],d,iv,info)
    for n,m in metrics.items():
        for k in ("cumulative_relative_path_m","max_relative_displacement_m","net_relative_displacement_m","max_rotation_rad","min_z_m","max_derived_linear_speed_m_s","max_derived_angular_speed_rad_s"):
            need(abs(m[k]-v["metrics"][n][k])<2e-6,"METRIC_RECOMPUTE_"+k)
        need(abs(m["settle_max_displacement_m"]-iv["dishes"][n]["settle_max_displacement_m"])<2e-7,"SETTLE_RECOMPUTE")
    read_trigger(f["trigger.tsv"])
    return {"scene_id":name,"archive_sha256":expected,"geometry":geom,"trial_id":d["trial_id"],"batch_id":d["batch_id"],"image_sha256":c["image_sha256"],"pixel_sha256":c["pixel_sha256"],"ahash":perceptual,"pose_rows":len(ids)*10301,"metrics":metrics,"fov_bounds":bounds,"contact":contacts(f,d,iv,v,ids,tracks),"center_group":d["upper_tray_center_group"],"signed_support_offset_m":d["upper_support_offset_x_m"],"support_margin_m":d["nominal_support_margin_m"],"upper":d["initial_dishes"][-1]["name"],**cleanup(v),"human_approved":False,"training_eligible":False,"ground_truth":"UNKNOWN_HOLD"}

def audit(a,asum,b,bsum,c,csum):
    verify_sidecar(a,asum,"a16_pilot_evidence.tar.gz",OWNER);verify_sidecar(b,bsum,"a16_pilot_diagnostics.tar.gz",DIAG)
    f=read_tar(a,OWNER,allowed=OUTER);g=read_tar(b,DIAG,allowed=DIAGNOSTICS)
    batch=j(f["batch_status.json"]);hold(batch)
    need(batch==j(g["batch_status.json"]) and batch["source_sha"]==PIN and batch["source_class"]=="OWNER_WSL2" and batch["platform_sha"]==PLATFORM_SHA and batch["exit_code"]==0 and set(batch["scenes"])==set(SCENES),"BATCH_IDENTITY")
    pre=j(g["preflight.json"])
    need(pre["source_sha"]==PIN and pre["actual_head"]["rc"]==0 and pre["actual_head"]["stdout"].strip()==PIN and pre["tracked_clean"]["rc"]==0 and not pre["tracked_clean"]["stdout"] and pre["mode"]=="--gui" and pre["ros_distro"]=="jazzy" and pre["gz_version"]["stdout"].strip()=="8.15.0","PREFLIGHT_PIN")
    probe=j(g["cleanup_probe.json"])
    need(probe["scope"]=="MINIMAL_CAMERA_ONLY_NO_DISH_NO_CONTACT_PLUGIN" and probe["cleanup"]=="FAIL" and probe["data"]=="PASS" and probe["all_owned_stopped"] is True and {x["role"]:x["returncode"] for x in probe["processes"]}=={"server":-11,"bridge":0},"PROBE_CONTRACT")
    out=[]
    for n in SCENES:
        k=n+"/a16_raw.tar.gz";raw=f[k];verify_sidecar(raw,f[k+".sha256"],"a16_raw.tar.gz",INNER[n])
        x=read_tar(raw,INNER[n],allowed=RAW);v=j(x["verdict.json"])
        need(batch["scenes"][n]==dict(v,archive_sha256=INNER[n]),"SCENE_BATCH_DRIFT")
        out.append(scene(x,n,INNER[n]))
    need(len({x["trial_id"] for x in out})==8 and len({x["batch_id"] for x in out})==1 and len({x["geometry"]["layout"] for x in out})==8 and len({x["geometry"]["fingerprint"] for x in out})==8 and len({x["geometry"]["family"] for x in out})==2,"LAYOUT_INDEPENDENCE")
    prior=audit_a15(c,csum);old=read_a15_tar(c,A15_OWNER_SHA)
    old_geo=[]
    for n,h in A15_INNER_SHA.items():
        d=j(read_a15_tar(old[n+"/a15_raw.tar.gz"],h,inner=True)["a15_design.json"])
        old_geo.append([[x["radius_m"],x["thickness_m"]] for x in d["initial_dishes"]])
    need(not any(x["geometry"]["dimensions_m"] in old_geo for x in out),"A15_GEOMETRY_REUSE")
    images=[(x["scene_id"],x["pixel_sha256"],x["image_ahash64"]) for x in prior["scenes"]]+[(x["scene_id"],x["pixel_sha256"],x["ahash"]) for x in out]
    need(len({x[1] for x in images})==12,"EXACT_PIXEL_DUPLICATE")
    near=[{"pair":[x[0],y[0]],"hamming":sum(a!=b for a,b in zip(x[2],y[2]))} for i,x in enumerate(images) for y in images[i+1:] if sum(a!=b for a,b in zip(x[2],y[2]))<=8]
    totals=Counter()
    for x in out:
        for s in x["contact"]["topics"].values():totals.update(s)
    return {"schema":2,"scope":"B_QA04_OWNER_REVIEW_ONLY","actual_owner_raw_directly_recomputed":True,"source_class":"OWNER_WSL2_A16","source_sha":PIN,"owner_sha256":OWNER,"diagnostics_sha256":DIAG,"outer_manifest_verified":len(f),"inner_manifest_verified":len(RAW)*8,"diagnostic_manifest_verified":len(g),"a15_owner_sha256":A15_OWNER_SHA,"a15_direct_audit":True,"independent_layouts":12,"geometry_families":4,"near_duplicate_review_candidates":near,"scenes":out,"contact_totals":dict(totals),"cleanup_probe":probe,"visual_review":"USER_COMPLETED_NOT_GT_APPROVAL","gates":{f"B-Q0{i}":"PASS" if i==1 else "HOLD" for i in range(1,8)},"gate_reasons":{"B-Q02":"EXACT_T0_FOV_SUPPORT_RECALCULATED; USER_VISUAL_COMPLETED; PER_SAMPLE_OCCLUSION_REVIEW_RECORD_NOT_PROVIDED","B-Q03":"PHYSICAL_RECALCULATED; ENGINE_FULL_DELIVERY_HOLD; CLEANUP_FAIL_SEPARATE","B-Q04":"HUMAN_GT_APPROVAL_ZERO","B-Q05":"12_LAYOUTS_4_FAMILIES; SIGNED_OFFSET_ALIGNMENT_SHORTCUT_REMAINS","B-Q06":"NEAR_DUPLICATE_REVIEW_AND_NO_APPROVED_GROUP_SPLIT","B-Q07":"NO_APPROVED_MANIFEST; RGB_ONLY_FUTURE_INPUT"},"ground_truth":"UNKNOWN_HOLD","approved_count":0,"human_approved":False,"training_eligible":False,"production_contact_health":"HOLD","product_approval":False}
