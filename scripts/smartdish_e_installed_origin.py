#!/usr/bin/env python3
"""Verify the actual installed ROS overlay and source tree; no model imports or motion."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

MODULES={
    "smartdish_ai":("stability_inference_node","model_runtime","inference_core"),
    "smartdish_service":("manager_node","mission_manager","product_admission","ui_app"),
    "smartdish_robot":("navigation_adapter","contract"),
}
ENTRIES={"smartdish_ai":("stability_inference_node",),
         "smartdish_service":("smartdish_manager","smartdish_ui"),
         "smartdish_robot":("navigation_adapter",)}
def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def same_bytes(actual, expected):
    actual,expected=Path(actual),Path(expected)
    if not actual.is_file() or not expected.is_file() or digest(actual)!=digest(expected):
        raise RuntimeError("E_OWNER_INSTALLED_SOURCE_MISMATCH:"+str(actual))
    return digest(actual)

def git(root,*args):
    return subprocess.check_output(["git","-c","safe.directory="+str(root),"-C",str(root),*args],
                                   text=True,timeout=15).strip()

def inspect(root,pin,base,packages):
    root,base=Path(root).resolve(),Path(base).resolve()
    if git(root,"rev-parse","HEAD")!=pin:
        raise RuntimeError("E_OWNER_INSTALLED_PIN_DRIFT")
    # Tracked bytes must also match the commit. Do not modify the worktree.
    if git(root,"status","--porcelain","--untracked-files=no"):
        raise RuntimeError("E_OWNER_INSTALLED_TRACKED_TREE_DIRTY")
    if Path(sys.executable).resolve()!=Path("/usr/bin/python3").resolve():
        raise RuntimeError("E_OWNER_INSTALLED_PYTHON_DRIFT")
    records=[]
    for pkg in packages:
        prefix=Path(subprocess.check_output(["ros2","pkg","prefix",pkg],text=True,timeout=15).strip())
        if prefix.resolve()!=(base/pkg).resolve():
            raise RuntimeError("E_OWNER_ROS_PREFIX_DRIFT:"+pkg+":"+str(prefix))
        for exe in ENTRIES[pkg]:
            path=prefix/"lib"/pkg/exe
            with path.open("rb") as f:
                first=f.readline().decode("utf-8").strip()
            if not first.startswith("#!") or Path(first[2:]).resolve()!=Path("/usr/bin/python3").resolve():
                raise RuntimeError("E_OWNER_ROS_ENTRYPOINT_PYTHON_DRIFT:"+str(path))
            records.append({"package":pkg,"entrypoint":str(path),"shebang":first,"sha256":digest(path)})
        for mod in MODULES[pkg]:
            spec=importlib.util.find_spec(pkg+"."+mod)
            if spec is None or spec.origin is None:
                raise RuntimeError("E_OWNER_ROS_MODULE_MISSING:"+pkg+"."+mod)
            actual=Path(spec.origin)
            expected=root/"src"/pkg/pkg/(mod+".py")
            records.append({"package":pkg,"module":mod,"installed_path":str(actual),
                            "source_path":str(expected),"sha256":same_bytes(actual,expected)})
        if pkg=="smartdish_service":
            name="smartdish_e_owner_aion.launch.py"
            installed=prefix/"share"/pkg/"launch"/name
            source=root/"src"/pkg/"launch"/name
            records.append({"package":pkg,"launch":str(installed),"sha256":same_bytes(installed,source)})
    return {"source_sha":pin,"install_base":str(base),"python":sys.executable,"records":records}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--pin",required=True)
    p.add_argument("--install-base",type=Path,required=True)
    p.add_argument("--packages",nargs="+",choices=MODULES,required=True)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    result=inspect(a.root,a.pin,a.install_base,a.packages)
    if a.out:
        a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
    print("E_OWNER_INSTALLED_MODULE_BYTES_MATCH")
if __name__=="__main__":
    main()
