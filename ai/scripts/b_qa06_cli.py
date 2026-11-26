"""QA06 frozen 20-scene offline qualification; never manufacture human decisions."""
from __future__ import annotations
import argparse,base64,csv,hashlib,html,io,itertools,json,math,os,platform,re,shutil,subprocess,tarfile,tempfile
from collections import Counter,defaultdict
from pathlib import Path,PurePosixPath
from xml.etree import ElementTree as ET
import PIL
from PIL import Image,ImageDraw,ImageOps,ImageStat
import audit_b_a15 as a15
import audit_b_a16 as a16
import audit_b_qa05_diversity as q
import prepare_dataset as contract

PIN18="f1bf400f9b9ef6f554f90b92d92e1e63aeffb049"
REG18="3831383b501767fd81e98aabc1326fc9eb2c15df9e6c450964be25b4e4ef4d6b"
QA05="240bfe72317303566a43b0a3e97bd4c042d95ce75e36ce87e0d940808e391371"
QA05_REPORT="80953ce1bbcca9e1205c8a3fe32c8a4c15a6389f04cec3d4c0a847397fa7808c"
QA05_PIN="f1d9e803725caeeeb43e6d2ad2d66c3945d30a99"
PINS={**q.INPUTS,"qa05":("b_qa05_diagnostics.tar.gz",QA05),
 "a18_p1_raw":("a18_pilot_evidence.tar.gz","9c96f6e3aa8fea3a7450c7eed808e9e611083feb0057d7de0b4773ba840031d2"),
 "a18_p1_diag":("a18_pilot_diagnostics.tar.gz","aa5700d57eb6c15a0239632006b814ac64c3bcff2af66401a656f6b3aa046c04"),
 "a18_p2_raw":("a18_pilot_evidence.tar.gz","32b29821013339ddbb927d5fcba6e9493da56be5ac6ac16dc2a8b19f2551c731"),
 "a18_p2_diag":("a18_pilot_diagnostics.tar.gz","4073fb531d6a575f17c2b844bd4443b88f657c0442dcf4a5c8ef201d577bbfdf")}
