"""A-only production server profile. Explicit opt-in, never global preload.

The tested WSL library pair is a compatibility allowlist, not a vendor fix.
Do not use this module to modify the shared Platform or S7 launch defaults.
"""
from __future__ import annotations
import hashlib,os,re,stat,struct,subprocess
from pathlib import Path

INHERIT="inherit"
RETAIN="wsl_d3d12_retention_v1"
PROFILES=(INHERIT,RETAIN)
CORE="/usr/lib/wsl/lib/libd3d12core.so"
D3D12="/usr/lib/wsl/lib/libd3d12.so"
LIBRARIES={
    CORE:"a4104a2022932d8e6c714f103ebd89db1c5bdbf36fe92151c88d3d93d4e3894d",
    D3D12:"b3d78d409a4dbbe8612551fc0c0d746d3e58d7997ee7eba78ce1064d77cfa8c3",
}
OWNER_ACCEPTANCE_SHA="ffe39e4e330b99014fc2276fda4ba07fa4ae58b7d382467617cf89044a4a5f99"
OWNER_ACCEPTANCE_RECORD="942ad5f7921dc245ad9361cab29732e67d22c51b"
MESA_VERSION="25.2.8-0ubuntu0.24.04.5"
MESA_PACKAGES=("libgl1-mesa-dri","libglx-mesa0","mesa-libgallium")
ENV_KEYS=("GALLIUM_DRIVER","MESA_D3D12_DEFAULT_ADAPTER_NAME","LIBGL_ALWAYS_SOFTWARE","MESA_LOADER_DRIVER_OVERRIDE","GZ_SIM_RENDER_ENGINE","LD_PRELOAD","LD_AUDIT")

def require(ok,code):
    if not ok:raise ValueError(code)

def _run(args,env,timeout=15):
    p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=timeout,check=False)
    require(p.returncode==0,"A17_08_COMMAND_FAILED:"+args[0])
    return p.stdout.strip()

def _trusted_library(name,expected):
    p=Path(name);resolved=p.resolve(strict=True)
    require(resolved.is_relative_to(Path("/usr/lib/wsl")),"A17_08_LIBRARY_OUTSIDE_WSL")
    # Verify resolved file and its directories; do not accept a caller-supplied path.
    for d in [resolved,*resolved.parents]:
        s=d.stat()
        require(s.st_uid==0 and not s.st_mode&0o022,"A17_08_LIBRARY_PATH_UNTRUSTED")
    with resolved.open("rb") as f:
        st=os.fstat(f.fileno());hdr=f.read(20)
        require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022,"A17_08_LIBRARY_UNTRUSTED")
        require(len(hdr)==20 and hdr[:6]==b"\x7fELF\x02\x01" and struct.unpack_from("<H",hdr,18)[0]==62,"A17_08_LIBRARY_ELF_X86_64_REQUIRED")
        f.seek(0);digest=hashlib.file_digest(f,"sha256").hexdigest()
    require(digest==expected,"A17_08_LIBRARY_SHA_DRIFT:"+name)
    return {"path":name,"realpath":str(resolved),"sha256":digest,"size_bytes":st.st_size}

def _native_environment(env):
    require(not env.get("LD_PRELOAD") and not env.get("LD_AUDIT"),"A17_08_INHERITED_LOADER_OVERRIDE")
    require(env.get("GALLIUM_DRIVER")=="d3d12" and env.get("MESA_D3D12_DEFAULT_ADAPTER_NAME")=="NVIDIA","A17_08_NATIVE_D3D12_NVIDIA_REQUIRED")
    require(env.get("LIBGL_ALWAYS_SOFTWARE") in (None,"","0") and not env.get("MESA_LOADER_DRIVER_OVERRIDE"),"A17_08_SOFTWARE_OR_DRIVER_OVERRIDE")
    require(env.get("GZ_SIM_RENDER_ENGINE","ogre2")=="ogre2","A17_08_OGRE2_REQUIRED")
    require(env.get("ROS_DISTRO")=="jazzy","A17_08_JAZZY_REQUIRED")

def _renderer(glx):
    m=re.search(r"(?m)^OpenGL renderer string:\s*(D3D12 \(NVIDIA[^\n]*\))\s*$",glx)
    require(m and re.search(r"(?mi)^\s*Accelerated:\s*yes\s*$",glx),"A17_08_GLX_NATIVE_NOT_CORROBORATED")
    return m.group(1)

