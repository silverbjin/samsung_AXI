"""Bounded shutdown of owned subprocess groups only, preserving exit codes."""
import os
import signal
import subprocess

def stop_owned(proc, *, int_timeout=8, term_timeout=5, kill_timeout=5):
    if proc is None: raise ValueError("PLATFORM_PROCESS_REQUIRED")
    rc=proc.poll()
    events=[]
    if rc is not None:
        return {"pid":proc.pid,"returncode":rc,"stopped":True,"signals":events}
    # A caller must create the child with start_new_session=True.
    # Refuse the caller's group or an unexpected group.
    if os.getpgid(proc.pid)!=proc.pid or proc.pid==os.getpgrp():
        raise ValueError("PLATFORM_PROCESS_NOT_OWNED_GROUP")
    for sig,seconds in ((signal.SIGINT,int_timeout),(signal.SIGTERM,term_timeout),(signal.SIGKILL,kill_timeout)):
        if proc.poll() is not None: break
        try:
            os.killpg(proc.pid,sig)
            events.append(int(sig))
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=seconds)
            break
        except subprocess.TimeoutExpired:
            pass
    rc=proc.poll()
    return {"pid":proc.pid,"returncode":rc,"stopped":rc is not None,"signals":events}
