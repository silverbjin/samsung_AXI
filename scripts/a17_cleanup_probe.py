#!/usr/bin/env python3
"""A17 bounded camera-only reproduction. No A15/A16 production scene replay."""
import argparse,hashlib,json,os,random,shutil,signal,subprocess,sys,time,uuid
from pathlib import Path
import xml.etree.ElementTree as ET
from a17_cleanup_contract import *
from smartdish_platform.lifecycle import stop_owned
from smartdish_tray_world import build_world
from smartdish_tray_camera import TOPIC
from smartdish_a_tray_live import gz_call

def cmd(args,env,timeout=12):
    try:
        p=subprocess.run(args,env=env,text=True,capture_output=True,timeout=timeout)
        return {"rc":p.returncode,"stdout":p.stdout[-24000:],"stderr":p.stderr[-4000:]}
    except (OSError,subprocess.TimeoutExpired) as exc:return {"rc":None,"error":str(exc)}
def make_world(path):
    tree,_=build_world("ST-01",101)
    w=tree.find("world")
    for m in list(w.findall("model")):
        if m.get("name","").startswith("dish_"):w.remove(m)
    ET.ElementTree(tree).write(path,encoding="utf-8",xml_declaration=True)
    if sha(path)!=HISTORICAL_WORLD_SHA:raise RuntimeError("A17_HISTORICAL_WORLD_SHA_DRIFT")
def snapshot(pid,out,env):
    for name in ("maps","status","cmdline"):
        try:
            data=Path("/proc",str(pid),name).read_bytes()
            (out/(name+".txt")).write_bytes(data.replace(b"\0",b" ") if name=="cmdline" else data)
        except OSError as exc:(out/(name+".txt")).write_text("UNAVAILABLE "+str(exc))
    dump(out/"renderer_probe.json",{"requested":{k:env.get(k) for k in ENV_KEYS},"glxinfo_same_environment_not_server_context":cmd(["glxinfo","-B"],env),"maps_scope":"LOADED_LIBRARIES_NOT_DIRECT_GL_CONTEXT_PROOF"})
