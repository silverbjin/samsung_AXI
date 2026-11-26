#!/usr/bin/env python3
"""One native camera-only library lifetime mitigation candidate; no baseline rerun."""
import argparse,json,os,re,sys,stat
from pathlib import Path
from a17_cleanup_probe import cmd,make_world,probe
from a17_cleanup_contract import archive,dump,sha,ENV_KEYS
from a17_gpu_retention_contract import CORE,BASELINE_OWNER_SHA,BASELINE_PIXEL,server_override,evaluate
def main():
    p=argparse.ArgumentParser();p.add_argument("--sha",required=True);p.add_argument("--out",required=True,type=Path);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.out.resolve();out.mkdir(parents=True,exist_ok=False,mode=0o700)
    report={"scope":"A17_GPU_RETENTION_MINIMAL_ONLY","source_sha":a.sha,"baseline_owner_sha":BASELINE_OWNER_SHA,"baseline_native_rc":-11,"baseline_software_rc":0,"baseline_native_pixel":BASELINE_PIXEL,"historical_cleanup":"FAIL","production_cleanup":"NOT_RUN","production_contact_health":"HOLD","human_approved":False,"root_cause":"UNMAPPED_D3D12_TSD_CALLBACK_STRONGLY_SUPPORTED_VENDOR_FIX_NOT_PROVEN","case":None,"first_error":None,"verdict":"GPU_RETENTION_MINIMAL_MITIGATION_HOLD"}
    rc=2
    try:
        env=os.environ
        head=cmd(["git","-C",str(root),"rev-parse","HEAD"],env)
        clean=cmd(["git","-C",str(root),"status","--porcelain","--untracked-files=no"],env)
        gz=cmd(["gz","sim","--versions"],env)
        kernel=cmd(["uname","-r"],env)
        pre={"actual_head":head,"tracked_clean":clean,"gz_version":gz,"kernel":kernel,"ros_distro":env.get("ROS_DISTRO"),"renderer":{k:env.get(k) for k in ENV_KEYS},"existing_loader_override":bool(env.get("LD_PRELOAD") or env.get("LD_AUDIT")),"libraries":{}}
        dump(out/"preflight.json",pre)
        if not re.fullmatch("[0-9a-f]{40}",a.sha) or head.get("rc")!=0 or head.get("stdout","").strip()!=a.sha or clean.get("rc")!=0 or clean.get("stdout") or gz.get("stdout","").strip()!="8.15.0" or env.get("ROS_DISTRO")!="jazzy" or "microsoft" not in kernel.get("stdout","").lower():raise RuntimeError("A17_RETENTION_PREFLIGHT")
        override=server_override(env)
        for name in (CORE,"/usr/lib/wsl/lib/libd3d12.so"):
            f=Path(name);s=f.stat()
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022 or f.open("rb").read(4)!=b"\x7fELF":raise RuntimeError("A17_UNTRUSTED_SYSTEM_LIBRARY")
            pre["libraries"][name]={"sha256":sha(f),"size":s.st_size,"realpath":str(f.resolve())}
        pre["server_only_override"]=override;dump(out/"preflight.json",pre)
        sdf=out/"camera_only.sdf";make_world(sdf)
        case=probe(root,out/"native_retained",sdf,"native",server_env_override=override);report["case"]=case
        q=out/"native_retained";maps=(q/"maps.txt").read_text() if (q/"maps.txt").is_file() else ""
        glx=json.loads((q/"renderer_probe.json").read_text()).get("glxinfo_same_environment_not_server_context",{}).get("stdout","") if (q/"renderer_probe.json").is_file() else ""
        report.update(evaluate(case,maps,glx))
        if report["verdict"]=="GPU_RETENTION_MINIMAL_MITIGATION_PASS":rc=0
        else:report["first_error"]="A17_RETENTION_GATE_HOLD"
    except Exception as exc:report["first_error"]=type(exc).__name__+": "+str(exc)
    finally:
        report["exit_code"]=rc;dump(out/"a17_retention_report.json",report);archive(out)
        print("A17_RETENTION_VERDICT="+report["verdict"],flush=True)
    return rc
if __name__=="__main__":raise SystemExit(main())
