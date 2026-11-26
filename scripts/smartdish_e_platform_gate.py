"""E planning/release gate. A data PASS is not feature approval; fail closed."""
import argparse,json,re,subprocess
from pathlib import Path
from smartdish_platform.baseline import check,git

ROLES=("A","B","C","D")
def validate(root,manifest,baseline):
    common=check(root,baseline)
    if manifest.get("schema")!=1 or manifest.get("platform_sha")!=baseline:
        raise ValueError("E_PLATFORM_PIN_MISMATCH")
    roles=manifest.get("roles",{})
    if set(roles)!=set(ROLES): raise ValueError("E_ROLE_SET_MISMATCH")
    results={}
    for role in ROLES:
        item=roles[role]
        problems=[]
        sha=item.get("source_sha")
        if not isinstance(sha,str) or not re.fullmatch("[0-9a-f]{40}",sha):
            problems.append("MISSING_ROLE_PIN")
        else:
            if subprocess.run(["git","-C",str(root),"merge-base","--is-ancestor",sha,common["actual_sha"]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
                problems.append("ROLE_NOT_IN_CANDIDATE")
            if subprocess.run(["git","-C",str(root),"merge-base","--is-ancestor",baseline,sha],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
                problems.append("ROLE_PLATFORM_NOT_SYNCED")
        if item.get("approval")!="APPROVED":problems.append("ROLE_NOT_APPROVED")
        if item.get("scoped_ci")!="PASS" or not item.get("ci_run_ids"):problems.append("ROLE_CI_NOT_VERIFIED")
        if item.get("owner_required") is True and (item.get("owner_verdict")!="PASS" or not re.fullmatch("[0-9a-f]{64}",item.get("owner_evidence_sha256") or "")):
            problems.append("OWNER_EVIDENCE_NOT_ACCEPTED")
        if type(item.get("owner_required")) is not bool:problems.append("OWNER_REQUIREMENT_UNDECLARED")
        results[role]={"source_sha":sha,"problems":problems,"verdict":"HOLD" if problems else "PASS"}
    # Manifest is a reviewed policy input; this script cannot prove authenticity of
    # remote CI/approval records by itself. E must cross-check real GitHub/Owner receipts.
    return {"platform":common,"roles":results,"integration_inputs":"PASS" if all(r["verdict"]=="PASS" for r in results.values()) else "HOLD","product_release":"NOT_ASSESSED","human_gt_approval":"NOT_ASSESSED"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",required=True);p.add_argument("--manifest",required=True,type=Path);p.add_argument("--root",default=".")
    p.add_argument("--require-ready",action="store_true")
    a=p.parse_args()
    r=validate(Path(a.root),json.loads(a.manifest.read_text()),a.baseline)
    print(json.dumps(r,indent=2,sort_keys=True))
    return 2 if a.require_ready and r["integration_inputs"]!="PASS" else 0
if __name__=="__main__":raise SystemExit(main())
