#!/usr/bin/env python3
"""E-only generated Nav2 overlay: keep every velocity command upstream of CM.
Never mutate the installed Nav2 or the released A/S7 launch. Fail closed on drift.
"""
import ast
import hashlib
import json
from pathlib import Path
import shutil

def sha(data):
    return hashlib.sha256(data).hexdigest()

def edit_at(source,node,replacement):
    # AST columns are UTF-8 byte offsets. The inspected official launch source
    # is ASCII at the patched expression; compute offsets on bytes nonetheless.
    lines=source.encode().splitlines(keepends=True)
    a=sum(map(len,lines[:node.lineno-1]))+node.col_offset
    b=sum(map(len,lines[:node.end_lineno-1]))+node.end_col_offset
    raw=source.encode()
    return (raw[:a]+replacement.encode()+raw[b:]).decode()

def rewrite_share(source,new_share):
    nodes=[n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call)
           and isinstance(n.func,ast.Name) and n.func.id=="get_package_share_directory"
           and len(n.args)==1 and isinstance(n.args[0],ast.Constant)
           and n.args[0].value=="nav2_bringup"]
    if len(nodes)!=1:
        raise RuntimeError("E_NAV_SHARE_EXPRESSION_DRIFT")
    return edit_at(source,nodes[0],repr(str(new_share)))

def rewrite_docking(source):
    nodes=[]
    for n in ast.walk(ast.parse(source)):
        if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Name) or n.func.id not in ("Node","ComposableNode"):
            continue
        kw={x.arg:x.value for x in n.keywords}
        package=kw.get("package")
        if isinstance(package,ast.Constant) and package.value=="opennav_docking":
            name=kw.get("name"); remap=kw.get("remappings")
            if not isinstance(name,ast.Constant) or name.value!="docking_server" or not isinstance(remap,ast.Name) or remap.id!="remappings":
                raise RuntimeError("E_NAV_DOCKING_REMAP_CONTRACT_DRIFT")
            nodes.append((n.func.id,remap))
    if sorted(k for k,_ in nodes)!=["ComposableNode","Node"]:
        raise RuntimeError("E_NAV_EXPECTED_DOCKING_NODES_DRIFT")
    for _,n in sorted(nodes,key=lambda x:(x[1].lineno,x[1].col_offset),reverse=True):
        source=edit_at(source,n,"remappings + [('cmd_vel', 'cmd_vel_nav')]")
    ast.parse(source)
    return source

def prepare_overlay(nav_share,restaurant_launch,out):
    nav_share,restaurant_launch,out=Path(nav_share),Path(restaurant_launch),Path(out)
    overlay=out/"e_nav2_overlay"
    overlay.mkdir(exist_ok=False)
    shutil.copytree(nav_share/"launch",overlay/"launch",ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    for sub in ("params","rviz"):
        if (nav_share/sub).is_dir():shutil.copytree(nav_share/sub,overlay/sub)
    inputs=[(nav_share/"launch"/"navigation_launch.py",overlay/"launch"/"navigation_launch.py",rewrite_docking),
            (nav_share/"launch"/"bringup_launch.py",overlay/"launch"/"bringup_launch.py",lambda s:rewrite_share(s,overlay)),
            (restaurant_launch,overlay/"restaurant_navigation.launch.py",lambda s:rewrite_share(s,overlay))]
    records=[]
    for original,generated,change in inputs:
        raw=original.read_bytes()
        transformed=change(raw.decode())
        ast.parse(transformed)
        generated.write_text(transformed)
        assert original.read_bytes()==raw
        records.append({"original":str(original),"source_sha256":sha(raw),
                        "generated":str(generated),"generated_sha256":sha(generated.read_bytes())})
    receipt={"scope":"E_STATION_ONLY_NAV2_DOCKING_THROUGH_CM","changes":records,
             "velocity_chain":["cmd_vel_nav","velocity_smoother","cmd_vel_smoothed","collision_monitor","cmd_vel"],
             "installed_files_modified":False,"s7_launch_modified":False}
    (out/"nav2_overlay_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return overlay/"restaurant_navigation.launch.py"
