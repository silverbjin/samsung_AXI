#!/usr/bin/env python3
"""DBG-17: isolated REAL Gazebo GUI/Qt preflight before any dish simulation.

No ROS goals, no training labels, no global Gazebo kill. The lightweight world
and GUI use a private GZ_PARTITION and only owned child process groups.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import tarfile
from datetime import datetime, timezone

PROFILES=("xcb","native")
FATAL=re.compile(
    r"Failed to create OpenGL context|QGLXContext: Failed|"
    r"glx: failed to create dri|glx: failed to create drisw|"
    r"QSGRenderLoop::handleContextCreationFailure|"
    r"Failed to create dummy context|Aborted \(Signal|"
    r"Could not load the Qt platform plugin",re.I)
WORLD="smartdish_gui_preflight"
# Minimal static visual ensures GUI loads its 3D scene; no robotics/physics goals.
SDF="""<?xml version="1.0"?>
<sdf version="1.9">
 <world name="smartdish_gui_preflight">
  <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
  <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
  <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
  <scene><ambient>0.6 0.6 0.6 1</ambient><background>0.2 0.3 0.4 1</background></scene>
  <model name="context_probe_cube"><static>true</static>
    <link name="link"><visual name="visual"><geometry><box><size>1 1 1</size></box></geometry></visual></link>
  </model>
 </world>
</sdf>
"""


def gui_profile_env(source, profile):
    """Preserve user's NVIDIA D3D12 vars. XCB is scoped to GUI, not ~/.bashrc."""
    if profile not in PROFILES:
        raise ValueError("A13_GUI_PROFILE_UNAPPROVED")
    env=dict(source)
    if profile=="xcb":
        if not env.get("DISPLAY"):
            raise RuntimeError("A13_GUI_XCB_DISPLAY_MISSING")
        env["QT_QPA_PLATFORM"]="xcb"
        env.pop("WAYLAND_DISPLAY",None)
    env["QSG_INFO"]="1"
    return env


def gui_failure(log, code, duration, minimum):
    if FATAL.search(log):
        return "A13_GUI_CONTEXT_CREATION_FAILED"
    if code is not None:
        return "A13_GUI_PROCESS_EXITED_RC="+str(code)
    if duration<minimum:
        return "A13_GUI_STABILITY_WINDOW_INCOMPLETE"
    return None


