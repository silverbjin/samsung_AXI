"""Independent E artifact reader using B actual physical replay and raw stop evidence.
No ROS or A control imports. Never use historical A session IDs for E.
"""
import argparse,hashlib,json,math,re,shutil,tarfile,tempfile
from pathlib import Path
from PIL import Image
import smartdish_b_product_evidence_qa as b
from smartdish_e_product_odom import audit,ns,MAX_GAP_NS,PROFILE

def need(ok,reason):b.need(ok,reason)
def sha(p):return b.sha(p)
def js(p):return b.js(p)
def lines(p):return [json.loads(x) for x in Path(p).open()]
def one(values,reason):
    need(len(values)==1,reason)
    return values[0]

def intake(tar,sidecar,dst):
    """Original TAR + sidecar + exact full internal hash index; bounded safe extraction."""
    digest=sha(tar)
    need(Path(sidecar).read_text().split()[0]==digest,"E_TAR_SHA")
    seen=set();total=0
    with tarfile.open(tar,"r:gz") as archive:
        for m in archive:
            need(b.safe_name(m.name) and m.name not in seen and (m.isfile() or m.isdir()) and not m.issparse(),"E_TAR_MEMBER")
            need(m.name.split("/")[0]=="a04_live","E_TAR_ROOT")
            seen.add(m.name);total+=m.size
            need(total<1_000_000_000 and len(seen)<3000 and m.size<=400_000_000,"E_TAR_LIMIT")
            p=Path(dst)/m.name
            if m.isdir():p.mkdir(parents=True,exist_ok=True)
            else:
                p.parent.mkdir(parents=True,exist_ok=True)
                with p.open("xb") as f:shutil.copyfileobj(archive.extractfile(m),f)
                need(p.stat().st_size==m.size,"E_TAR_MEMBER_SIZE")
    root=Path(dst)/"a04_live";index={}
    for line in (root/"SHA256SUMS").read_text().splitlines():
        h,n=line.split("  ",1);n=n.removeprefix("./")
        need(b.safe_name(n) and n not in index and re.fullmatch("[0-9a-f]{64}",h),"E_INDEX")
        need(sha(root/n)==h,"E_INTERNAL_SHA")
        index[n]=h
    actual={x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file()}-{"SHA256SUMS"}
    need(set(index)==actual,"E_INDEX_SET")
    return root,dict(tar_sha256=digest,internal_files=len(index))

def wait_review(odom,d_events,rid):
    """D publishes repeated countdown status; use first actual entry, not last heartbeat."""
    d_events=[r for r in d_events if r["body"].get("request_id")==rid]
    need(all(x["steady_ns"]<=y["steady_ns"] for x,y in zip(d_events,d_events[1:])),"D_EVENT_ORDER")
    results=[]
    for waiting,operation,duration in (("WAIT_LOADING","LOAD",10),("WAIT_UNLOADING","UNLOAD",5)):
        starts=[r for r in d_events if r["topic"]=="/collection/status" and r["body"].get("state")==waiting]
        end=one([r for r in d_events if r["topic"]=="/collection/dish_transfer_request" and r["body"].get("operation")==operation],"D_TRANSFER_REQUEST_COUNT")
        need(starts,"D_WAIT_STATE_MISSING")
        a,z=starts[0]["steady_ns"],end["steady_ns"]
        need(all(a<=r["steady_ns"]<=z for r in starts) and z-a>=duration*10**9,"D_WAIT_TOO_SHORT")
        # No intervening other state before the expected LOADING/UNLOADING transition.
        states=[r["body"]["state"] for r in d_events if a<=r["steady_ns"]<=z and r["topic"]=="/collection/status"]
        need(states[-1]==("LOADING" if operation=="LOAD" else "UNLOADING") and set(states[:-1])=={waiting},"D_WAIT_STATE_ORDER")
        samples=[r for r in odom if not r["duplicate"] and r["steady_ns"]<=z]
        before=[i for i,r in enumerate(samples) if r["steady_ns"]<=a]
        need(before,"WAIT_ODOM_START_MISSING")
        window=samples[before[-1]:]
        need(a-window[0]["steady_ns"]<=MAX_GAP_NS and z-window[-1]["steady_ns"]<=MAX_GAP_NS and
             all(0<y["steady_ns"]-x["steady_ns"]<=MAX_GAP_NS for x,y in zip(window,window[1:])) and
             all(math.hypot(*r["linear"])<=.01 and math.hypot(*r["angular"])<=.02 for r in window),"B_WAIT_RAW_CONTINUITY")
        results.append(dict(operation=operation,wait_s=(z-a)/1e9,start_ns=a,steady_ns=z,request=end["body"],samples=len(window),status_heartbeats=len(starts)))
    return results

