"""Immutable CPU QA05 CLI. Private output, normal success/failure archive."""
import argparse,hashlib,io,json,os,platform,re,subprocess,tarfile
from pathlib import Path
import PIL
from audit_b_qa05_diversity import audit,INPUTS
def main(argv=None):
    p=argparse.ArgumentParser()
    for k in INPUTS:p.add_argument("--"+k.replace("_","-"),type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True);p.add_argument("--verifier-sha",required=True)
    a=p.parse_args(argv);os.umask(0o077);out=a.out_dir.absolute()
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    report={"scope":"B_QA05_HOLD","actual_12_scene_roi_review":False,"gates":{f"B-Q0{i}":"HOLD" for i in range(1,8)},"previous_qa04_q01":"PASS","ground_truth":"UNKNOWN_HOLD","approved_count":0,"training_eligible":False,"model_training_executed":False,"production_contact_health":"HOLD","cleanup":"FAIL","product_approval":False}
    rc=2;head=None;receipt={}
    try:
        root=Path(__file__).resolve().parents[2]
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if not re.fullmatch("[0-9a-f]{40}",a.verifier_sha) or head!=a.verifier_sha:raise ValueError("B_QA05_HEAD_DRIFT")
        if subprocess.check_output(["git","-C",str(root),"status","--porcelain","--untracked-files=no"],text=True).strip():raise ValueError("B_QA05_TRACKED_DIRTY")
        report=audit({k:getattr(a,k) for k in INPUTS},out,receipt);rc=0
    except Exception as e:report["first_error"]=type(e).__name__+": "+str(e)
    status={"exit_code":rc,"verifier_sha":a.verifier_sha,"checkout_head":head,"python":platform.python_version(),"pillow":PIL.__version__,"expected_input_sha":{k:v[1] for k,v in INPUTS.items()},"input_receipt":receipt,"actual_12_scene_roi_review":rc==0,"approved_count":0,"training_executed":False}
    for n,x in (("qa05_report.json",report),("diagnostic_status.json",status)):
        (out/n).write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf8")
    files=sorted(x for x in out.iterdir() if x.is_file())
    dest=out/"b_qa05_diagnostics.tar.gz"
    with tarfile.open(dest,"x:gz") as t:
        sums=b""
        for x in files:
            t.add(x,arcname=x.name,recursive=False);sums+=(hashlib.sha256(x.read_bytes()).hexdigest()+"  "+x.name+"\n").encode()
        info=tarfile.TarInfo("SHA256SUMS");info.size=len(sums);info.mode=0o600;t.addfile(info,io.BytesIO(sums))
    digest=hashlib.sha256(dest.read_bytes()).hexdigest()
    Path(str(dest)+".sha256").write_text(digest+"  "+dest.name+"\n")
    print("B_QA05_REVIEW_ONLY" if rc==0 else "B_QA05_HOLD");print("B_QA05_DIAGNOSTICS="+str(dest));print("B_QA05_DIAGNOSTICS_SHA="+digest)
    return rc
if __name__=="__main__":raise SystemExit(main())
