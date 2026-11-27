"""CI-only process supervisor; diagnostic timeout and scoped cleanup, never a PASS substitute."""
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path

ENV="SMARTDISH_E_SESSION_TOKEN"
def token():
    if os.environ.get("CI")!="true" or os.environ.get("GITHUB_ACTIONS")!="true" or not os.environ.get("GZ_PARTITION","").startswith("smartdish_a04_e_") or os.environ.get("WSL_DISTRO_NAME"):
        raise RuntimeError("E_SUPERVISOR_CI_ONLY")
    return "smartdish-e-"+os.environ["GITHUB_RUN_ID"]+"-"+os.environ.get("GITHUB_RUN_ATTEMPT","1")

def owned(value):
    needle=(ENV+"="+value).encode()
    found=[]
    for p in Path("/proc").iterdir():
        if not p.name.isdecimal() or int(p.name)==os.getpid():continue
        try:
            if p.stat().st_uid!=os.getuid():continue
            # Zombies cannot write files; do not mistake them for a live writer.
            stat=(p/"stat").read_text().rsplit(")",1)[1].split()
            if stat[0]=="Z":continue
            if needle in (p/"environ").read_bytes().split(b"\0"):
                found.append(int(p.name))
        except (OSError,IndexError):continue
    return sorted(found)

def send_owned(value,sig):
    # Recheck exact inherited token immediately before each signal.
    for pid in owned(value):
        try:
            if pid in owned(value):os.kill(pid,sig)
        except ProcessLookupError:pass

def await_empty(value,seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if not owned(value):return []
        time.sleep(.2)
    return owned(value)

def cleanup(value):
    before=owned(value)
    if before:
        send_owned(value,signal.SIGINT)
        residual=await_empty(value,3.)
        if residual:send_owned(value,signal.SIGKILL)
        after=await_empty(value,3.)
    else:residual=after=[]
    return dict(before=before,forced_pids=residual,remaining=after,clean=not before)

def phase_timeout(path,now,budget=45.):
    try:d=json.loads(Path(path).read_text())
    except (OSError,ValueError):return None
    if d.get("initializing") is True and now-float(d["steady_s"])>=budget:return d["stage"]
    return None

def supervise(args):
    value=token();env=os.environ|{ENV:value}
    if owned(value):raise RuntimeError("E_PRIOR_OWNED_PROCESSES")
    proc=subprocess.Popen(args.command,env=env,start_new_session=True)
    begin=time.monotonic();reason=None;stalled=None
    try:
        while proc.poll() is None:
            stalled=phase_timeout(args.phase,time.monotonic())
            if stalled:reason="E_STARTUP_STAGE_TIMEOUT";break
            if time.monotonic()-begin>=950:reason="E_SESSION_WALL_TIMEOUT";break
            time.sleep(.25)
        if reason:
            print(reason+":"+str(stalled),flush=True)
            try:os.kill(proc.pid,signal.SIGINT)
            except ProcessLookupError:pass
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:pass
    finally:
        result=cleanup(value)
        try:proc.wait(timeout=3)
        except subprocess.TimeoutExpired:pass
        report=dict(reason=reason,stalled_stage=stalled,process_exit=proc.poll(),elapsed_s=time.monotonic()-begin,cleanup=result)
        args.report.write_text(json.dumps(report,indent=2)+"\n")
        print("E_SUPERVISOR_REPORT="+json.dumps(report),flush=True)
    # A forced cleanup or any orphan is diagnostic only, even if child's exit was 0.
    return 0 if reason is None and proc.returncode==0 and result["clean"] and not result["remaining"] else 1

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--phase",type=Path);p.add_argument("--report",type=Path,required=True)
    p.add_argument("--cleanup-only",action="store_true");p.add_argument("command",nargs=argparse.REMAINDER)
    a=p.parse_args()
    if a.cleanup_only:
        r=cleanup(token());a.report.write_text(json.dumps(r,indent=2)+"\n")
        # Non-empty before means a cleanup fault, but no residual permits diagnostic archive.
        return 0 if not r["remaining"] else 1
    if a.command and a.command[0]=="--":a.command=a.command[1:]
    if not a.phase or not a.command:p.error("phase and command required")
    return supervise(a)
if __name__=="__main__":sys.exit(main())
