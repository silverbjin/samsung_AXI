#!/usr/bin/env python3
"""Read-only private C v1 checkpoint SHA preflight (no torch, test, or image).

Requires the exact E Owner-integrated model digest from code; callers cannot
supply a different expected hash via CLI/env.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_ai"))
from smartdish_ai.model_runtime import (
    OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256 as EXPECTED_SHA,
)

def audit_model_file(path):
    path=Path(path).expanduser()
    if path.is_symlink() or not path.is_file():
        raise ValueError("E_OWNER_MODEL_NOT_REGULAR_FILE")
    digest=hashlib.sha256()
    size=0
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            size+=len(chunk)
            digest.update(chunk)
    if size==0:
        raise ValueError("E_OWNER_MODEL_EMPTY")
    actual=digest.hexdigest()
    if actual!=EXPECTED_SHA:
        raise PermissionError("E_OWNER_CHECKPOINT_SHA_MISMATCH")
    return dict(model_basename=path.name,checkpoint_sha256=actual,
                bytes=size,authorized_scope="OWNER_WSL2_GAZEBO_INTEGRATION_ONLY",
                private_weights_disclosed=False,model_performance_pass=False,
                test4_opened=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--report",type=Path,default=None,
                   help="Optional path for safe private SHA/size receipt (no weights)")
    args=p.parse_args()
    try:
        r=audit_model_file(args.checkpoint)
    except (ValueError,PermissionError,OSError) as exc:
        print("E_OWNER_MODEL_PREFLIGHT_BLOCKED="+str(exc),file=sys.stderr)
        raise SystemExit(2)
    if args.report is not None:
        if args.report.exists():
            raise SystemExit("E_OWNER_REPORT_EXISTS_NO_OVERWRITE")
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("E_OWNER_MODEL_SHA_PASS")
    print(json.dumps(r,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
