"""Verify a consumer checkout against an externally selected trusted platform SHA."""
import argparse,json,re,subprocess
from pathlib import Path

def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()

def check(root,baseline):
    root=Path(root)
    if not re.fullmatch("[0-9a-f]{40}",baseline):
        raise ValueError("PLATFORM_BASELINE_PIN_INVALID")
    actual=git(root,"rev-parse","HEAD")
    if git(root,"rev-parse",baseline+"^{commit}")!=baseline: raise ValueError("PLATFORM_PIN_MISMATCH")
    if subprocess.run(["git","-C",str(root),"merge-base","--is-ancestor",baseline,actual]).returncode:
        raise ValueError("PLATFORM_BASELINE_NOT_IN_ANCESTRY")
    trusted=json.loads(git(root,"show",baseline+":config/smartdish_platform_baseline.json"))
    paths=trusted["protected_paths"]
    if not paths: raise ValueError("PLATFORM_PROTECTED_PATHS_EMPTY")
    # The list comes from the trusted baseline, not the consumer branch.
    if subprocess.run(["git","-C",str(root),"diff","--quiet",baseline,actual,"--",*paths]).returncode:
        raise ValueError("PLATFORM_PROTECTED_PATH_DRIFT")
    if git(root,"status","--porcelain","--untracked-files=no"): raise ValueError("PLATFORM_TRACKED_DIRTY")
    return {"baseline_sha":baseline,"actual_sha":actual,"platform_version":trusted["version"],"verdict":"PASS"}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",default=".");p.add_argument("--baseline",required=True)
    a=p.parse_args();print(json.dumps(check(a.root,a.baseline),sort_keys=True))