def probe(root,out,sdf,profile,debug=False,*,server_env_override=None):
    import rclpy
    from sensor_msgs.msg import Image
    from rclpy.qos import qos_profile_sensor_data
    out.mkdir()
    env=renderer(os.environ,profile)
    env.update(GZ_PARTITION="a17_"+uuid.uuid4().hex,ROS_DOMAIN_ID=str(random.randrange(40,180)),GZ_SIM_RENDER_ENGINE="ogre2")
    # ROS domain and partition isolated; display/Qt unchanged between compared profiles.
    state={"profile":profile,"instrumentation":"GDB" if debug else "DIRECT","world_sha256":sha(sdf),"data":"HOLD","cleanup":"NOT_RUN","first_error":None,"server_rc":None,"bridge_rc":None,"all_owned_stopped":False,"shutdown_signal_sent":False,"frames":[]}
    handles=[];server=None;bridge=None;node=None;initialized=False;inferior=None
    def launch(role,args,child_env):
        h=(out/(role+".log")).open("x");handles.append(h)
        return subprocess.Popen(args,env=child_env,stdout=h,stderr=subprocess.STDOUT,start_new_session=True)
    def spin():
        if server.poll() is not None or bridge.poll() is not None:raise RuntimeError("A17_EARLY_EXIT")
        rclpy.spin_once(node,timeout_sec=.05)
    def image(m):
        t=int(m.header.stamp.sec)*1000000000+int(m.header.stamp.nanosec)
        if len(state["frames"])<200 and m.encoding=="rgb8" and m.width==640 and m.height==480 and m.step==1920 and len(m.data)==640*480*3:
            state["frames"].append({"stamp_ns":t,"sha256":hashlib.sha256(bytes(m.data)).hexdigest()})
    try:
        gz=shutil.which("gz")
        if not gz:raise RuntimeError("A17_GZ_MISSING")
        args=[gz,"sim","-s","-v2",str(sdf)]
        if debug:
            if not shutil.which("gdb") or not shutil.which("ruby") or b"ruby" not in Path(gz).open("rb").readline():raise RuntimeError("A17_GDB_OR_RUBY_CLI_UNSUPPORTED")
            e=dict(env,A17_GDB_OUT=str(out))
            server=launch("server",["gdb","-q","-nx","--batch","-x",str(root/"scripts/a17_gdb_capture.py"),"--args","ruby",*args],e)
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                if server.poll() is not None:raise RuntimeError("A17_GDB_EARLY_EXIT")
                if (out/"gdb_status.json").is_file():
                    s=json.loads((out/"gdb_status.json").read_text())
                    if s.get("inferior_pid"):
                        inferior=s;break
                time.sleep(.1)
            if inferior is None or not owned_inferior(inferior["inferior_pid"],inferior["start_ticks"],server.pid):raise RuntimeError("A17_GDB_INFERIOR_NOT_OWNED")
        else:
            child_env=dict(env)
            if server_env_override is not None:child_env.update(server_env_override)
            server=launch("server",args,child_env)
        bridge=launch("bridge",["ros2","run","ros_gz_bridge","parameter_bridge","--ros-args","-p","config_file:="+str(root/"config/smartdish_tray_bridge.yaml")],env)
        rclpy.init(args=None,domain_id=int(env["ROS_DOMAIN_ID"]));initialized=True
        node=rclpy.create_node("a17_cleanup_"+uuid.uuid4().hex[:12])
        node.create_subscription(Image,TOPIC,image,qos_profile_sensor_data)
        deadline=time.monotonic()+65
        while time.monotonic()<deadline:
            spin()
            r=cmd(["gz","service","-l"],env,7)
            if "/world/smartdish_tray/control" in r.get("stdout","") and node.count_publishers(TOPIC)>0:break
        else:raise RuntimeError("A17_READY_TIMEOUT")
        gz_call(env,"smartdish_tray","pause: false")
        deadline=time.monotonic()+35
        while time.monotonic()<deadline and not any(x["stamp_ns"]>=1000000000 for x in state["frames"]):spin()
        if not any(x["stamp_ns"]>=1000000000 for x in state["frames"]):raise RuntimeError("A17_RGB_TIMEOUT")
        gz_call(env,"smartdish_tray","pause: true")
        pid=inferior["inferior_pid"] if debug else server.pid
        snapshot(pid,out,env)
        state["data"]="PASS"
        print("A17_CAMERA_PASS="+out.name,flush=True)
    except Exception as exc:state["first_error"]=type(exc).__name__+": "+str(exc)
    finally:
        if node:node.destroy_node()
        if initialized:rclpy.shutdown()
        procs=[]
        if bridge:
            row=stop_owned(bridge);row.update(role="bridge",group_remaining=group_remaining(bridge.pid));procs.append(row);state["bridge_rc"]=row["returncode"]
        if server:
            if debug and inferior:
                try:
                    signal_inferior(inferior["inferior_pid"],inferior["start_ticks"],server.pid,signal.SIGINT);state["shutdown_signal_sent"]=True
                    server.wait(timeout=45)
                except (RuntimeError,ProcessLookupError,subprocess.TimeoutExpired) as exc:state["debug_shutdown_error"]=str(exc)
                if server.poll() is None and owned_inferior(inferior["inferior_pid"],inferior["start_ticks"],server.pid):
                    signal_inferior(inferior["inferior_pid"],inferior["start_ticks"],server.pid,signal.SIGKILL)
                row=stop_owned(server);state["debugger_rc"]=row["returncode"]
                if (out/"gdb_status.json").exists():
                    s=json.loads((out/"gdb_status.json").read_text());state["gdb"]=s;state["server_rc"]=gdb_exit(s)
                state["inferior_remaining"]=owned_inferior(inferior["inferior_pid"],inferior["start_ticks"],server.pid)
            else:
                row=stop_owned(server);state["shutdown_signal_sent"]=2 in row["signals"]
                if not debug:state["server_rc"]=row["returncode"]
            row.update(role="debugger" if debug else "server",group_remaining=group_remaining(server.pid));procs.append(row)
        for h in handles:h.close()
        state["processes"]=procs
        state["all_owned_stopped"]=len(procs)==2 and all(p["stopped"] and not p["group_remaining"] for p in procs) and not state.get("inferior_remaining",False)
        state["cleanup"]="PASS" if state["all_owned_stopped"] and state["server_rc"]==state["bridge_rc"]==0 and state["shutdown_signal_sent"] else "FAIL"
        dump(out/"verdict.json",state)
        print("A17_CASE="+json.dumps({k:state[k] for k in ("profile","instrumentation","data","cleanup","server_rc","bridge_rc","all_owned_stopped","first_error")}),flush=True)
    return state
