#!/usr/bin/env python3
"""R03 opt-in collection; original A13 GUI/physics contract stays intact."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

from smartdish_platform.runtime import renderer_env

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sha",required=True)
    p.add_argument("--plugin",required=True,type=Path)
    p.add_argument("--scene",required=True,choices=["ST-02","UN-01"])
    p.add_argument("--trace",required=True,type=Path)
    p.add_argument("--headless",action="store_true")
    p.add_argument("--native-gui",action="store_true")
    p.add_argument("--inject-gui-abort",action="store_true")
    a=p.parse_args()
    if a.inject_gui_abort and (os.environ.get("CI")!="true" or a.headless):
        p.error("CI GUI fault injection only")
    import smartdish_a_tray_live as live
    import smartdish_a14_physics as physics
    from a14_r02_production_collect import install_adapter
    import smartdish_a_tray_gui_preflight as preflight
    if not a.plugin.is_file(): p.error("plugin missing")
    original_split,original_retain,original_build=install_adapter(a.plugin.resolve())
    events=[]; gui=None; roles={}; injected=False
    real_popen=subprocess.Popen
    real_stop=live.stop_owned
    real_call=live.gz_call
    real_subprocess=live.subprocess
    real_gui_env=preflight.gui_profile_env
    def event(kind,**values):
        events.append(dict(event=kind,monotonic_ns=time.monotonic_ns(),**values))
    class Proxy:
        def __getattr__(self,key): return getattr(real_subprocess,key)
        def Popen(self,cmd,*args,**kwargs):
            nonlocal gui
            role="gui" if cmd[:3]==["gz","sim","-g"] else "server" if cmd[:3]==["gz","sim","-s"] else "aux"
            proc=real_popen(cmd,*args,**kwargs); roles[proc.pid]=role
            if role=="gui": gui=proc
            env=kwargs.get("env",os.environ)
            event("launch",pid=proc.pid,role=role,command=list(cmd[:5]),
                  renderer={k:env.get(k) for k in ("GALLIUM_DRIVER","LIBGL_ALWAYS_SOFTWARE","QT_QPA_PLATFORM",
                             "MESA_D3D12_DEFAULT_ADAPTER_NAME","GZ_SIM_RENDER_ENGINE","DISPLAY")})
            return proc
    def stop(proc):
        if proc is None: return real_stop(proc)
        event("cleanup_begin",pid=proc.pid,role=roles.get(proc.pid,"unknown"),rc=proc.poll())
        try: return real_stop(proc)
        finally: event("cleanup_end",pid=proc.pid,role=roles.get(proc.pid,"unknown"),rc=proc.poll())
    def call(env,world,payload,*args,**kwargs):
        nonlocal injected
        result=real_call(env,world,payload,*args,**kwargs)
        if gui is not None and payload=="pause: false":
            event("observation_unpaused",gui_pid=gui.pid,gui_rc=gui.poll())
            if a.inject_gui_abort and not injected:
                if gui.poll() is not None: raise RuntimeError("DBG_GUI_NOT_ALIVE_BEFORE_INJECTION")
                os.killpg(gui.pid,signal.SIGABRT)
                injected=True;event("gui_abort_injected",pid=gui.pid,signal=int(signal.SIGABRT))
        if gui is not None and payload=="pause: true": event("observation_paused",gui_rc=gui.poll())
        return result
    live.subprocess=Proxy()
    live.stop_owned=stop
    live.gz_call=call
    preflight.gui_profile_env=lambda env,profile:renderer_env(real_gui_env(env,profile),not a.native_gui)
    os.environ.setdefault("SMARTDISH_A_TRAY_GUI_PROFILE","xcb")
    # Avoid huge core dumps during CI signal injection; does not change exit code.
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    try:
        live.run(argparse.Namespace(mode="single",scene=a.scene,seed=211,
                  expected_sha=a.sha,a14_static=True,gui=not a.headless))
    finally:
        a.trace.write_text(json.dumps(dict(source_sha=a.sha,scene_id=a.scene,
                      injected=injected,events=events),indent=2,sort_keys=True)+"\n")
        live.subprocess=real_subprocess
        live.stop_owned=real_stop
        live.gz_call=real_call
        preflight.gui_profile_env=real_gui_env
        live.split_scene_for_sensor_warmup=original_split
        physics.retain_contact_sample=original_retain
        physics.build_v2=original_build
if __name__=="__main__":
    main()
