"""QA05 read-only diversity review. Never train, approve labels or release splits."""
from __future__ import annotations
import base64,csv,html,io,itertools,json,math,statistics
from collections import Counter,defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image,ImageDraw,ImageStat
import audit_b_a15 as a15
import audit_b_a16 as a16

QA04_SHA="6bb16e93a22079c588a63afc9f04e8725154b25313ea133d277d5ba547eea83f"
QA04_REPORT="8cebb1fbe64de0b5db8acb55aa34f461f7f67c9a7158462cd3ba6289a6ca6eec"
QA04_PIN="b36694d8c243e44147f9f32b9c2189deef1e8f9f"
INPUTS={"a15":("a15_pilot_evidence.tar.gz",a15.OWNER_SHA),"a16":("a16_pilot_evidence.tar.gz",a16.OWNER),"a16_diag":("a16_pilot_diagnostics.tar.gz",a16.DIAG),"qa04":("b_a16_qa04_diagnostics.tar.gz",QA04_SHA)}
REGIONS=("full","tray","dish")
def need(ok,msg):
    if not ok: raise ValueError("B_QA05_"+msg)
def sha(data):return a15.sha(data)
def j(data):return json.loads(data)
def get(path,name,pin):
    path=Path(path);side=Path(str(path)+".sha256")
    need(path.is_file() and side.is_file() and not path.is_symlink() and not side.is_symlink(),"INPUT_MISSING_OR_LINK_"+name)
    need(path.stat().st_size<400*1024*1024 and side.stat().st_size<4096,"INPUT_SIZE")
    b=path.read_bytes();a15.verify_sidecar(b,side.read_bytes(),name,pin);return b
def hamming(a,b):
    need(len(a)==len(b)==64 and set(a+b)<={"0","1"},"HASH64_BITS")
    return (int(a,2)^int(b,2)).bit_count()
def dhash(im):
    p=list(im.convert("L").resize((9,8),Image.Resampling.BICUBIC).getdata())
    return "".join("1" if p[y*9+x]>p[y*9+x+1] else "0" for y in range(8) for x in range(8))
def pixels(im):return sha(im.tobytes())
def image_data(im):
    gray=im.convert("L").resize((64,64),Image.Resampling.BICUBIC)
    return {"ahash":a15.ahash(im),"dhash":dhash(im),"gray":list(gray.getdata())}
def block_ssim(x,y):
    # Non-overlapping 8x8 blocks, population moments, L=255; exploratory only.
    need(len(x)==len(y)==4096,"SSIM_SHAPE")
    scores=[]
    for r in range(0,64,8):
        for c in range(0,64,8):
            a=[x[i*64+k] for i in range(r,r+8) for k in range(c,c+8)]
            b=[y[i*64+k] for i in range(r,r+8) for k in range(c,c+8)]
            m=statistics.mean(a);n=statistics.mean(b)
            va=sum((v-m)**2 for v in a)/64;vb=sum((v-n)**2 for v in b)/64
            cov=sum((v-m)*(w-n) for v,w in zip(a,b))/64
            scores.append((2*m*n+6.5025)*(2*cov+58.5225)/((m*m+n*n+6.5025)*(va+vb+58.5225)))
    return sum(scores)/64
