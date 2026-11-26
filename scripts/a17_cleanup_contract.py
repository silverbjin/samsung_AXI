"""A17 pure diagnostic policy and process helpers; no GT or product changes."""
import hashlib,json,os,re,signal,time,tarfile,io
from pathlib import Path
from smartdish_platform.evidence import verify_archive
HISTORICAL_WORLD_SHA="8f50fd3859468fad16a43cdd46dbf2f33d392798ed67b7743a98a9845dcacd18"
ENV_KEYS=("GALLIUM_DRIVER","MESA_D3D12_DEFAULT_ADAPTER_NAME","LIBGL_ALWAYS_SOFTWARE","MESA_LOADER_DRIVER_OVERRIDE","GZ_SIM_RENDER_ENGINE","DISPLAY","WAYLAND_DISPLAY","QT_QPA_PLATFORM")
def sha(path):
    with Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def dump(path,data):
    Path(path).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
def renderer(source,profile):
    e=dict(source)
    if profile=="software":
        e.update(GALLIUM_DRIVER="llvmpipe",LIBGL_ALWAYS_SOFTWARE="1")
        e.pop("MESA_D3D12_DEFAULT_ADAPTER_NAME",None);e.pop("MESA_LOADER_DRIVER_OVERRIDE",None)
    elif profile!="native":raise ValueError("A17_PROFILE")
    return e
def proc_identity(pid):
    raw=Path("/proc",str(pid),"stat").read_text().rsplit(")",1)[1].split()
    return {"pid":pid,"ppid":int(raw[1]),"pgid":int(raw[2]),"start_ticks":raw[19]}
def owned_inferior(pid,start,parent):
    try:
        row=proc_identity(pid)
        return row["start_ticks"]==str(start) and row["ppid"]==parent and pid!=os.getpid()
    except (OSError,IndexError,ValueError):return False
def signal_inferior(pid,start,parent,sig):
    if not owned_inferior(pid,start,parent):raise RuntimeError("A17_INFERIOR_IDENTITY")
    os.kill(pid,sig)
def group_remaining(pid):
    try:os.killpg(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True
def gdb_exit(s):
    if s.get("debugger_error"):return None
    if s.get("inferior_exit_signal") is not None:return -int(s["inferior_exit_signal"])
    if s.get("inferior_exit_code") is not None:return int(s["inferior_exit_code"])
    return None
def compare(rows):
    direct={r["profile"]:r for r in rows if r["instrumentation"]=="DIRECT"}
    if set(direct)!={"native","software"}:return "NATIVE_CONTRAST_NOT_RUN"
    a,b=direct["native"],direct["software"]
    if not all(r["data"]=="PASS" and r["all_owned_stopped"] and r.get("bridge_rc")==0 for r in (a,b)):return "CONTRAST_INCONCLUSIVE"
    if a["server_rc"]==-11 and b["server_rc"]==0:return "SOFTWARE_MITIGATION_CANDIDATE_ROOT_UNPROVEN"
    if a["server_rc"]==b["server_rc"]==-11:return "BOTH_PROFILES_CRASH_ROOT_UNPROVEN"
    if a["server_rc"]==b["server_rc"]==0:return "NOT_REPRODUCED_ROOT_UNPROVEN"
    return "CONTRAST_OTHER_ROOT_UNPROVEN"
def archive(root):
    root=Path(root).resolve()
    allowed={".json",".txt",".log",".sdf"}
    files=[]
    for p in sorted(root.rglob("*")):
        if p.is_symlink():raise ValueError("A17_UNSAFE_LINK")
        if p.is_file() and p.suffix in allowed:
            if p.stat().st_size>16*1024*1024:raise ValueError("A17_FILE_LIMIT")
            files.append(p)
    if not files or len(files)>100 or sum(p.stat().st_size for p in files)>96*1024*1024:raise ValueError("A17_ARCHIVE_LIMIT")
    manifest="".join(sha(p)+"  "+p.relative_to(root).as_posix()+"\n" for p in files).encode()
    dest=root/"a17_cleanup_evidence.tar.gz"
    with tarfile.open(dest,"x:gz") as t:
        for p in files:t.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
        m=tarfile.TarInfo("SHA256SUMS");m.size=len(manifest);t.addfile(m,io.BytesIO(manifest))
    digest=sha(dest);verify_archive(dest,digest)
    Path(str(dest)+".sha256").write_text(digest+"  "+dest.name+"\n")
    print("A17_EVIDENCE_ARCHIVE="+str(dest),flush=True);print("A17_EVIDENCE_SHA256="+digest,flush=True)
    return digest