def prepare(source,profile,source_class):
    """Return server-only env and private provenance. No subprocess starts on rejection."""
    require(profile in PROFILES,"A17_08_PROFILE_UNKNOWN")
    env=dict(source)
    if profile==INHERIT:return env,None
    require(source_class=="OWNER_WSL2","A17_08_OWNER_PROFILE_ONLY")
    _native_environment(env)
    kernel=_run(["uname","-r"],env)
    require("microsoft" in kernel.lower() and "wsl2" in kernel.lower(),"A17_08_WSL2_REQUIRED")
    gz=_run(["gz","sim","--versions"],env)
    require(gz=="8.15.0","A17_08_HARMONIC_VERSION_DRIFT")
    packages={name:_run(["dpkg-query","-W","-f=${Version}",name],env) for name in MESA_PACKAGES}
    require(all(v==MESA_VERSION for v in packages.values()),"A17_08_MESA_VERSION_DRIFT")
    libs={name:_trusted_library(name,h) for name,h in LIBRARIES.items()}
    glx=_run(["glxinfo","-B"],env)
    renderer=_renderer(glx)
    record={"schema":1,"profile":profile,"scope":"A_GAZEBO_SERVER_ONLY","owner_minimal_evidence_sha256":OWNER_ACCEPTANCE_SHA,"owner_acceptance_record":OWNER_ACCEPTANCE_RECORD,"kernel":kernel,"gz_sim":gz,"ros_distro":"jazzy","mesa_packages":packages,"libraries":libs,"glx_renderer":renderer,"glx_scope":"SAME_ENV_GLX_NOT_SERVER_CONTEXT_PROOF","requested_server_env":{k:env.get(k) for k in ENV_KEYS},"runtime_observation":None,"production_cleanup":"NOT_RUN","historical_cleanup":"FAIL","vendor_fix_proven":False}
    env["LD_PRELOAD"]=CORE
    record["requested_server_env"]["LD_PRELOAD"]=CORE
    return env,record

def observe(proc,record):
    """Read only our live Popen child; retain selected env fields, not arbitrary secrets."""
    require(record is not None and proc.poll() is None,"A17_08_SERVER_NOT_ALIVE")
    pid=proc.pid;p=Path("/proc",str(pid))
    require(os.getpgid(pid)==pid and pid!=os.getpgrp(),"A17_08_SERVER_GROUP_NOT_OWNED")
    env={}
    for item in (p/"environ").read_bytes().split(b"\0"):
        key,sep,val=item.partition(b"=")
        if sep and key.decode(errors="replace") in ENV_KEYS:env[key.decode()]=val.decode(errors="replace")
    expected=record["requested_server_env"]
    require(all(env.get(k)==v for k,v in expected.items() if v is not None) and env.get("LD_PRELOAD")==CORE and not env.get("LD_AUDIT"),"A17_08_ACTUAL_SERVER_ENV_DRIFT")
    lines=(p/"maps").read_text().splitlines();mapped=[]
    for line in lines:
        parts=line.split(maxsplit=5)
        if len(parts)==6 and parts[5] in {x["realpath"] for x in record["libraries"].values()}|set(record["libraries"]):mapped.append({"path":parts[5],"permissions":parts[1]})
    for name,x in record["libraries"].items():
        require(any(m["path"] in (name,x["realpath"]) and "x" in m["permissions"] for m in mapped),"A17_08_SERVER_LIBRARY_NOT_MAPPED:"+name)
    require(proc.poll() is None,"A17_08_SERVER_EXITED_DURING_OBSERVATION")
    record["runtime_observation"]={"pid":pid,"selected_env":env,"mapped_libraries":mapped,"scope":"ACTUAL_SERVER_PROCESS_MAPS_NOT_DIRECT_GL_CONTEXT"}
    return record["runtime_observation"]

def cleanup_result(record,rows,data,all_owned_stopped):
    """Preserve data/GUI outcomes; production cleanup is a separate stricter gate."""
    if record is None:return "NOT_REQUESTED"
    server=[x for x in rows if x.get("role")=="server"]
    required_roles={"server","native_contact","rgb_bridge","contact_bridge"}
    non_gui=[x for x in rows if x.get("role")!="gui"]
    ok=(data=="PASS" and record.get("runtime_observation") is not None and all_owned_stopped
        and len(server)==1 and set(x.get("role") for x in non_gui)==required_roles
        and len(non_gui)==len(required_roles)
        and all(x.get("returncode")==0 and x.get("stopped") is True and x.get("process_group_remaining") is False for x in non_gui)
        and server[0].get("signals")==[2])
    record["production_cleanup"]="PASS" if ok else "HOLD"
    return record["production_cleanup"]