INNER18=dict(zip((f"L18-{i:02d}" for i in range(1,9)),[
"34d7c3d07835ba8f7ba5699d4de9000c00375e793e5f6764a8e96f45eab0e46a","f0b7b0b6811926660e8431c5e6360129723c03fcf53d3d164d954dd58069e76a","34fac84fbd20f60c57c01c46b768326352cc5f0560dc0627dc83ddeda60b1b7f","09427f4ca0f3f7a2c652a9db480056a66f91dc80319ccf1501b928b27eaad3ad","ebbff87e50fb08966f587a84440da7366bd3a9d9d5b6aa0757546932b2908113","69a43adf6edcaaa5bedc877cb2b8c9ea7528de157cd1772101d4373d7dc5c422","f0a97bc309ef8a81d47c4dc4e502823d7e59ecfd09b3d3101ddc23d7e482645c","771ca43697353f2da1a95d2770c2a240c7ea0f0e0ca8d92775be4d58351d1aeb"]))
SCENES=set(a15.INNER_SHA)|set(a16.INNER)|set(INNER18)
APP_FIELDS=("reviewer","reviewed_at","initial_placement","rgb_observable","occlusion","physics_validity","learning_suitability","license_status","license_basis","decision","reason")
SCOPE="FIXED_WORLD_Y_TORQUE_CONDITIONAL_STATIC_CYLINDER_RGB_T0_ONLY"
def need(ok,msg):
    if not ok:raise ValueError("B_QA06_"+msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return sha(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())
def j(b):return json.loads(b)
def put(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf8")
def csvrows(b):return list(csv.DictReader(io.StringIO(b.decode("utf8"))))
def safe_tar(b,pin):
    need(len(b)<400*1024*1024 and sha(b)==pin,"ARCHIVE_SHA")
    files={};size=0
    with tarfile.open(fileobj=io.BytesIO(b),mode="r:gz") as t:
        for m in t:
            n=m.name;p=PurePosixPath(n)
            need(n and p.as_posix()==n and not p.is_absolute() and not any(x in ("",".","..") for x in n.split("/")) and "\\" not in n and ":" not in n and m.isfile() and n not in files,"TAR_UNSAFE")
            need(0<=m.size<=300*1024*1024 and len(files)<200,"TAR_LIMIT")
            size+=m.size;need(size<=800*1024*1024,"TAR_TOTAL")
            body=t.extractfile(m).read(m.size+1);need(len(body)==m.size,"TAR_SIZE");files[n]=body
    sums=files.pop("SHA256SUMS");expected={}
    for line in sums.decode().splitlines():
        h,n=line.split("  ",1);need(re.fullmatch("[0-9a-f]{64}",h) and n not in expected,"MANIFEST_FORMAT");expected[n]=h
    need(expected=={n:sha(b) for n,b in files.items()},"MANIFEST_MISMATCH")
    return files
def read_inputs(paths,receipt):
    result={};errors=[]
    need(set(paths)==set(PINS),"INPUT_REGISTRY_KEYS")
    for key,(name,pin) in PINS.items():
        try:
            b=q.get(paths[key],name,pin,receipt.setdefault(key,{}));files=safe_tar(b,pin)
            receipt[key]["manifest_verified"]=len(files);result[key]=files
        except Exception as e:errors.append(e)
    if errors:raise errors[0]
    return result
def fingerprint(ds):
    rows=[[round(float(x.get(k,0))*1e6) for k in ("radius_m","thickness_m","mass_kg","friction_mu","x","y","z","roll","pitch","yaw")] for x in ds]
    return canonical({"version":"A18_CANONICAL_PHYSICAL_V1","shape":"cylinder_stack","rows":rows})
def hold_boundary(d,v):
    need(d["human_approved"] is False and v["human_approved"] is False and d["training_eligible"] is False and v["training_eligible"] is False and d["ground_truth"]==v["ground_truth"]=="UNKNOWN_HOLD" and d["rule_candidate"]=="UNKNOWN" and v["production_contact_health"]=="HOLD","GT_CONTACT_BOUNDARY")
def phase_check(raw,diag,phase):
    scenes={f"L18-{i:02d}" for i in range(1 if phase==1 else 5,5 if phase==1 else 9)}
    need(set(raw)=={"batch_status.json"}|{s+"/"+n for s in scenes for n in ("a18_raw.tar.gz","a18_raw.tar.gz.sha256")},"A18_OUTER_SET")
    need(len(diag)==(34 if phase==1 else 35),"A18_DIAG_COUNT")
    batch=j(raw["batch_status.json"]);pre=j(diag["preflight.json"])
    need(batch==j(diag["batch_status.json"]) and batch["schema"]==3 and batch["phase"]==phase and batch["source_class"]=="OWNER_WSL2" and batch["source_sha"]==PIN18 and batch["platform_sha"]==a15.PLATFORM_SHA and batch["producer_version"]=="SMARTDISH_A18_V1" and batch["exit_code"]==0 and set(batch["scenes"])==scenes and set(batch["planned_scenes"])==scenes and batch["human_approved"] is False and batch["training_eligible"] is False,"A18_PHASE_SOURCE")
    need(pre["source_sha"]==PIN18 and pre["actual_head"]["rc"]==0 and pre["actual_head"]["stdout"].strip()==PIN18 and pre["tracked_clean"]["rc"]==0 and not pre["tracked_clean"]["stdout"] and pre["mode"]=="--gui" and pre["ros_distro"]=="jazzy" and pre["gz_version"]["stdout"].strip()=="8.15.0","A18_OWNER_PREFLIGHT")
    if phase==2:
        g=j(diag["phase_gate.json"]);need(g["core_unchanged"] is True and g["owner_gate"]=="PASS" and g["owner_phase1_archive_sha256"]==PINS["a18_p1_raw"][1] and g["owner_phase1_source_sha"]==PIN18,"A18_PHASE_GATE")
    return batch
def row18(f,s,phase,pin,batch,registry):
    d,c,iv,v=[j(f[n]) for n in ("a18_design.json","capture.json","initial_validity.json","verdict.json")]
    need(set(f)==a16.RAW-{"a16_design.json"}|{"a18_design.json"},"A18_INNER_SET")
    hold_boundary(d,v)
    need(d["schema"]==3 and d["producer_version"]==v["producer_version"]=="SMARTDISH_A18_V1" and d["source_sha"]==v["source_sha"]==PIN18 and d["source_class"]=="OWNER_WSL2" and d["phase"]==phase and d["scene_id"]==v["scene_id"]==s and d["platform_sha"]==v["platform_sha"]==a15.PLATFORM_SHA and d["registry_sha256"]==REG18 and d["qa05_evidence_sha256"]==QA05,"A18_IDENTITY")
    need(batch["scenes"][s]==dict(v,archive_sha256=pin),"A18_BATCH_VERDICT")
    spec=next(x for x in registry["layouts"] if x["scene_id"]==s);family=registry["families"][spec["family"]];ds=d["initial_dishes"]
    fp=fingerprint(ds);layout=canonical({"version":"A18_LAYOUT_V1","family":family["id"],"physical_signature":fp})
    need(fp==d["physical_fingerprint"]==spec["physical_signature_v1"] and layout==d["physical_layout_id"]==d["stack_id"]==spec["layout_id"] and d["geometry_family_id"]==family["id"] and [[x["radius_m"],x["thickness_m"]] for x in ds]==family["dims"] and [x["x"] for x in ds]==spec["x"] and d["seed"]==0,"A18_CANONICAL")
    need(d["world_sha256"]==sha(f["scenario.sdf"]) and d["t0_ns"]==a15.T0_NS and d["step_ns"]==a15.STEP_NS and d["end_ns"]==a15.END_NS and d["prediction_contract"]=="FIXED_WORLD_Y_TORQUE_CONDITIONAL" and d["physics_profile"]=="STATIC_TRAY_FIXED_WORLD_Y_TORQUE" and d["environment_profile_id"]=="A15_STATIC_TRAY_OVERHEAD_V1","A18_PROFILE")
    need(d["trigger"]=={"target":ds[-1]["name"]+"/body","frame":"world","torque_nm":[0,.12,0],"start_ns":a15.TRIGGER_NS,"duration_ns":500_000_000},"A18_TRIGGER_PROFILE")
    a15.validate_sdf(f["scenario.sdf"],d)
    root=ET.fromstring(f["scenario.sdf"]);models={m.get("name"):m for m in root.findall("./world/model")}
    need(models["tray_platform"].findtext("static")=="true","A18_TRAY_STATIC")
    for x in ds:
        m=models[x["name"]];link=m.find("link")
        need(float(link.findtext("inertial/mass"))==x["mass_kg"]==.22 and float(link.findtext("collision/surface/friction/ode/mu"))==x["friction_mu"]==.65 and float(link.findtext("collision/surface/friction/ode/mu2"))==.65,"A18_MATERIAL")
        need(all(abs(u-w)<1e-8 for u,w in zip(map(float,m.findtext("pose").split()),[x[k] for k in ("x","y","z","roll","pitch","yaw")])),"A18_SDF_POSE")
        for kind in ("visual","collision"):
            g=link.find(kind+"/geometry/cylinder");need(float(g.findtext("radius"))==x["radius_m"] and float(g.findtext("length"))==x["thickness_m"],"A18_SDF_GEOMETRY")
    info=c["camera_info"];k=info["k"]
    need(c["stamp_ns"]==info["stamp_ns"]==a15.T0_NS and c["encoding"]=="rgb8" and c["frame_id"]==info["frame_id"]=="smartdish_tray_optical" and info["width"]==640 and info["height"]==480 and len(k)==9 and all(math.isfinite(x) for x in k) and k[0]>0 and k[4]>0 and all(abs(x)<1e-12 for x in info["d"]),"A18_CAMERA")
    png=f["tray_rgb_t0.png"];need(sha(png)==c["image_sha256"],"A18_IMAGE_SHA")
    with Image.open(io.BytesIO(png)) as im0:
        im0.load();need(im0.format=="PNG" and im0.mode=="RGB" and im0.size==(640,480) and q.pixels(im0)==c["pixel_sha256"],"A18_RGB");im=im0.copy()
    metrics,tracks,ids=a16.read_pose_grid(f["poses.tsv"],d)
    for n,m in metrics.items():
        for key in ("cumulative_relative_path_m","max_relative_displacement_m","net_relative_displacement_m","max_rotation_rad","min_z_m","max_derived_linear_speed_m_s","max_derived_angular_speed_rad_s"):
            tol=2e-6 if "angular" not in key else .002
            need(abs(m[key]-v["metrics"][n][key])<=tol,"A18_METRIC_"+key)
        need(abs(m["settle_max_displacement_m"]-iv["dishes"][n]["settle_max_displacement_m"])<=2e-7,"A18_SETTLE")
    boxes=a16.visibility_geometry(f["poses.tsv"],d,iv,info)
    a15.read_trigger(f["trigger.tsv"]);contact=a16.contacts(f,d,iv,v,ids,tracks)
    need(v["data_verdict"]==v["cleanup"]==v["gui"]=="PASS" and v["all_owned_stopped"] is True and {p["role"] for p in v["processes"]}=={"server","native_contact","rgb_bridge","contact_bridge","gui"} and len(v["processes"])==5 and all(p["returncode"]==0 and p["signals"]==[2] and p["stopped"] is True and p["process_group_remaining"] is False for p in v["processes"]),"A18_CLEANUP")
    # GPU runtime evidence is pinned to the accepted producer report; not a new GL context audit.
    frame,trace=q.pose_at_and_trace(f["poses.tsv"],d["expected_entities"]);tp=frame["tray_platform"];cam=frame["camera"]
    visual=models["tray_platform"].find("link/visual");w,dep,th=map(float,visual.findtext("geometry/box/size").split())
    need(abs(w-d["platform"]["width_m"])<1e-8 and abs(dep-d["platform"]["depth_m"])<1e-8,"A18_TRAY_DIM")
    for e in (models["tray_platform"].find("link/pose"),visual.find("pose")):
        need(e is None or all(abs(float(x))<1e-12 for x in e.text.split()),"A18_TRAY_LOCAL_OFFSET")
    pts=[]
    for x,y,z in itertools.product((-w/2,w/2),(-dep/2,dep/2),(-th/2,th/2)):
        pts.append(q.project(tuple(a+b for a,b in zip(a15.xyz(tp),a15.rotate(a15.norm_q(tp),(x,y,z)))),cam,k))
    tray=q.bounds(pts);dish=q.bounds([(b[i],b[i+1]) for b in boxes.values() for i in (0,2)])
    rel={n:trace[n][0][1:] for n in trace};top,lower=ds[-1],ds[-2];p=rel[top["name"]];z=rel[lower["name"]]
    offset=[p[i]-z[i] for i in range(2)];off=math.hypot(*offset);margin=lower["radius_m"]-off;full=margin-top["radius_m"]
    actual=iv["actual_t0_support_geometry"]
    need(abs(actual["center_support_margin_m"]-margin)<1e-7 and abs(actual["full_containment_margin_m"]-full)<1e-7,"A18_MARGIN_RECALC")
    upper=metrics[top["name"]]["max_relative_displacement_m"]
    obs="POSITION_MAINTAINED" if upper<=1e-8 else "LARGE_DISPLACEMENT" if upper>=.1 else "OTHER_OBSERVED"
    overlay=im.copy();draw=ImageDraw.Draw(overlay);draw.rectangle(tray,outline="cyan",width=2);draw.rectangle(dish,outline="yellow",width=2)
    for n,b in boxes.items():draw.rectangle(b,outline="magenta",width=1);draw.text((b[0],b[1]),n,fill="white")
    buf=io.BytesIO();overlay.save(buf,format="PNG")
    r={"scene_id":s,"trial_id":d["trial_id"],"layout":layout,"family":family["id"],"stack_id":layout,"physical_signature":fp,"seed":0,"version":"a18","environment":d["environment_profile_id"],"source_environment":"OWNER_WSL2","inner_sha":pin,"image_sha":c["image_sha256"],"pixel_sha":c["pixel_sha256"],"dish_count":len(ds),"dishes":ds,"relative_t0_xyz_m":rel,"stack_height_nominal_m":sum(x["thickness_m"] for x in ds),"upper_center_distance_m":math.hypot(*p[:2]),"center_nominal":d["upper_tray_center_group"],"source_sha":PIN18,"offset_xy_m":offset,"offset_m":off,"nominal_support_margin_m":full,"center_support_margin_m":margin,"torque_world_nm":[0,.12,0],"torque_tray_nm":a15.rotate(a15.q_inv(a15.norm_q(tp)),(0,.12,0)),"support_offset_world_m":a15.rotate(a15.norm_q(tp),(*offset,0.)),"colors":[x["color"] for x in ds],"background":root.findtext("./world/scene/background") or "UNKNOWN","camera_pose":cam,"brightness":ImageStat.Stat(im.convert("L")).mean[0],"dish_bbox_area_px2":(dish[2]-dish[0])*(dish[3]-dish[1]),"tray_bbox":tray,"dish_bbox":dish,"dish_bboxes":boxes,"bbox_overlap":[{"pair":[n,m],"bbox_intersection_px2":q.intersect(b,boxes[m])} for n,b in boxes.items() for m in boxes if n<m],"visibility":"BBOX_ONLY_NOT_SEGMENTATION","support":iv["support"],"settle":iv["dishes"],"trigger":d["trigger"],"end_ns":d["end_ns"],"metrics":metrics,"observation":obs,"visual_review_history":"NOT_PER_SCENE_GT_APPROVAL","contact_health":"HOLD","contact_recomputed":contact,"cleanup":"PASS","gt":"UNKNOWN_HOLD","human_approved":False,"training_eligible":False,"gpu_evidence_scope":"PINNED_A18_OWNER_ACCEPTANCE_PROFILE_NOT_NEW_GL_CONTEXT_AUDIT"}
    return r,{n:q.image_data(x) for n,x in {"full":im,"tray":im.crop(q.crop_box(tray)),"dish":im.crop(q.crop_box(dish))}.items()},buf.getvalue(),trace,png
def load_candidates(inputs,receipt,registry_path):
    registry_bytes=registry_path.read_bytes();need(sha(registry_bytes)==REG18,"A18_REGISTRY_SHA");registry=j(registry_bytes)
    qa=inputs["qa05"];prior=j(qa["qa05_report.json"]);status=j(qa["diagnostic_status.json"])
    need(sha(qa["qa05_report.json"])==QA05_REPORT and status["verifier_sha"]==QA05_PIN and prior["actual_12_scene_roi_review"] is True and prior["approved_count"]==0 and prior["input_sha"]=={k:v[1] for k,v in q.INPUTS.items()},"QA05_RECEIPT")
    need(sha(inputs["qa04"]["qa_report.json"])==q.QA04_REPORT,"QA04_REPORT")
    oldmap={r["scene_id"]:r for r in j(inputs["qa04"]["qa_report.json"])["scenes"]}
    prev={r["scene_id"]:r for r in csvrows(qa["geometry_inventory.csv"])}
    items=[];inner={}
    for version,pins in (("a15",a15.INNER_SHA),("a16",a16.INNER)):
        for s,pin in pins.items():
            outer=inputs[version];key=s+"/"+version+"_raw.tar.gz";b=outer[key]
            a15.verify_sidecar(b,outer[key+".sha256"],version+"_raw.tar.gz",pin);f=safe_tar(b,pin)
            receipt[version].setdefault("inner",{})[s]=len(f)
            item=q.adapt(f,version,s,pin,oldmap.get(s));r=item[0]
            for k in ("layout","family","trial_id","image_sha","pixel_sha","inner_sha","observation"):
                need(r[k]==prev[s][k],"QA05_SCENE_LINK_"+k)
            r["physical_signature"]=fingerprint(r["dishes"]);r["center_support_margin_m"]=r["nominal_support_margin_m"]+r["dishes"][-1]["radius_m"]
            items.append(item);inner[s]=b
    for phase in (1,2):
        key=f"a18_p{phase}_raw";raw=inputs[key];batch=phase_check(raw,inputs[f"a18_p{phase}_diag"],phase)
        for s in sorted(batch["scenes"]):
            b=raw[s+"/a18_raw.tar.gz"];pin=INNER18[s];a15.verify_sidecar(b,raw[s+"/a18_raw.tar.gz.sha256"],"a18_raw.tar.gz",pin);f=safe_tar(b,pin)
            receipt[key].setdefault("inner",{})[s]=len(f);items.append(row18(f,s,phase,pin,batch,registry));inner[s]=b
    items.sort(key=lambda x:x[0]["scene_id"]);records=[x[0] for x in items]
    need({r["scene_id"] for r in records}==SCENES and len(records)==len(q.unique_layouts(records))==len({r["physical_signature"] for r in records})==len({r["trial_id"] for r in records})==20 and len({r["family"] for r in records})==6,"FREEZE_IDENTITY")
    need(len({r["pixel_sha"] for r in records})==len({r["image_sha"] for r in records})==20,"PIXEL_FILE_DUPLICATE")
    oldpairs=csvrows(qa["similarity_matrix.csv"]);pairs=[]
    for p in oldpairs:
        for k,v in list(p.items()):
            if k in ("same_pixel","same_file"):p[k]=v=="True"
            elif k not in ("a","b"):p[k]=float(v) if "ssim" in k else int(v)
        pairs.append(p)
    oldids=set(prev)
    need(len(pairs)==66 and {tuple(sorted((p["a"],p["b"]))) for p in pairs}==set(itertools.combinations(sorted(oldids),2)),"QA05_PAIR_SET")
    for x,y in itertools.combinations(items,2):
        if x[0]["scene_id"] in oldids and y[0]["scene_id"] in oldids:continue
        pairs.extend(q.similarity([x,y]))
    need(len(pairs)==190 and len({tuple(sorted((p["a"],p["b"]))) for p in pairs})==190,"PAIR_COUNT")
    return items,inner,pairs
def review_rows(reg):
    return [dict(evidence_id=r["evidence_id"],scene_id=r["scene_id"],archive_sha256=r["archive_sha256"],image_sha256=r["image_sha256"],observation=r["observation"],**{k:"" for k in APP_FIELDS}) for r in reg]
def preprocess(png,box):
    # Existing ImageOps.fit 224x224; test its central 480x480 crop against projected dish bbox.
    with Image.open(io.BytesIO(png)) as im:
        need(im.mode=="RGB" and im.size==(640,480),"PREPROCESS_INPUT")
        need(80<=box[0] and box[2]<560 and 0<=box[1] and box[3]<480,"PREPROCESS_DISH_CLIPPED")
        out=io.BytesIO();ImageOps.fit(ImageOps.exif_transpose(im).convert("RGB"),(224,224),Image.Resampling.BILINEAR).save(out,format="PNG")
    return out.getvalue()
def gates():
    reasons=["pinned provenance verified","human RGB/occlusion review pending","offline pose/ECM reviewed; production Contact HOLD","human GT and rights pending","shortcut and near pairs need review","no approved group split","no released manifest/C review"]
    return {f"B-Q0{i+1}":{"previous":"PASS" if i==0 else "HOLD","current":"PASS" if i==0 else "HOLD","reason":r,"owner":("B" if i in (0,4,5) else "B/Operator" if i in (1,3) else "PM/B/C" if i==2 else "B/C"),"mvp_impact":"AI OFF retained; AI ON held"} for i,r in enumerate(reasons)}
def readiness(out,state,why,version=None):
    put(out/"c_training_readiness.json",{"dataset_state":state,"dataset_version":version,"verdict":"C_REVIEW_REQUIRED" if state=="DATASET_V1_RELEASED" else "NO_GO","pipeline_qualification":"CONTRACT_READY_C_REVIEW_REQUIRED" if state=="DATASET_V1_RELEASED" else "HOLD","research_pilot":"CONDITIONAL_REVIEW_REQUIRED","generalization_validation":"NOT_ESTABLISHED","safety_certification":"OUT_OF_SCOPE","scope":SCOPE,"training_executed":False,"input":"RGB(t0) only; no metadata or post-t0","blockers":why})
    put(out/"e_integration_readiness.json",{"verdict":"HOLD","ai_off":"PRESERVE_EXISTING","ai_on":"NO_MODEL_ACCEPTANCE_OR_E_RUNTIME_EVIDENCE","mock_fallback":"INDEPENDENT_WORK_ALLOWED","training_executed":False,"blockers":why+["C model/evaluation and E integration acceptance required"]})
    put(out/"remaining_blockers.json",{"blockers":why,"A19":"NOT_AUTHORIZED","change_request":"NONE_UNTIL_SPECIFIC_BLOCKING_EVIDENCE_AND_PM_APPROVAL"})
def render_review(out,items,pairs,reg):
    rows=review_rows(reg);q.write_csv(out/"review_worksheet.csv",rows)
    (out/"human_approval_template.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows))
    sections=[]
    for r,_,overlay,trace,png in items:
        n=r["scene_id"];related=sorted((p for p in pairs if n in (p["a"],p["b"])),key=lambda p:p["dish_ahash"])[:5]
        info={k:r[k] for k in ("dishes","relative_t0_xyz_m","offset_xy_m","center_support_margin_m","nominal_support_margin_m","support","settle","trigger","metrics","observation","contact_health","cleanup","visibility")}
        topview=[]
        for d in r["dishes"]:
            p=r["relative_t0_xyz_m"][d["name"]];topview.append(f'<circle cx="{160+p[0]*400}" cy="{115-p[1]*400}" r="{d["radius_m"]*400}" fill="#acc6dc" fill-opacity=".55" stroke="#385b80"/>')
        diagram='<svg viewBox="0 0 320 230" width="320"><rect x="20" y="3" width="280" height="224" fill="#eee" stroke="#555"/>'+''.join(topview)+'</svg>'
        sections.append(f'<section><h2>{html.escape(n)}</h2><p>Original RGB (t0); overlay is conservative bounding box, not a mask.</p><img width="640" src="data:image/png;base64,{base64.b64encode(png).decode()}"><img width="640" src="data:image/png;base64,{base64.b64encode(overlay).decode()}"><h3>Initial tray-relative geometry (schematic)</h3>{diagram}<h3>Displacement from t0 (100 ms display)</h3>{q.trace_svg(trace)}<pre>{html.escape(json.dumps(info,indent=2))}</pre><p>Nearest review candidates: {html.escape(json.dumps(related))}</p><p>Complete the separate human approval JSONL/CSV. No decisions prefilled.</p></section>')
    (out/"review_workbook.html").write_text('<!doctype html><meta charset="utf-8"><title>QA06 private frozen candidates</title><style>body{font:16px sans-serif;max-width:950px;margin:2rem auto}section{border-top:1px solid #888;padding:1rem}img{max-width:100%}pre{white-space:pre-wrap}</style><h1>QA06 REVIEW_ONLY — 20 frozen candidates</h1>'+''.join(sections))
def audit(paths,out,source,registry_path,receipt):
    inputs=read_inputs(paths,receipt);items,inners,pairs=load_candidates(inputs,receipt,registry_path);rs=[x[0] for x in items]
    reg=[];(out/"candidate_rgb").mkdir();(out/"physics_evidence").mkdir()
    for r,_,_,_,png in items:
        s=r["scene_id"];b=inners[s];path="candidate_rgb/"+s+".png";evidence="physics_evidence/"+s+".tar.gz"
        (out/path).write_bytes(png);(out/evidence).write_bytes(b)
        prep="PASS"
        try:preprocess(png,r["dish_bbox"])
        except ValueError:prep="HOLD_DISH_CLIPPED"
        reg.append({"evidence_id":canonical([r["source_sha"],r["inner_sha"],r["scene_id"],r["image_sha"]]),"source_sha":r["source_sha"],"archive_sha256":r["inner_sha"],"schema_version":{"a15":1,"a16":2,"a18":3}[r["version"]],"producer_version":"SMARTDISH_"+r["version"].upper()+"_V1","source_class":"OWNER_WSL2","scene_id":s,"physical_layout_id":r["layout"],"physical_fingerprint":r["physical_signature"],"geometry_family_id":r["family"],"trial_id":r["trial_id"],"image_sha256":r["image_sha"],"pixel_sha256":r["pixel_sha"],"data_verdict":"PASS","cleanup_verdict":r["cleanup"],"contact_health":"HOLD","human_approval_status":"PENDING","license_status":"PENDING","release_status":"REVIEW_ONLY","observation":r["observation"],"image_path":path,"physics_path":evidence,"physics_bytes":len(b),"dish_bbox":r["dish_bbox"],"preprocess_224":prep})
    put(out/"evidence_registry.json",reg);q.write_csv(out/"dataset_candidate_manifest.csv",reg);q.write_csv(out/"unified_geometry_inventory.csv",rs);q.write_csv(out/"similarity_matrix.csv",pairs)
    roi={r:{str(t):sum(p[r+"_ahash"]<=t for p in pairs) for t in (0,4,8,12)} for r in q.REGIONS};put(out/"roi_similarity_report.json",{"pair_count":190,"reused":66,"new":124,"ahash_threshold_counts":roi,"scope":"EXPLORATORY_NOT_DUPLICATE_VERDICT"})
    risk=q.risks(rs);q.write_csv(out/"shortcut_risk_matrix.csv",risk)
    prior_families={r["family"] for r in rs if r["version"]!="a18"}
    cells={(r["family"],r["center_nominal"],"positive" if r["offset_xy_m"][0]>1e-6 else "negative" if r["offset_xy_m"][0]<-1e-6 else "zero") for r in rs if r["family"] in prior_families}
    split=q.split_feasibility(rs,pairs);put(out/"group_split_feasibility.json",split)
    render_review(out,items,pairs,reg)
    why=["human GT/rights/occlusion pending","PM/B/C offline evidence policy and near-pair review pending","approved family-independent split absent"]
    report={"state":"B_QA06_CANDIDATE_FROZEN_REVIEW_READY","scope":SCOPE,"actual_candidates":20,"families":6,"observations":dict(Counter(r["observation"] for r in rs)),"historical_family_cells":len(cells),"roi":roi,"split":split,"preprocess":dict(Counter(r["preprocess_224"] for r in reg)),"manifest_counts":receipt,"old_physics_reused":12,"new_pose_contact_recomputed":8,"approved_count":0,"dataset_release":"HOLD","training_executed":False,"cleanup":dict(Counter(r["cleanup"] for r in rs)),"contact_health":"HOLD","A19":"NOT_AUTHORIZED","gpu_profile":"A18 Owner accepted scope; no new GPU instrumentation"}
    put(out/"qa06_report.json",report);put(out/"gate_status.json",gates());readiness(out,"CANDIDATE_FROZEN",why)
    files={str(p.relative_to(out)):sha(p.read_bytes()) for p in sorted(out.rglob("*")) if p.is_file()}
    seal={"schema":1,"source_sha":source,"scope":SCOPE,"candidate_version":canonical(reg),"inputs":{k:v[1] for k,v in PINS.items()},"files":files,"state":report["state"]}
    put(out/"audit_receipt.json",seal);(out/"audit_receipt.json.sha256").write_text(sha((out/"audit_receipt.json").read_bytes())+"  audit_receipt.json\n")
    return report
def side_verified(p,expected=None):
    p=Path(p);s=Path(str(p)+".sha256")
    need(p.is_file() and s.is_file() and not p.is_symlink() and not s.is_symlink(),"SEALED_FILE_MISSING")
    b=p.read_bytes();h=sha(b);need(s.read_text().split()==[h,p.name] and (expected is None or h==expected),"SEALED_FILE_SHA");return b
def safe_local(root,name):
    p=PurePosixPath(name);need(p.as_posix()==name and not p.is_absolute() and ".." not in p.parts and "\\" not in name,"RECEIPT_PATH")
    x=root/name;need(x.is_file() and x.resolve().is_relative_to(root.resolve()) and not x.is_symlink() and not any(y.is_symlink() for y in x.parents if y!=root and y.is_relative_to(root)),"RECEIPT_FILE")
    return x
def read_receipt(root,expected,source):
    need(re.fullmatch("[0-9a-f]{64}",expected or "") is not None,"TRUSTED_RECEIPT_REQUIRED")
    r=j(side_verified(root/"audit_receipt.json",expected));need(r["source_sha"]==source and r["state"]=="B_QA06_CANDIDATE_FROZEN_REVIEW_READY" and r["inputs"]=={k:v[1] for k,v in PINS.items()},"RECEIPT_VERSION")
    for n,h in r["files"].items():need(sha(safe_local(root,n).read_bytes())==h,"RECEIPT_ARTIFACT_DRIFT")
    reg=j((root/"evidence_registry.json").read_bytes())
    need(canonical(reg)==r["candidate_version"] and len(reg)==20 and {x["scene_id"] for x in reg}==SCENES and len({x["physical_layout_id"] for x in reg})==20 and all(x["human_approval_status"]=="PENDING" and x["release_status"]=="REVIEW_ONLY" for x in reg),"RECEIPT_CANDIDATE")
    return r,reg
def validate_approvals(rows,reg):
    by={x["evidence_id"]:x for x in reg};need(len(rows)==len(by) and len({x.get("evidence_id") for x in rows})==len(by),"APPROVAL_COMPLETE")
    valid=[];excluded=[]
    for a in rows:
        r=by[a["evidence_id"]]
        need(all(a.get(k)==r[k] for k in ("scene_id","archive_sha256","image_sha256","observation")),"APPROVAL_EVIDENCE_LINK")
        need(all(isinstance(a.get(k),str) and a[k].strip() and a[k]!="PENDING" for k in APP_FIELDS),"APPROVAL_PENDING")
        need(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:Z|[+-]\d\d:\d\d)",a["reviewed_at"]) is not None,"APPROVAL_TIMESTAMP")
        need(a["decision"] in ("STABLE","UNSTABLE","EXCLUDE"),"APPROVAL_DECISION")
        if a["decision"]=="EXCLUDE":excluded.append({"scene_id":r["scene_id"],"reason":a["reason"]});continue
        need(all(a[k]=="PASS" for k in ("initial_placement","rgb_observable","occlusion","physics_validity","learning_suitability")) and a["license_status"] in ("OWNED","AUTHORIZED") and r["preprocess_224"]=="PASS","APPROVAL_OR_RIGHTS_HOLD")
        valid.append((r,a))
    return valid,excluded
def family_split(valid,pairs,decisions):
    # Conservative: all family members stay together; explicitly reviewed near pairs
    # may be independent or require same split. No automatic deletion.
    by={r["scene_id"]:(r,a) for r,a in valid};families=sorted({r["geometry_family_id"] for r,a in valid})
    need(all(len({r["physical_layout_id"] for r,a in valid if a["decision"]==label})>=3 for label in contract.LABELS),"MIN_CLASS_LAYOUTS")
    same=[]
    for p in pairs:
        if p["a"] not in by or p["b"] not in by:continue
        need(p["same_pixel"] not in (True,"True") and p["same_file"] not in (True,"True"),"EXACT_DUPLICATE")
        if int(p["tray_ahash"])<=8 or int(p["dish_ahash"])<=8:
            key="|".join(sorted((p["a"],p["b"])));d=decisions.get(key,{})
            need(d.get("decision") in ("INDEPENDENT","SAME_SPLIT") and isinstance(d.get("reason"),str) and d["reason"].strip() and isinstance(d.get("reviewer"),str) and d["reviewer"].strip(),"NEAR_PAIR_REVIEW_PENDING")
            if d["decision"]=="SAME_SPLIT":same.append((by[p["a"]][0]["geometry_family_id"],by[p["b"]][0]["geometry_family_id"]))
    best=None
    for choices in itertools.product(contract.SPLITS,repeat=len(families)):
        m=dict(zip(families,choices))
        if any(m[a]!=m[b] for a,b in same):continue
        counts={s:Counter(a["decision"] for r,a in valid if m[r["geometry_family_id"]]==s) for s in contract.SPLITS}
        if not all(all(c[l]>0 for l in contract.LABELS) for c in counts.values()):continue
        score=sum(abs(sum(counts[s].values())-len(valid)*t) for s,t in zip(contract.SPLITS,(.6,.2,.2)))
        key=(score,canonical(m))
        if best is None or key<best[0]:best=(key,m)
    need(best is not None,"NO_INDEPENDENT_FAMILY_SPLIT")
    return best[1]
def release(root,out,receipt_sha,source,approval,policy):
    seal,reg=read_receipt(root,receipt_sha,source)
    need(approval is not None and policy is not None,"HUMAN_APPROVAL_REQUIRED")
    ab=side_verified(approval);pb=side_verified(policy);rows=[j(x) for x in ab.splitlines() if x.strip()];pol=j(pb)
    need(pol["receipt_sha256"]==receipt_sha and pol["approval_sha256"]==sha(ab) and pol["scope"]==SCOPE and pol["offline_pose_ecm_contact_exception"]=="ACCEPT_RESEARCH_ONLY_WITH_PRODUCTION_CONTACT_HOLD","POLICY_SCOPE_APPROVAL")
    need(all(isinstance(pol.get(k),dict) and pol[k].get("decision")=="APPROVE" and str(pol[k].get("reviewer","")).strip() and str(pol[k].get("reason","")).strip() for k in ("pm","b","c")),"PM_B_C_REVIEW_REQUIRED")
    valid,excluded=validate_approvals(rows,reg);pairs=csvrows((root/"similarity_matrix.csv").read_bytes());assignment=family_split(valid,pairs,pol.get("near_pair_decisions",{}))
    stage=Path(tempfile.mkdtemp(prefix=".release-",dir=out))
    try:
        (stage/"images").mkdir();(stage/"evidence").mkdir();manifest=[];split=[]
        for i,(r,a) in enumerate(sorted(valid,key=lambda x:x[0]["evidence_id"])):
            # Opaque ID; no label or scene token in filename. Evidence remains separate.
            name="sample-"+r["evidence_id"][:24];ip="images/"+name+".png";ep="evidence/"+name+".tar.gz"
            png=preprocess(safe_local(root,r["image_path"]).read_bytes(),r["dish_bbox"])
            (stage/ip).write_bytes(png);b=safe_local(root,r["physics_path"]).read_bytes();need(sha(b)==r["archive_sha256"],"PHYSICS_SHA");(stage/ep).write_bytes(b)
            config={"camera":"RGB_T0_ONLY","preprocess":"Pillow ImageOps.fit RGB224 BILINEAR","physics_evidence":ep,"physics_evidence_sha256":sha(b),"physics_evidence_size_bytes":len(b)}
            row=dict(sample_id=name,scene_id=r["scene_id"],stack_id=r["physical_layout_id"],label=a["decision"],image_path=ip,source="GAZEBO_TRAY",capture_config=json.dumps(config),license_status=a["license_status"],ground_truth="PHYSICS_OBSERVED",image_sha256=sha(png))
            manifest.append(row);split.append(dict(row,split=assignment[r["geometry_family_id"]]))
        contract.validate(manifest,stage)
        need(len({sha(Image.open(stage/x["image_path"]).tobytes()) for x in manifest})==len(manifest),"PREPROCESS_PIXEL_DUPLICATE")
        contract.write_csv(stage/"manifest.csv",manifest,contract.FIELDS);contract.write_csv(stage/"split_manifest.csv",split,contract.SPLIT_FIELDS)
        with (stage/"excluded_samples.csv").open("x",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["scene_id","reason"]);w.writeheader();w.writerows(excluded)
        (stage/"human_approval_ledger.jsonl").write_bytes(ab);(stage/"approved_policy.json").write_bytes(pb)
        (stage/"DATASET_CARD_KO.md").write_text("# SmartDish Dataset v1 — conditional research pilot\nRGB(t0) only; fixed world +Y torque; no safety certification. Human approval and rights per ledger. Production Contact HOLD, historic cleanup FAIL. C actual training NOT_RUN.\n")
        version=canonical({"candidate":seal["candidate_version"],"approval":sha(ab),"policy":sha(pb),"manifest":sha((stage/"manifest.csv").read_bytes()),"split":sha((stage/"split_manifest.csv").read_bytes())})
        release_info={"state":"DATASET_V1_RELEASED","verdict":"B_QA06_FINAL_DATASET_V1_RELEASED","version":version,"candidate_version":seal["candidate_version"],"receipt_sha256":receipt_sha,"source_sha":source,"label_map":contract.LABEL_MAP,"approved_count":len(manifest),"excluded_count":len(excluded),"family_assignment":assignment,"scope":SCOPE,"contact_health":"HOLD","training_executed":False,"files":{str(p.relative_to(stage)):sha(p.read_bytes()) for p in stage.rglob("*") if p.is_file()}}
        put(stage/"dataset_release.json",release_info);(stage/"dataset_release.json.sha256").write_text(sha((stage/"dataset_release.json").read_bytes())+"  dataset_release.json\n")
        stage.rename(out/"dataset_v1")
    except Exception:
        shutil.rmtree(stage,ignore_errors=True);raise
    readiness(out,"DATASET_V1_RELEASED",["C must independently verify dataset and approve training plan; E actual model not accepted"],version)
    put(out/"gate_status.json",{"offline_dataset":"RELEASED_RESEARCH_ONLY","production_contact":"HOLD","E":"HOLD","scope":SCOPE})
    return release_info
def verify_released(root,expected,source,out):
    r=j(side_verified(root/"dataset_release.json",expected));need(r["source_sha"]==source and r["state"]=="DATASET_V1_RELEASED" and r["label_map"]==contract.LABEL_MAP,"RELEASE_VERSION")
    for n,h in r["files"].items():need(sha(safe_local(root,n).read_bytes())==h,"RELEASE_ARTIFACT_DRIFT")
    rows=contract.load_manifest(root/"manifest.csv");contract.validate(rows,root)
    need(len(rows)==r["approved_count"],"RELEASE_COUNT")
    readiness(out,"DATASET_V1_RELEASED",["C independent model readiness review still required"],r["version"]);return r
def diagnostics(out,status):
    put(out/"diagnostic_status.json",status)
    # Raw nested TARs and released data are not duplicated in the diagnostic archive.
    files=[p for p in sorted(out.iterdir()) if p.is_file()]
    dest=out/"b_qa06_diagnostics.tar.gz"
    with tarfile.open(dest,"x:gz") as t:
        sums=b""
        for p in files:
            t.add(p,arcname=p.name,recursive=False);sums+=(sha(p.read_bytes())+"  "+p.name+"\n").encode()
        m=tarfile.TarInfo("SHA256SUMS");m.size=len(sums);m.mode=0o600;t.addfile(m,io.BytesIO(sums))
    (out/(dest.name+".sha256")).write_text(sha(dest.read_bytes())+"  "+dest.name+"\n")
    print("B_QA06_DIAGNOSTICS="+str(dest));print("B_QA06_DIAGNOSTICS_SHA="+sha(dest.read_bytes()))
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("stage",choices=("audit","review","release","readiness"));p.add_argument("--out-dir",type=Path,required=True);p.add_argument("--verifier-sha",required=True)
    p.add_argument("--input-registry",type=Path);p.add_argument("--audit-dir",type=Path);p.add_argument("--receipt-sha");p.add_argument("--approval",type=Path);p.add_argument("--policy",type=Path);p.add_argument("--dataset-dir",type=Path);p.add_argument("--dataset-release-sha")
    a=p.parse_args(argv);os.umask(0o077);out=a.out_dir.absolute();out.mkdir(parents=True,exist_ok=False,mode=0o700)
    receipt={};status={"stage":a.stage,"source_sha":a.verifier_sha,"checkout_head":None,"tracked_clean":None,"python":platform.python_version(),"pillow":PIL.__version__,"platform":platform.platform(),"input_receipt":receipt,"exit_code":2,"training_executed":False,"dataset_release":"HOLD","first_error":None}
    try:
        root=Path(__file__).resolve().parents[2]
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip();status["checkout_head"]=head
        need(re.fullmatch("[0-9a-f]{40}",a.verifier_sha) and head==a.verifier_sha,"HEAD_DRIFT")
        clean=not subprocess.check_output(["git","-C",str(root),"status","--porcelain","--untracked-files=no"],text=True).strip();status["tracked_clean"]=clean;need(clean,"DIRTY")
        if a.stage=="audit":
            paths=j(a.input_registry.read_bytes());need(all(Path(v).is_absolute() for v in paths.values()),"ABSOLUTE_INPUTS")
            result=audit(paths,out,head,Path(__file__).with_name("qa06_a18_registry.json"),receipt)
        elif a.stage=="review":
            seal,reg=read_receipt(a.audit_dir,a.receipt_sha,head)
            for n in ("review_workbook.html","review_worksheet.csv","human_approval_template.jsonl"):shutil.copyfile(a.audit_dir/n,out/n)
            result={"state":"REVIEW_ONLY","candidate_version":seal["candidate_version"]};readiness(out,"CANDIDATE_FROZEN",["human approval pending"])
        elif a.stage=="release":
            result=release(a.audit_dir,out,a.receipt_sha,head,a.approval,a.policy);status["dataset_release"]="RELEASED"
        else:
            need(re.fullmatch("[0-9a-f]{64}",a.dataset_release_sha or "") is not None,"TRUSTED_RELEASE_SHA_REQUIRED")
            result=verify_released(a.dataset_dir,a.dataset_release_sha,head,out);status["dataset_release"]="RELEASED"
        status["exit_code"]=0;status["result_state"]=result["state"];print(result["state"])
    except Exception as e:
        status["first_error"]=type(e).__name__+": "+str(e);status["result_state"]="B_QA06_HOLD"
        readiness(out,"HOLD",[status["first_error"]])
        if not (out/"gate_status.json").exists():put(out/"gate_status.json",{"previous_Q01":"PASS","current":"HOLD","reason":status["first_error"]})
        print("B_QA06_HOLD",status["first_error"])
    diagnostics(out,status);return status["exit_code"]
if __name__=="__main__":raise SystemExit(main())
