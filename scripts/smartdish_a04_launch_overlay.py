"""Opt-in A04 launch overlay. Never edit installed or repository launch files."""
import ast
import difflib
import json
from pathlib import Path
from hashlib import sha256

def patch_docking(source):
    """Only patch the two official docking_server declarations; fail closed on drift."""
    tree=ast.parse(source)
    targets=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):continue
        kw={k.arg:k.value for k in node.keywords if k.arg}
        name=kw.get("name")
        if not isinstance(name,ast.Constant) or name.value!="docking_server":continue
        v=kw.get("remappings")
        if not isinstance(v,ast.Name) or v.id!="remappings":raise RuntimeError("DOCKING_REMAP_SOURCE_DRIFT")
        targets.append(v)
    if len(targets)!=2:raise RuntimeError("DOCKING_DECLARATION_COUNT:"+str(len(targets)))
    lines=source.splitlines(keepends=True)
    for v in sorted(targets,key=lambda q:q.lineno,reverse=True):
        i=v.lineno-1
        if v.lineno!=v.end_lineno:raise RuntimeError("DOCKING_REMAP_MULTILINE")
        lines[i]=lines[i][:v.col_offset]+"remappings + [('cmd_vel', 'cmd_vel_nav')]"+lines[i][v.end_col_offset:]
    patched="".join(lines);ast.parse(patched)
    return patched

def prepare_launch_overlay(out):
    from ament_index_python.packages import get_package_share_directory
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    nav=Path(get_package_share_directory("nav2_bringup"))/"launch"
    restaurant=Path(get_package_share_directory("restaurant_bringup"))/"launch/navigation.launch.py"
    originals={"nav_navigation":nav/"navigation_launch.py","nav_bringup":nav/"bringup_launch.py","restaurant":restaurant}
    sources={k:v.read_text() for k,v in originals.items()}
    generated={k:out/(k+".launch.py") for k in originals}
    patched={"nav_navigation":patch_docking(sources["nav_navigation"])}
    old="os.path.join(launch_dir, 'navigation_launch.py')"
    if sources["nav_bringup"].count(old)!=1:raise RuntimeError("NAV_BRINGUP_SOURCE_DRIFT")
    patched["nav_bringup"]=sources["nav_bringup"].replace(old,repr(str(generated["nav_navigation"])))
    old="os.path.join(nav,'launch','bringup_launch.py')"
    if sources["restaurant"].count(old)!=2:raise RuntimeError("RESTAURANT_LAUNCH_SOURCE_DRIFT")
    patched["restaurant"]=sources["restaurant"].replace(old,repr(str(generated["nav_bringup"])))
    manifest={}
    for k in originals:
        ast.parse(patched[k])
        (out/(k+".original.py")).write_text(sources[k])
        generated[k].write_text(patched[k])
        (out/(k+".diff")).write_text("".join(difflib.unified_diff(sources[k].splitlines(True),patched[k].splitlines(True),fromfile=str(originals[k]),tofile=str(generated[k]))))
        manifest[k]={"installed_path":str(originals[k]),"source_sha256":sha256(sources[k].encode()).hexdigest(),"generated_sha256":sha256(patched[k].encode()).hexdigest()}
        if originals[k].read_text()!=sources[k]:raise RuntimeError("INSTALLED_SOURCE_MUTATED")
    (out/"launch_overlay_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return generated["restaurant"],manifest