def stop_owned(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGINT)
        proc.wait(timeout=6)
    except (ProcessLookupError,subprocess.TimeoutExpired):
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL)
                proc.wait(timeout=3)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_gui_preflight(root:Path, source_sha:str, profile="xcb", seconds=9.0,
                      out_dir:Path|None=None):
    if not re.fullmatch("[0-9a-f]{40}",source_sha):
        raise RuntimeError("A13_GUI_PREFLIGHT_SHA_INVALID")
    actual=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                   text=True,timeout=8).strip()
    if actual!=source_sha:
        raise RuntimeError("A13_GUI_PREFLIGHT_SOURCE_SHA_MISMATCH")
    if seconds<3.0 or seconds>30.0:
        raise RuntimeError("A13_GUI_PREFLIGHT_DURATION_INVALID")
    env=gui_profile_env(os.environ,profile)
    if not env.get("DISPLAY") and not env.get("WAYLAND_DISPLAY"):
        raise RuntimeError("A13_GUI_PREFLIGHT_DISPLAY_MISSING")
    start_utc=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder=(out_dir if out_dir else root/"generated/smartdish_tray"/
            ("gui_preflight_"+start_utc+"_"+str(os.getpid())))
    folder.mkdir(parents=True,exist_ok=False)
    world=folder/"minimal_gui_world.sdf"
    world.write_text(SDF)
    private_env=dict(env)
    private_env["GZ_PARTITION"]="smartdish_dbg17_"+str(os.getpid())+"_"+start_utc
    report={"schema":1,"source_sha":source_sha,"profile":profile,
            "verdict":"NOT_RUN","phase":"create",
            "requires_real_gazebo_gui":True,
            "profile_env":{"DISPLAY":env.get("DISPLAY"),
               "WAYLAND_DISPLAY":env.get("WAYLAND_DISPLAY"),
               "QT_QPA_PLATFORM":env.get("QT_QPA_PLATFORM"),
               "QSG_INFO":env.get("QSG_INFO"),
               "GALLIUM_DRIVER":env.get("GALLIUM_DRIVER"),
               "MESA_D3D12_DEFAULT_ADAPTER_NAME":env.get("MESA_D3D12_DEFAULT_ADAPTER_NAME"),
               "LIBGL_ALWAYS_SOFTWARE":env.get("LIBGL_ALWAYS_SOFTWARE")},
            "world_sha256":sha256(world),"gazebo_server_ready":False,
            "gui_started":False,"gui_survival_wall_s":0.0,
            "first_error":None,"process_cleanup":[]}
    procs=[];files=[]
    try:
        report["phase"]="gazebo_server"
        server_log=(folder/"gazebo_server.log").open("w")
        files.append(server_log)
        srv=subprocess.Popen(["gz","sim","-s","-v2",str(world)],
            env=private_env,stdin=subprocess.DEVNULL,
            stdout=server_log,stderr=subprocess.STDOUT,start_new_session=True)
        procs.append(srv)
        timeout_at=time.monotonic()+28.0
        while time.monotonic()<timeout_at:
            if srv.poll() is not None:
                raise RuntimeError("A13_GUI_PREFLIGHT_SERVER_EXITED")
            service=subprocess.run(["gz","service","-l"],env=private_env,
                capture_output=True,text=True,timeout=5)
            if service.returncode==0 and "/world/"+WORLD+"/control" in service.stdout:
                report["gazebo_server_ready"]=True
                break
            time.sleep(.5)
        if not report["gazebo_server_ready"]:
            raise RuntimeError("A13_GUI_PREFLIGHT_SERVER_NOT_READY")
        report["phase"]="gazebo_gui_context"
        gui_log=(folder/"gazebo_gui.log").open("w")
        files.append(gui_log)
        gui=subprocess.Popen(["gz","sim","-g","-v2"],
            env=private_env,stdin=subprocess.DEVNULL,
            stdout=gui_log,stderr=subprocess.STDOUT,start_new_session=True)
        procs.append(gui)
        report["gui_started"]=True
        since=time.monotonic()
        while time.monotonic()-since<seconds:
            gui_log.flush()
            log=(folder/"gazebo_gui.log").read_text(errors="replace")[-65536:]
            reason=gui_failure(log,gui.poll(),time.monotonic()-since,seconds)
            if reason and reason!="A13_GUI_STABILITY_WINDOW_INCOMPLETE":
                raise RuntimeError(reason)
            if srv.poll() is not None:
                raise RuntimeError("A13_GUI_PREFLIGHT_SERVER_DIED_DURING_GUI")
            time.sleep(.25)
        log=(folder/"gazebo_gui.log").read_text(errors="replace")[-65536:]
        report["gui_survival_wall_s"]=round(time.monotonic()-since,3)
        reason=gui_failure(log,gui.poll(),report["gui_survival_wall_s"],seconds)
        if reason:
            raise RuntimeError(reason)
        report["verdict"]="GAZEBO_GUI_PROCESS_STABLE_NO_GLX_ERROR"
        report["phase"]="completed"
    except BaseException as exc:
        report["verdict"]="FAIL"
        report["first_error"]=str(exc)
        print("A13_GUI_CONTEXT_PREFLIGHT_FAIL="+str(exc),flush=True)
    finally:
        for proc in reversed(procs):
            stop_owned(proc)
            report["process_cleanup"].append(
                {"pid":proc.pid,"returncode_after_cleanup":proc.poll(),
                 "stopped":proc.poll() is not None})
        for fp in files:
            fp.close()
        report["all_owned_processes_stopped"]=all(
            x["stopped"] for x in report["process_cleanup"])
        report["gui_log_has_qsg_info"]=bool(
            re.search(r"scene graph|QSG|OpenGL|render loop",(
                folder/"gazebo_gui.log").read_text(errors="replace"),re.I)
            if (folder/"gazebo_gui.log").exists() else False)
        if report["verdict"]!="FAIL" and not report["all_owned_processes_stopped"]:
            report["verdict"]="FAIL"
            report["first_error"]="A13_GUI_PREFLIGHT_PROCESS_CLEANUP_FAILED"
        result=folder/"gui_preflight_result.json"
        result.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        rows=[]
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.name not in ("SHA256SUMS","gui_preflight_evidence.tar.gz"):
                rows.append(sha256(path)+"  "+path.name)
        (folder/"SHA256SUMS").write_text("\n".join(rows)+"\n")
        bundle=folder/"gui_preflight_evidence.tar.gz"
        with tarfile.open(bundle,"w:gz") as t:
            for path in sorted(folder.iterdir()):
                if path.is_file() and path!=bundle:
                    t.add(path,arcname=path.name)
        print("SMARTDISH_A_TRAY_GUI_PREFLIGHT_RESULT="+str(result),flush=True)
        print("SMARTDISH_A_TRAY_GUI_PREFLIGHT_EVIDENCE="+str(bundle),flush=True)
        if report["verdict"]=="FAIL":
            raise RuntimeError(report["first_error"])
    print("SMARTDISH_A_TRAY_GUI_PREFLIGHT_PASS="+str(result),flush=True)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sha",required=True)
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--profile",choices=PROFILES,default="xcb")
    p.add_argument("--seconds",type=float,default=9.0)
    a=p.parse_args()
    try:
        run_gui_preflight(a.root,a.sha,a.profile,a.seconds)
    except Exception as e:
        print("SMARTDISH_A_TRAY_GUI_PREFLIGHT_BLOCKED="+str(e),file=sys.stderr)
        sys.exit(2)


if __name__=="__main__":
    main()
