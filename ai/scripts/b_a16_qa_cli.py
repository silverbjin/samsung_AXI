"""Private QA04 CPU offline CLI. No training output."""
import argparse,csv,hashlib,io,json,os,sys,tarfile
from pathlib import Path
from audit_b_a16 import audit
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("owner","diagnostics","a15","out-dir"):p.add_argument("--"+n,type=Path,required=True)
    p.add_argument("--verifier-sha",required=True)
    a=p.parse_args();out=a.out_dir.expanduser().absolute()
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    def get(path):
        side=Path(str(path)+".sha256")
        if path.is_symlink() or side.is_symlink() or not path.is_file() or not side.is_file() or path.stat().st_size>400*1024*1024:raise ValueError("B_A16_INPUT_INVALID")
        return path.read_bytes(),side.read_bytes()
    rc=2
    try:
        if len(a.verifier_sha)!=40 or any(x not in "0123456789abcdef" for x in a.verifier_sha):raise ValueError("B_A16_VERIFIER_SHA")
        report=audit(*get(a.owner),*get(a.diagnostics),*get(a.a15));rc=0
    except Exception as e:
        report={"scope":"B_QA04_OWNER_VALIDATION_FAILED","actual_owner_raw_directly_recomputed":False,"first_error":type(e).__name__+": "+str(e),"gates":{f"B-Q0{i}":"HOLD" for i in range(1,8)},"human_approved":False,"approved_count":0,"training_eligible":False,"ground_truth":"UNKNOWN_HOLD"}
    report["verifier_sha"]=a.verifier_sha
    (out/"qa_report.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    if rc==0:
        with (out/"review_worksheet.csv").open("x",newline="") as f:
            w=csv.writer(f);w.writerow(["scene","layout","observed_upper_max_m","visual_occlusion","human_decision","reviewer","reason","license_status"])
            for s in report["scenes"]:w.writerow([s["scene_id"],s["geometry"]["layout"],s["metrics"][s["upper"]]["max_relative_displacement_m"],"","","","",""])
    (out/"diagnostic_status.json").write_text(json.dumps({"verifier_sha":a.verifier_sha,"exit_code":rc,"approved_count":0,"actual_owner_raw_directly_recomputed":rc==0},indent=2)+"\n")
    files=[x for x in (out/"qa_report.json",out/"diagnostic_status.json",out/"review_worksheet.csv") if x.is_file()]
    dest=out/"b_a16_qa04_diagnostics.tar.gz"
    sums="".join(hashlib.sha256(x.read_bytes()).hexdigest()+"  "+x.name+"\n" for x in files).encode()
    with tarfile.open(dest,"x:gz") as t:
        for x in files:t.add(x,arcname=x.name,recursive=False)
        m=tarfile.TarInfo("SHA256SUMS");m.size=len(sums);t.addfile(m,io.BytesIO(sums))
    digest=hashlib.sha256(dest.read_bytes()).hexdigest()
    Path(str(dest)+".sha256").write_text(digest+"  "+dest.name+"\n")
    print("B_A16_QA04_REVIEW_ONLY" if rc==0 else "B_A16_QA04_HOLD")
    print("B_A16_QA04_DIAGNOSTICS="+str(dest));print("B_A16_QA04_DIAGNOSTICS_SHA="+digest)
    return rc
if __name__=="__main__":raise SystemExit(main())