def bounds(points,size=(640,480)):
    need(points and all(math.isfinite(v) for p in points for v in p),"ROI_NONFINITE")
    b=(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
    need(0<=b[0]<b[2]<size[0] and 0<=b[1]<b[3]<size[1],"ROI_OUTSIDE")
    return b
def crop_box(b,size=(640,480)):
    bounds([(b[0],b[1]),(b[2],b[3])],size)
    return (math.floor(b[0]),math.floor(b[1]),math.ceil(b[2]),math.ceil(b[3]))
def project(world,cam,k):
    p=a15.rotate(a15.q_inv(a15.norm_q(cam)),tuple(a-b for a,b in zip(world,a15.xyz(cam))))
    need(p[0]>.05,"ROI_CAMERA_DEPTH")
    return (k[2]-k[0]*p[1]/p[0],k[5]-k[4]*p[2]/p[0])
def pose_at_and_trace(data,names):
    t0=a15.T0_NS;end=a15.END_NS; step=100_000_000
    frames=defaultdict(dict)
    for r in csv.DictReader(io.StringIO(data.decode()),delimiter="\t"):
        t=int(r["sim_ns"]);n=r["entity"]
        if t0<=t<=end and (t-t0)%step==0 and n in names:
            need(n not in frames[t],"POSE_DUPLICATE")
            p={k:float(r[k]) for k in ("x","y","z","qx","qy","qz","qw")}
            need(all(math.isfinite(v) for v in p.values()),"POSE_NONFINITE");a15.norm_q(p);frames[t][n]=p
    need(set(frames)==set(range(t0,end+1,step)) and all(set(f)==set(names) for f in frames.values()),"TRACE_GRID")
    trace={n:[] for n in names if n.startswith("dish_")}
    for t in sorted(frames):
        f=frames[t]
        for n in trace:
            p,_=a15.relative(f["tray_platform"],f[n]);trace[n].append([t,*p])
    return frames[t0],trace
def intersect(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
def adapt(f,version,scene,pin,prior=None):
    d,c,iv,v=[j(f[n]) for n in (version+"_design.json","capture.json","initial_validity.json","verdict.json")]
    expected=a15.A15_SHA if version=="a15" else a16.PIN
    need(d["scene_id"]==v["scene_id"]==scene and d["source_sha"]==v["source_sha"]==expected,"SCENE_SOURCE")
    need(d["human_approved"] is False and v["human_approved"] is False and v["ground_truth"]=="UNKNOWN_HOLD" and d["rule_candidate"]=="UNKNOWN","GT_BOUNDARY")
    need(v["production_contact_health"]=="HOLD" and v["cleanup"]=="FAIL" and any(p["role"]=="server" and p["returncode"]==-11 for p in v["processes"]),"CONTACT_CLEANUP_BOUNDARY")
    need(d["world_sha256"]==sha(f["scenario.sdf"]),"SDF_SHA")
    geom=a15.geometry_provenance(d) if version=="a15" else a16.geometry(d,f["scenario.sdf"])
    family=d["geometry_family_id"];layout=d["physical_layout_id"]
    need(layout==d["stack_id"],"LAYOUT_STACK")
    info=c["camera_info"];k=info["k"]
    need(c["stamp_ns"]==info["stamp_ns"]==a15.T0_NS and c["encoding"]=="rgb8" and info["width"]==640 and info["height"]==480 and len(k)==9 and all(math.isfinite(x) for x in k) and k[0]>0 and k[4]>0,"CAMERA")
    need(all(abs(x)<1e-12 for x in info.get("d",[])),"DISTORTION_UNSUPPORTED")
    png=f["tray_rgb_t0.png"];need(sha(png)==c["image_sha256"],"IMAGE_SHA")
    with Image.open(io.BytesIO(png)) as src:
        need(src.format=="PNG" and src.mode=="RGB" and src.size==(640,480),"RGB_FORMAT");src.load();im=src.copy()
    px=pixels(im);ah=a15.ahash(im);hamming(ah,ah)
    if version=="a15":
        need(c["image_sha256"]==a15.EXPECTED_IMAGES[scene],"A15_PINNED_IMAGE")
    else:
        need(prior is not None and prior["scene_id"]==scene and prior["archive_sha256"]==pin and prior["trial_id"]==d["trial_id"] and prior["geometry"]["layout"]==layout and prior["geometry"]["family"]==family and prior["image_sha256"]==c["image_sha256"] and prior["pixel_sha256"]==px and prior["ahash"]==ah,"QA04_SCENE_LINK")
    ds=d["initial_dishes"];names=["tray_platform","camera"]+[x["name"] for x in ds]
    frame,trace=pose_at_and_trace(f["poses.tsv"],names)
    root=ET.fromstring(f["scenario.sdf"])
    models={m.get("name"):m for m in root.findall("./world/model")}
    tray=models["tray_platform"];visual=tray.find("link/visual")
    need(visual is not None and visual.find("geometry/box/size") is not None,"TRAY_BOX")
    for e in (tray.find("link/pose"),visual.find("pose")):
        need(e is None or all(abs(float(x))<1e-12 for x in e.text.split()),"TRAY_LOCAL_OFFSET_UNSUPPORTED")
    w,dep,th=map(float,visual.findtext("geometry/box/size").split())
    need(w>0 and dep>0 and th>0 and abs(w-d["platform"]["width_m"])<1e-8 and abs(dep-d["platform"]["depth_m"])<1e-8,"TRAY_DIMENSIONS")
    tp=frame["tray_platform"];cam=frame["camera"]
    corners=[]
    for x,y,z in itertools.product((-w/2,w/2),(-dep/2,dep/2),(-th/2,th/2)):
        rot=a15.rotate(a15.norm_q(tp),(x,y,z));world=tuple(a+b for a,b in zip(a15.xyz(tp),rot))
        corners.append(project(world,cam,k))
    traybox=bounds(corners)
    fn=a15.visibility_geometry if version=="a15" else a16.visibility_geometry
    dishboxes=fn(f["poses.tsv"],d,iv,info)
    dishbox=bounds([(b[i],b[i+1]) for b in dishboxes.values() for i in (0,2)])
    rois={"full":im,"tray":im.crop(crop_box(traybox)),"dish":im.crop(crop_box(dishbox))}
    rel={n:trace[n][0][1:] for n in trace}
    top,lower=ds[-1],ds[-2];p=rel[top["name"]];q=rel[lower["name"]]
    offset=[p[i]-q[i] for i in range(2)];off=math.hypot(*offset)
    margins=lower["radius_m"]-top["radius_m"]-off
    colors=[]
    for x in ds:
        m=models[x["name"]];g=m.find("link/visual/geometry/cylinder")
        need(g is not None and abs(float(g.findtext("radius"))-x["radius_m"])<1e-8 and abs(float(g.findtext("length"))-x["thickness_m"])<1e-8,"DISH_SDF_GEOMETRY")
        colors.append(m.findtext("link/visual/material/diffuse") or "UNKNOWN")
    metrics=v["metrics"] if version=="a15" else prior["metrics"]
    upper=metrics[top["name"]]["max_relative_displacement_m"]
    obs="POSITION_MAINTAINED" if upper<=1e-8 else "LARGE_DISPLACEMENT" if upper>=.1 else "OTHER_OBSERVED"
    overlaps=[{"pair":[n,m],"bbox_intersection_px2":intersect(b,dishboxes[m])} for n,b in dishboxes.items() for m in dishboxes if n<m]
    bg=root.findtext("./world/scene/background") or "UNKNOWN"
    annotated=im.copy();draw=ImageDraw.Draw(annotated);draw.rectangle(traybox,outline="cyan",width=2);draw.rectangle(dishbox,outline="yellow",width=2)
    for n,b in dishboxes.items():draw.rectangle(b,outline="magenta",width=1);draw.text((b[0],b[1]),n,fill="white")
    buf=io.BytesIO();annotated.save(buf,format="PNG")
    record={"scene_id":scene,"trial_id":d["trial_id"],"layout":layout,"family":family,"stack_id":d["stack_id"],"seed":d["seed"],"version":version,"environment":d["environment_profile_id"],"source_environment":"OWNER_WSL2","inner_sha":pin,"image_sha":c["image_sha256"],"pixel_sha":px,"dish_count":len(ds),"dishes":ds,"relative_t0_xyz_m":rel,"stack_height_nominal_m":sum(x["thickness_m"] for x in ds),"upper_center_distance_m":math.hypot(*p[:2]),"offset_xy_m":offset,"offset_m":off,"nominal_support_margin_m":margins,"torque_world_nm":d["trigger"]["torque_nm"],"colors":colors,"background":bg,"camera_pose":cam,"brightness":statistics.mean(ImageStat.Stat(im.convert("L")).mean),"dish_bbox_area_px2":(dishbox[2]-dishbox[0])*(dishbox[3]-dishbox[1]),"tray_bbox":traybox,"dish_bbox":dishbox,"dish_bboxes":dishboxes,"bbox_overlap":overlaps,"visibility":"BBOX_ONLY_NOT_SEGMENTATION","support":iv["support"],"settle":iv["dishes"],"trigger":d["trigger"],"end_ns":d["end_ns"],"metrics":metrics,"observation":obs,"contact_health":"HOLD","cleanup":"FAIL","gt":"UNKNOWN_HOLD","human_approved":False,"training_eligible":False}
    return record,{n:image_data(v) for n,v in rois.items()},buf.getvalue(),trace
def unique_layouts(records):
    groups=defaultdict(list)
    for r in records:groups[r["layout"]].append(r)
    return groups
def similarity(items):
    rows=[]
    for a,b in itertools.combinations(items,2):
        r={"a":a[0]["scene_id"],"b":b[0]["scene_id"],"same_pixel":a[0]["pixel_sha"]==b[0]["pixel_sha"],"same_file":a[0]["image_sha"]==b[0]["image_sha"]}
        for region in REGIONS:
            x,y=a[1][region],b[1][region]
            r.update({region+"_ahash":hamming(x["ahash"],y["ahash"]),region+"_dhash":hamming(x["dhash"],y["dhash"]),region+"_block_ssim":block_ssim(x["gray"],y["gray"])})
        rows.append(r)
    return rows
def risks(records):
    fields={
      "center_0.05m":lambda r:"near" if r["upper_center_distance_m"]<=.05 else "offset",
      "dish_count":lambda r:str(r["dish_count"]),"family":lambda r:r["family"],"version":lambda r:r["version"],
      "height_0.1m":lambda r:"low" if r["stack_height_nominal_m"]<=.1 else "high",
      "color_sequence":lambda r:"|".join(r["colors"]),"brightness_16bin":lambda r:str(int(r["brightness"]//16)),
      "dish_bbox_2000px2":lambda r:str(int(r["dish_bbox_area_px2"]//2000)),
      "offset_0.03m":lambda r:"small" if r["offset_m"]<=.03 else "large",
      "signed_offset_x":lambda r:"positive" if r["offset_xy_m"][0]>1e-6 else "negative" if r["offset_xy_m"][0]<-1e-6 else "zero",
      "support_margin":lambda r:"positive" if r["nominal_support_margin_m"]>0 else "nonpositive",
      "environment":lambda r:r["environment"],"background":lambda r:r["background"],
      "camera":lambda r:json.dumps({k:round(v,6) for k,v in r["camera_pose"].items()},sort_keys=True),
      "torque":lambda r:str(r["torque_world_nm"])}
    out=[]
    for field,fn in fields.items():
        cells=defaultdict(Counter)
        for r in records:cells[fn(r)][r["observation"]]+=1
        pure=sum(max(c.values()) for c in cells.values());total=len(records)
        category="PHYSICAL_OR_PROXY" if field in ("center_0.05m","dish_count","family","height_0.1m","offset_0.03m","signed_offset_x","support_margin","torque") else "POTENTIAL_NUISANCE_OR_PROXY"
        for k,c in sorted(cells.items()):
            out.append({"variable":field,"category":category,"value":k,"counts":json.dumps(c,sort_keys=True),"n":sum(c.values()),"pure_cell":len(c)==1,"exploratory_in_sample_purity":pure/total,"status":"FIXED_UNTESTABLE" if len(cells)==1 else "DESCRIPTIVE_ONLY"})
    # explicit crossing cells, absent combinations remain zero.
    for fam,center,sign in itertools.product(sorted({r["family"] for r in records}),("near","offset"),("negative","zero","positive")):
        c=Counter(r["observation"] for r in records if r["family"]==fam and fields["center_0.05m"](r)==center and fields["signed_offset_x"](r)==sign)
        out.append({"variable":"family_x_center_x_signed_offset","category":"PHYSICAL_CROSS","value":fam+"|"+center+"|"+sign,"counts":json.dumps(c,sort_keys=True),"n":sum(c.values()),"status":"OBSERVED" if c else "MISSING_COMBINATION"})
    return out
def split_feasibility(records,pairs):
    groups=unique_layouts(records);families=defaultdict(set);obs=defaultdict(set)
    for r in records:families[r["family"]].add(r["layout"]);obs[r["observation"]].add(r["layout"])
    labels=sorted(obs);fs=sorted(families);valid=0;checked=0
    # Hypothetical observations only; count partitions, never export assignments.
    for choices in itertools.product(range(3),repeat=len(fs)):
        if len(set(choices))!=3:continue
        checked+=1
        bins=[set().union(*(families[f] for f,c in zip(fs,choices) if c==i)) for i in range(3)]
        if all(all(b&obs[k] for k in labels) for b in bins):valid+=1
    return {"scope":"NON_RELEASED_SIMULATION","layout_groups":len(groups),"family_groups":len(families),"observed_layout_counts":{k:len(v) for k,v in obs.items()},"family_partition_candidates":checked,"family_partitions_with_every_observation_in_each_split":valid,"exact_duplicate_review_pairs":sum(p["same_pixel"] for p in pairs),"near_review_pairs":sum(p["dish_ahash"]<=8 or p["tray_ahash"]<=8 for p in pairs),"approved_groups":0,"minimum_approved_groups_per_label":3,"released":False}
def write_csv(path,rows):
    need(bool(rows),"EMPTY_OUTPUT")
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open("x",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,tuple)) else v for k,v in r.items()})
def trace_svg(trace):
    lines=[]
    for i,(n,ps) in enumerate(trace.items()):
        p0=ps[0][1:];coords=[(p[0],math.dist(p[1:],p0)) for p in ps]
        pts=" ".join(f"{35+(t-a15.T0_NS)/(a15.END_NS-a15.T0_NS)*560:.2f},{160-min(v,2)/2*135:.2f}" for t,v in coords)
        color=["#2463a6","#d45335","#19875b"][i%3]
        lines.append(f'<polyline fill="none" stroke="{color}" points="{pts}"/><text x="{40+i*145}" y="18" fill="{color}">{html.escape(n)}</text>')
    return '<svg viewBox="0 0 640 190" width="640"><path d="M35 25V160H595" fill="none" stroke="gray"/><text x="2" y="30">2m</text><text x="3" y="160">0</text><text x="35" y="180">2s</text><text x="550" y="180">12.3s</text>'+''.join(lines)+'</svg>'
def workbook(out,items,pairs):
    worksheet=[];sections=[]
    for r,_,png,trace in items:
        n=r["scene_id"];related=sorted((p for p in pairs if n in (p["a"],p["b"])),key=lambda p:p["dish_ahash"])[:4]
        worksheet.append({"scene_id":n,"layout":r["layout"],"initial_placement":"","occlusion":"","physics_validity":"","learning_suitability":"","license_status":"","gt_decision":"","reviewer":"","reason":""})
        safe=html.escape(json.dumps({k:r[k] for k in ("dishes","relative_t0_xyz_m","support","settle","trigger","metrics","bbox_overlap","contact_health","cleanup","observation")},ensure_ascii=False,indent=2))
        sections.append(f'<section><h2>{html.escape(n)}</h2><img alt="t0 ROI overlay" width="640" src="data:image/png;base64,{base64.b64encode(png).decode()}"><p>cyan tray; yellow dish union; magenta conservative boxes; not masks. User A16 visual review is not GT approval.</p>{trace_svg(trace)}<p>100ms display only; full physical metrics reused from accepted evidence.</p><pre>{safe}</pre><p>Similar pairs: {html.escape(json.dumps(related))}</p><p>Human decisions: blank — use accompanying CSV.</p></section>')
    write_csv(out/"review_worksheet.csv",worksheet)
    (out/"review_workbook.html").write_text('<!doctype html><meta charset="utf-8"><title>QA05 private REVIEW_ONLY</title><style>body{font:16px sans-serif;margin:2rem;max-width:900px}section{border-top:1px solid #aaa;padding:1rem}pre{white-space:pre-wrap}img{max-width:100%}</style><h1>QA05 private REVIEW_ONLY</h1>'+''.join(sections),encoding="utf8")
def audit(paths,out):
    # Exact accepted archives; do not rerun expensive full physics audit.
    blobs={k:get(paths[k],*spec) for k,spec in INPUTS.items()}
    q=a16.read_tar(blobs["qa04"],QA04_SHA,allowed={"qa_report.json","review_worksheet.csv","diagnostic_status.json"})
    need(sha(q["qa_report.json"])==QA04_REPORT,"QA04_REPORT_SHA");prior=j(q["qa_report.json"]);status=j(q["diagnostic_status.json"])
    need(status["verifier_sha"]==QA04_PIN and status["exit_code"]==0 and prior["actual_owner_raw_directly_recomputed"] and prior["owner_sha256"]==a16.OWNER and prior["a15_owner_sha256"]==a15.OWNER_SHA and prior["diagnostics_sha256"]==a16.DIAG and prior["a15_direct_audit"] and prior["approved_count"]==0,"QA04_LINK")
    prior_map={r["scene_id"]:r for r in prior["scenes"]};need(set(prior_map)==set(a16.SCENES),"QA04_SCENES")
    old=a15.read_tar(blobs["a15"],a15.OWNER_SHA);new=a16.read_tar(blobs["a16"],a16.OWNER,allowed=a16.OUTER)
    diag=a16.read_tar(blobs["a16_diag"],a16.DIAG,allowed=a16.DIAGNOSTICS)
    need(j(new["batch_status.json"])==j(diag["batch_status.json"]),"A16_BATCH_DIAG_LINK")
    items=[]
    for version,outer,pins in (("a15",old,a15.INNER_SHA),("a16",new,a16.INNER)):
        for n,pin in pins.items():
            k=n+"/"+version+"_raw.tar.gz";a15.verify_sidecar(outer[k],outer[k+".sha256"],version+"_raw.tar.gz",pin)
            f=a15.read_tar(outer[k],pin,inner=True) if version=="a15" else a16.read_tar(outer[k],pin,allowed=a16.RAW)
            items.append(adapt(f,version,n,pin,prior_map.get(n)))
    records=[x[0] for x in items];pairs=similarity(items)
    need(len(records)==12 and len(unique_layouts(records))==12 and len({r["family"] for r in records})==4 and len(pairs)==66,"INVENTORY_COUNT")
    need(len({r["pixel_sha"] for r in records})==12,"PIXEL_DUPLICATE_DRIFT")
    write_csv(out/"geometry_inventory.csv",records);write_csv(out/"similarity_matrix.csv",pairs)
    for region in REGIONS:
        for metric in ("ahash","dhash","block_ssim"):
            col=region+"_"+metric;lookup={tuple(sorted((r["a"],r["b"]))):r[col] for r in pairs}
            ids=[r["scene_id"] for r in records]
            write_csv(out/(col+"_12x12.csv"),[{"scene_id":a,**{b:(1 if metric=="block_ssim" else 0) if a==b else lookup[tuple(sorted((a,b)))] for b in ids}} for a in ids])
    near=sorted(pairs,key=lambda x:(x["dish_ahash"],x["dish_dhash"],-x["dish_block_ssim"]))
    write_csv(out/"near_review_pairs.csv",near)
    stats={r:{str(t):sum(x[r+"_ahash"]<=t for x in pairs) for t in (0,4,8,12)} for r in REGIONS}
    prior_pairs={tuple(sorted(x["pair"])):x["hamming"] for x in prior["near_duplicate_review_candidates"]}
    current={tuple(sorted((p["a"],p["b"]))):p["full_ahash"] for p in pairs if p["full_ahash"]<=8}
    roi={"scope":"EXPLORATORY_NOT_DUPLICATE_VERDICT","pair_count":len(pairs),"ahash_threshold_counts":stats,"qa04_full_ahash_matches":current==prior_pairs,"qa04_full_ahash_mismatches":[{"pair":k,"prior":prior_pairs.get(k),"current":current.get(k)} for k in sorted(set(prior_pairs)|set(current)) if prior_pairs.get(k)!=current.get(k)],"methods":"Pillow aHash legacy default; dHash BICUBIC 9x8; block SSIM grayscale BICUBIC 64x64 nonoverlap 8x8 population; rectangular crops; no masks"}
    (out/"roi_similarity_report.json").write_text(json.dumps(roi,indent=2))
    write_csv(out/"shortcut_risk_matrix.csv",risks(records))
    split=split_feasibility(records,pairs);(out/"group_split_feasibility.json").write_text(json.dumps(split,indent=2))
    workbook(out,items,pairs)
    return {"scope":"B_QA05_REVIEW_ONLY","actual_12_scene_roi_review":True,"previous_physics_reused":True,"input_sha":{k:v[1] for k,v in INPUTS.items()},"qa04_verifier":QA04_PIN,"scenes":len(records),"layouts":len(unique_layouts(records)),"families":len({r["family"] for r in records}),"observations":dict(Counter(r["observation"] for r in records)),"roi":roi,"split":split,"gates":{f"B-Q0{i}":"PASS" if i==1 else "HOLD" for i in range(1,8)},"ground_truth":"UNKNOWN_HOLD","approved_count":0,"training_eligible":False,"model_training_executed":False,"production_contact_health":"HOLD","cleanup":"FAIL","product_approval":False}