def capture_review(p,load,cap,ai,c):
    keys=("request_id","stack_id","transfer_id","capture_id","image_stamp_ns","rgb_sha256")
    need(all(cap[k]==ai[k]==c["request"][k] for k in keys),"CAPTURE_AI_ID")
    need(cap["request_id"]==load["request_id"] and cap["stack_id"]==load["stack_id"] and cap["transfer_id"]==load["transfer_id"],"CAPTURE_LOAD_ID")
    need(cap["status"]=="ACK" and cap["frame_id"]=="smartdish_tray_optical" and ai["inference_ok"] is True,"CAPTURE_AI_STATUS")
    b.check_rgb_order(cap["image_stamp_ns"],load["event_sim_ns"])
    directory=p/"product_receipts/captures"/hashlib.sha256(cap["capture_id"].encode()).hexdigest()
    rec=js(directory/"receipt.json")
    need(sha(directory/"receipt.json")==cap["receipt_sha256"] and rec["result"]=={k:v for k,v in cap.items() if k!="receipt_sha256"} and rec["load_receipt_sha256"]==load["receipt_sha256"],"CAPTURE_RECEIPT")
    packed=(directory/"frame.rgb").read_bytes();predict=(p/"c_input.rgb").read_bytes()
    need(len(packed)==640*480*3 and predict==packed and hashlib.sha256(predict).hexdigest()==cap["rgb_sha256"]==c["rgb_sha256"],"C_RGB_INPUT")
    with Image.open(directory/"frame.png") as image:need(image.mode=="RGB" and image.size==(640,480) and image.tobytes()==packed,"CAPTURE_PNG")
    need(sha(directory/"frame.png")==rec["png_sha256"],"PNG_SHA")
    raw=(p/"c_input_ros_bytes.bin").read_bytes();m=c["raw_metadata"]
    need(m["image_stamp_ns"]==cap["image_stamp_ns"] and m["frame_id"]==cap["frame_id"] and m["width"]==640 and m["height"]==480 and m["encoding"] in ("rgb8","bgr8") and m["step"]>=1920 and m["is_bigendian"] in (0,1) and len(raw)==m["step"]*480,"ROS_RAW_METADATA")
    need(hashlib.sha256(raw).hexdigest()==c["raw_sha256"],"ROS_RAW_SHA")
    canonical=b"".join(raw[i*m["step"]:i*m["step"]+1920] for i in range(480))
    if m["encoding"]=="bgr8":
        q=bytearray(canonical);q[0::3],q[2::3]=canonical[2::3],canonical[0::3];canonical=bytes(q)
    need(canonical==predict,"ROS_RAW_CANONICAL")
    need(c["invocation_count"]==1 and c["model_version"]==ai["model_version"],"C_INVOCATION_COUNT")
    # CI is explicitly an inference double; no private model claim or product model authorization.
    need(c["scope"]=="CI_DOUBLE_NOT_ACTUAL_MODEL" and c["private_model_loaded"] is False and c["model_version"]=="CI_DOUBLE_PRODUCT_E","CI_MODEL_SCOPE")
    return dict(scope=c["scope"],rgb_sha256=cap["rgb_sha256"],capture_id=cap["capture_id"],model_version=c["model_version"])

