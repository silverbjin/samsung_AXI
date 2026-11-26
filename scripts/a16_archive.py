"""A16 explicit archive allowlists; raw and diagnostic archives separate."""
import hashlib,json,sys,tarfile
from pathlib import Path
from smartdish_platform.evidence import sha256,verify_archive
from a16_pilot_world import SCENES,VERSION,PLATFORM_SHA
RAW={"a16_design.json","scenario.sdf","a14_contact_bridge.yaml","poses.tsv","trigger.tsv","entity_registry.tsv","ecm_contact_steps.tsv","native_contacts.tsv","ros_contacts.jsonl","capture.json","tray_rgb_t0.png","initial_validity.json","clock_rgb_trace.json","topic_qos.json","verdict.json"}
LOGS={"server.log","gui.log","rgb_bridge.log","contact_bridge.log","native_contact.log"}
def bundle(root,paths,name):
    root=Path(root).resolve()
    files={}
    for item in paths:
        p=root/item
        if not p.exists():continue
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root) or Path(item).is_absolute() or ".." in Path(item).parts:
            raise ValueError("A16_ARCHIVE_UNSAFE_PATH")
        files[str(item)]=p
    if not files:raise ValueError("A16_ARCHIVE_EMPTY")
    lines="".join(sha256(p)+"  "+n+"\n" for n,p in sorted(files.items()))
    target=root/name
    import io
    data=lines.encode()
    with tarfile.open(target,"x:gz") as t:
        for n,p in sorted(files.items()):t.add(p,arcname=n,recursive=False)
        m=tarfile.TarInfo("SHA256SUMS");m.size=len(data);t.addfile(m,io.BytesIO(data))
    digest=sha256(target)
    verify_archive(target,digest)
    with (root/(name+".sha256")).open("x") as f:f.write(digest+"  "+name+"\n")
    return digest
def scene_package(out):
    digest=bundle(out,RAW,"a16_raw.tar.gz")
    print("A16_RAW_SHA256="+digest,flush=True)
    return digest
def batch(root,pin,mode,rc):
    p=Path(root);scenes={};raw=[];logs=[]
    for s in SCENES:
        d=p/s;v=d/"verdict.json"
        row=json.loads(v.read_text()) if v.is_file() else {"data_verdict":"NOT_RUN_OR_INTERRUPTED"}
        tar=d/"a16_raw.tar.gz"
        if tar.is_file():
            row["archive_sha256"]=sha256(tar)
            raw.extend([s+"/a16_raw.tar.gz",s+"/a16_raw.tar.gz.sha256"])
        elif d.is_dir():
            # Retain partial files if collector was terminated before its finally.
            raw.extend(s+"/"+n for n in sorted(RAW) if (d/n).is_file())
        scenes[s]=row
        logs.extend(s+"/"+n for n in sorted(LOGS) if (d/n).is_file())
        logs.append(s+".log")
    summary={"schema":2,"source_sha":pin,"producer_version":VERSION,"platform_sha":PLATFORM_SHA,"source_class":"CLOUD_CI" if mode=="--ci" else "OWNER_WSL2","exit_code":rc,"scenes":scenes,"ground_truth":"UNKNOWN_HOLD","human_approved":False,"training_eligible":False,"production_contact_health":"HOLD","visual_review":"USER_ONLY_NOT_AUTOMATIC_GATE"}
    with (p/"batch_status.json").open("x") as f:json.dump(summary,f,indent=2,sort_keys=True);f.write("\n")
    digest=bundle(p,["batch_status.json",*raw],"a16_pilot_evidence.tar.gz")
    diag=bundle(p,["batch_status.json","preflight.json","contrast.json","cleanup_probe.json","cleanup_probe_server.log","cleanup_probe_bridge.log","cleanup_probe.sdf","build_pose.log","build_health.log",*logs],"a16_pilot_diagnostics.tar.gz")
    print("A16_EVIDENCE_ARCHIVE="+str(p/"a16_pilot_evidence.tar.gz"));print("A16_EVIDENCE_SHA256="+digest)
    print("A16_DIAGNOSTICS_ARCHIVE="+str(p/"a16_pilot_diagnostics.tar.gz"));print("A16_DIAGNOSTICS_SHA256="+diag)
if __name__=="__main__":batch(sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]))