def main():
    p=argparse.ArgumentParser();p.add_argument("--sha",required=True);p.add_argument("--out",required=True,type=Path);p.add_argument("--ci",action="store_true");a=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=a.out.resolve();out.mkdir(parents=True,exist_ok=False,mode=0o700)
    report={"source_sha":a.sha,"scope":"A17_CAMERA_ONLY_DIAGNOSTIC","historical_cleanup":"FAIL","root_cause":"UNPROVEN","production_contact_health":"HOLD","human_approved":False,"cases":[],"first_error":None}
    rc=2
    try:
        head=cmd(["git","-C",str(root),"rev-parse","HEAD"],os.environ)
        clean=cmd(["git","-C",str(root),"status","--porcelain","--untracked-files=no"],os.environ)
        gz=cmd(["gz","sim","--versions"],os.environ)
        dump(out/"preflight.json",{"actual_head":head,"tracked_clean":clean,"gz_version":gz,"gdb_version":cmd(["gdb","--version"],os.environ),"kernel":cmd(["uname","-r"],os.environ),"ros_distro":os.environ.get("ROS_DISTRO"),"renderer":{k:os.environ.get(k) for k in ENV_KEYS},"packages":cmd(["dpkg-query","-W","-f=${Package} ${Version}\\n","*mesa*","*gz-sim*","*ogre*"],os.environ)})
        if head.get("stdout","").strip()!=a.sha or clean.get("rc")!=0 or clean.get("stdout") or gz.get("stdout","").strip()!="8.15.0" or os.environ.get("ROS_DISTRO")!="jazzy":raise RuntimeError("A17_PREFLIGHT")
        if not a.ci and (os.environ.get("GALLIUM_DRIVER")!="d3d12" or os.environ.get("LIBGL_ALWAYS_SOFTWARE")=="1"):raise RuntimeError("A17_NATIVE_D3D12_ENV_REQUIRED")
        if a.ci and os.environ.get("CI")!="true":raise RuntimeError("A17_CI_ONLY")
        if not shutil.which("gdb"):raise RuntimeError("A17_GDB_MISSING_INSTALL_EXPLICITLY")
        sdf=out/"camera_only.sdf";make_world(sdf)
        for profile in (["software"] if a.ci else ["native","software"]):
            r=probe(root,out/(profile+"_direct"),sdf,profile);report["cases"].append(r)
            if not r["all_owned_stopped"]:raise RuntimeError("A17_PROCESS_REMAINS")
        # CI validates the actual GDB server path once, even if direct case is clean.
        # Owner only repeats a failed minimal case under debugger, at most two.
        for r in list(report["cases"]):
            if a.ci or (r["data"]=="PASS" and r["server_rc"]==-11):
                q=probe(root,out/(r["profile"]+"_gdb"),sdf,r["profile"],True);report["cases"].append(q)
                if not q["all_owned_stopped"]:raise RuntimeError("A17_DEBUG_PROCESS_REMAINS")
        report["contrast"]=compare(report["cases"])
        if a.ci:
            if len(report["cases"])!=2 or not all(r["data"]=="PASS" and r["cleanup"]=="PASS" for r in report["cases"]):raise RuntimeError("A17_CI_SOFTWARE_CONTRACT")
        elif not all(r["data"]=="PASS" for r in report["cases"] if r["instrumentation"]=="DIRECT"):raise RuntimeError("A17_DIRECT_DATA_HOLD")
        report["diagnostic_collection"]="COMPLETE_ROOT_UNPROVEN";rc=0
    except Exception as exc:report["first_error"]=type(exc).__name__+": "+str(exc);report["diagnostic_collection"]="HOLD"
    finally:
        report["exit_code"]=rc;dump(out/"a17_report.json",report);archive(out)
    return rc
if __name__=="__main__":raise SystemExit(main())