def review(root,repo,out,source,run):
    root=Path(root);p=root/"session";out=Path(out);out.mkdir(parents=True,exist_ok=True)
    e=js(p/"evidence.json");b.require_session(e,source,run)
    need((root/"source_sha.txt").read_text().strip()==source and (root/"upstream_sha.txt").read_text().strip()==b.UPSTREAM,"E_SOURCE_PIN")
    need(e["scope"]=="ACTUAL_E_SINGLE_WORLD_CI_C_PREDICTOR_DOUBLE" and e["verdict"]=="E_SINGLE_WORLD_CI_DOUBLE_L2_PASS" and e["first_error"] is None,"E_L2_NOT_GREEN")
    need(e["navigate_to_pose_goals_sent"]==3 and e["velocity_commands_published"]==0 and e["moving"]["nav_quiescent"],"GOAL_COUNT")
    # Original B actual geometric and exact ECM implementation, not runtime summary.
    geom,rc,floor,obs=b.geometry(p/"static",p)
    map_review=b.map_check(p/"static",Path(repo),floor,obs)
    paths=b.no_goal(p,e,floor,obs)
    phases=b.replay(p,e,rc,floor,obs,out,"E-"+str(run))
    need(len(phases)==3,"E_PHASE_COUNT")
    stop=audit(p/"raw_stop",source,str(run))
    need([x["goal_uuid"] for x in stop["legs"]]==[x["goal_uuid"] for x in e["moving"]["legs"]],"E_STOP_UUID")
    d_events=lines(p/"d_events.jsonl");dds=lines(p/"collection_dds.jsonl")
    topic=lambda k:[r["body"] for r in dds if r["topic"]==k]
    tx=topic("dish_transfer_result");need(len(tx)==2 and [x["operation"] for x in tx]==["LOAD","UNLOAD"],"TRANSFER_SEQUENCE")
    load,unload=tx
    ids=[int(x) for x in load["entity_ids"]];need(len(ids)==3 and len(set(ids))==3 and all(x>0 for x in ids),"DISH_IDS")
    b.verify_transfer(load,ids,3);b.verify_transfer(unload,ids,0)
    need(load["request_id"]==unload["request_id"] and load["stack_id"]==unload["stack_id"] and unload["event_sim_ns"]>load["event_sim_ns"] and load["transfer_id"]!=unload["transfer_id"],"TRANSFER_IDENTITY")
    waits=wait_review(lines(p/"raw_stop/odom_full.jsonl"),d_events,load["request_id"])
    journal=js(p/"product_receipts/transfers/transfer_journal.json");need(journal["locked"] is False,"JOURNAL_LOCK")
    a_events=lines(p/"product_receipts/a_runtime_events.jsonl")
    actual=[]
    for ack,wait,leg in zip(tx,waits,(e["moving"]["legs"][0],e["moving"]["legs"][1])):
        entry=journal["entries"][ack["transfer_id"]]
        need(entry["result"]==ack and entry["request"]==wait["request"],"JOURNAL_MISMATCH")
        file=p/"product_receipts/transfers"/(ack["receipt_sha256"]+".json");need(sha(file)==ack["receipt_sha256"],"TRANSFER_RECEIPT_SHA")
        rec=js(file);v=rec["evidence"]
        need(rec["result"]=={k:x for k,x in ack.items() if k!="receipt_sha256"},"TRANSFER_RECEIPT_BODY")
        need(v["source_sha"]==source and v["run_id"]==ack["stack_id"].split(":")[0] and v["world_sha256"]==e["world_sha256"],"TRANSFER_PROVENANCE")
        need(v["navigation"]["goal_uuid"]==leg["goal_uuid"] and v["navigation"]["stop_verified"],"TRANSFER_NAV_UUID")
        need(v["observation"]["event_sim_ns"]==ack["event_sim_ns"],"TRANSFER_SIM_TIME")
        log=p/"product_receipts"/v["service_receipt_dir"]/"gazebo_service_calls.jsonl"
        need(sha(log)==v["service_calls_sha256"],"SERVICE_SHA")
        service=b.service_review(log,ack["operation"],ids)
        published=one([x for x in a_events if x["event"]=="dish_transfer_result" and x["body"]==ack],"TRANSFER_A_PUBLISH")
        elapsed=(ns(published["steady_s"])-wait["steady_ns"])/1e9
        need(0<=elapsed<20 and ack["table_count"]==0,"TRANSFER_DEADLINE")
        actual.append(dict(operation=ack["operation"],ids=ids,elapsed_s=elapsed,service=service))
    cap=one(topic("capture_result"),"CAPTURE_COUNT");ai=one(topic("stability"),"AI_COUNT")
    model=capture_review(p,load,cap,ai,js(p/"c_predictor_receipt.json"))
    ui=js(p/"ui_events.json");approve=one([x for x in ui if x["event"]=="staff_confirm" and x["body"]["action"]=="APPROVE_CONTINUE"],"STAFF_APPROVAL_COUNT")
    need(approve["body"]["request_id"]==load["request_id"] and approve["body"]["capture_id"]==cap["capture_id"] and approve["body"]["stack_id"]==load["stack_id"],"STAFF_APPROVAL_ID")
    goals=[r for r in d_events if r["topic"]=="/collection/nav_goal"]
    need([x["body"]["leg"] for x in goals]==["TO_TABLE","TO_RETURN","TO_HOME"] and ns(approve["steady_s"])<goals[1]["steady_ns"],"STAFF_BEFORE_RETURN")
    need(js(p/"ui_result.json")["completed"] is True,"UI_COMPLETED")
    shutdown=b.shutdown(p,e)
    return dict(verdict="E_INDEPENDENT_CI_DOUBLE_PHYSICAL_QA_PASS",source_sha=source,run_id=run,
        geometry=geom,map=map_review,plans=paths,phases=phases,raw_stop=stop,waits=waits,transfers=actual,
        model=model,shutdown=shutdown,owner_l3="NOT_RUN",actual_private_model_loaded=False)

def main():
    p=argparse.ArgumentParser()
    for k in ("tar","sidecar","repo","out"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--source-sha",required=True);p.add_argument("--run-id",required=True);a=p.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root,manifest=intake(a.tar,a.sidecar,tmp)
        result=review(root,a.repo,a.out,a.source_sha,a.run_id)|{"archive":manifest}
        b.save(a.out/"e_independent_qa.json",result)
        print(result["verdict"])
if __name__=="__main__":main()
