"""P4 release: reviewed Cloud P3 evidence, unchanged production core, strict Owner gate."""
import json,sys,tarfile,tempfile,re,subprocess
from pathlib import Path
from smartdish_platform.evidence import sha256,verify_archive
from a18_pilot_world import design,phase_scenes,REGISTRY,VERSION,PLATFORM_SHA
P1_PIN="fd44ac7e9cca56c774bec810c438382219a786b1"
P1_RAW="525549fd7d5e12a0c8c28e397aab555d7ed0a423fc420d20487c8bd74d3674aa"
P1_DIAG="71dd06b5f2b0c4a2afd82ac8585701c0f22fb7ab9b6098032a1c284a8a6e9840"
CORE=("scripts/a18_pilot_world.py","scripts/a18_pilot_collect.py","scripts/a18_pilot_contract.py","config/smartdish_a18_layouts.json","scripts/a17_production_profile.py","scripts/a16_pilot","scripts/a14_physics_freshness","scripts/a16_diagnostics.py","scripts/a14_production_health_probe.py","scripts/smartdish_platform")
def need(ok,msg):
    if not ok:raise ValueError("A18_PHASE_GATE_"+msg)
def verify_core(root,pin):
    root=Path(root)
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()
    need(git("rev-parse","HEAD")==pin,"HEAD")
    if git("rev-parse","--is-shallow-repository")=="true":
        subprocess.run(["git","-C",str(root),"fetch","--no-tags","--depth=1","origin",P1_PIN],check=True,timeout=60)
    else:
        subprocess.run(["git","-C",str(root),"merge-base","--is-ancestor",P1_PIN,pin],check=True,timeout=15)
    need(subprocess.run(["git","-C",str(root),"diff","--quiet",P1_PIN,pin,"--",*CORE],timeout=20).returncode==0,"CORE_DRIFT")
def owner_row(v):
    need(v.get("data_verdict")==v.get("cleanup")=="PASS" and v.get("all_owned_stopped") is True and v.get("human_approved") is False and v.get("training_eligible") is False and v.get("ground_truth")=="UNKNOWN_HOLD" and v.get("production_contact_health")=="HOLD","OWNER_VERDICT")
    p=v.get("server_runtime_profile",{})
    need(p.get("profile")=="wsl_d3d12_retention_v1" and p.get("production_cleanup")=="PASS" and p.get("runtime_observation") and p.get("runtime_observation_pre_shutdown"),"OWNER_PROFILE")
    roles=[x for x in v["processes"] if x["role"]!="gui"]
    need({x["role"] for x in roles}=={"server","native_contact","rgb_bridge","contact_bridge"} and len(roles)==4,"OWNER_ROLES")
    need(all(x.get("returncode")==0 and x.get("stopped") is True and x.get("process_group_remaining") is False for x in roles),"OWNER_EXIT")
    need(next(x for x in roles if x["role"]=="server").get("signals")==[2],"OWNER_SERVER_SIGNAL")
def verify_owner(path,pin):
    p=Path(path);side=Path(str(p)+".sha256")
    need(p.is_file() and side.is_file(),"OWNER_ARCHIVE_REQUIRED")
    tokens=side.read_text().split()
    need(len(tokens)==2 and tokens[1]==p.name and re.fullmatch("[0-9a-f]{64}",tokens[0]),"OWNER_SIDECAR")
    verify_archive(p,tokens[0])
    def read(t,n):return t.extractfile(n).read()
    with tarfile.open(p,"r:gz") as t:
        b=json.loads(read(t,"batch_status.json"))
        need(b["source_sha"] in (pin,P1_PIN) and b["phase"]==1 and b["source_class"]=="OWNER_WSL2" and b["producer_version"]==VERSION and b["platform_sha"]==PLATFORM_SHA and b["exit_code"]==0 and b["planned_scenes"]==list(phase_scenes(1)) and set(b["scenes"])==set(phase_scenes(1)),"OWNER_BATCH")
        for s in phase_scenes(1):
            n=s+"/a18_raw.tar.gz";blob=read(t,n);h=b["scenes"][s]["archive_sha256"];side=read(t,n+".sha256").decode().split()
            need(side==[h,"a18_raw.tar.gz"],"OWNER_INNER_SIDECAR")
            with tempfile.TemporaryDirectory(prefix="a18_verify_") as td:
                q=Path(td)/"a18_raw.tar.gz";q.write_bytes(blob);verify_archive(q,h)
                with tarfile.open(q,"r:gz") as inner:
                    v=json.loads(read(inner,"verdict.json"));d=json.loads(read(inner,"a18_design.json"));e=design(s)
                    need(v=={k:x for k,x in b["scenes"][s].items() if k!="archive_sha256"},"OWNER_NESTED_VERDICT")
                    owner_row(v)
                    need(d["source_sha"]==b["source_sha"] and d["source_class"]=="OWNER_WSL2" and d["scene_id"]==s and d["physical_layout_id"]==e["physical_layout_id"] and d["physical_fingerprint"]==e["physical_fingerprint"] and d["registry_sha256"]==sha256(REGISTRY),"OWNER_IDENTITY")
    return {"owner_phase1_archive_sha256":tokens[0],"owner_phase1_source_sha":b["source_sha"]}
def main():
    root,pin,mode,previous,out=sys.argv[1:]
    verify_core(root,pin)
    record={"scope":"P3_CLOUD_REVIEW_GATE_P4_ONLY","phase1_cloud_source":P1_PIN,"phase1_cloud_raw_sha256":P1_RAW,"phase1_cloud_diag_sha256":P1_DIAG,"core_unchanged":True,"owner_gate":"NOT_APPLICABLE_CLOUD"}
    if mode!="--ci":
        record.update(verify_owner(previous,pin));record["owner_gate"]="PASS"
    Path(out).write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print("A18_PHASE2_GATE_PASS")
if __name__=="__main__":main()
