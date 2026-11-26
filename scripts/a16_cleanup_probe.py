"""One minimal camera-only teardown diagnostic, not a repeated A15/A16 layout."""
import json,os,random,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
import rclpy
from sensor_msgs.msg import Image
from rclpy.qos import qos_profile_sensor_data
from smartdish_platform.lifecycle import stop_owned
from smartdish_tray_world import build_world
from smartdish_tray_camera import TOPIC
from smartdish_a_tray_live import gz_call
def run(root,out):
    out=Path(out).resolve();root=Path(root).resolve()
    tree,_=build_world("ST-01",101);w=tree.find("world")
    for m in list(w.findall("model")):
        if m.get("name","").startswith("dish_"):w.remove(m)
    sdf=out/"cleanup_probe.sdf";ET.ElementTree(tree).write(sdf,encoding="utf-8",xml_declaration=True)
    env=dict(os.environ,GZ_PARTITION="a16_cleanup_"+str(os.getpid()),ROS_DOMAIN_ID=str(random.randrange(40,180)))
    p=[];handles=[];node=None;initialized=False;frames=[];status={"scope":"MINIMAL_CAMERA_ONLY_NO_DISH_NO_CONTACT_PLUGIN","data":"NOT_RUN","cleanup":"NOT_RUN","first_error":None,"renderer":{k:env.get(k) for k in ("GALLIUM_DRIVER","MESA_D3D12_DEFAULT_ADAPTER_NAME","LIBGL_ALWAYS_SOFTWARE")}}
    try:
        for role,cmd in [("server",["gz","sim","-s","-v2",str(sdf)]),("bridge",["ros2","run","ros_gz_bridge","parameter_bridge","--ros-args","-p","config_file:="+str(root/"config/smartdish_tray_bridge.yaml")])]:
            h=(out/f"cleanup_probe_{role}.log").open("x");handles.append(h);p.append((role,subprocess.Popen(cmd,env=env,stdout=h,stderr=subprocess.STDOUT,start_new_session=True)))
        rclpy.init(args=None,domain_id=int(env["ROS_DOMAIN_ID"]));initialized=True
        node=rclpy.create_node("a16_cleanup_"+str(os.getpid()))
        node.create_subscription(Image,TOPIC,lambda m:frames.append(m.header.stamp.sec*1000000000+m.header.stamp.nanosec),qos_profile_sensor_data)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            if any(proc.poll() is not None for _,proc in p):raise RuntimeError("CLEANUP_PROBE_EARLY_EXIT")
            rclpy.spin_once(node,timeout_sec=.05)
            r=subprocess.run(["gz","service","-l"],env=env,capture_output=True,text=True,timeout=7)
            if "/world/smartdish_tray/control" in r.stdout and node.count_publishers(TOPIC)>0:break
        else:raise RuntimeError("CLEANUP_PROBE_READY_TIMEOUT")
        gz_call(env,"smartdish_tray","pause: false")
        deadline=time.monotonic()+30
        while time.monotonic()<deadline and not any(t>=1000000000 for t in frames):
            rclpy.spin_once(node,timeout_sec=.05)
            if any(proc.poll() is not None for _,proc in p):raise RuntimeError("CLEANUP_PROBE_EARLY_EXIT")
        if not any(t>=1000000000 for t in frames):raise RuntimeError("CLEANUP_PROBE_IMAGE_TIMEOUT")
        gz_call(env,"smartdish_tray","pause: true");status["data"]="PASS"
    except Exception as exc:status["first_error"]=str(exc);status["data"]="HOLD"
    finally:
        if node:node.destroy_node()
        if initialized:rclpy.shutdown()
        rows=[]
        for role,proc in reversed(p):
            start=time.monotonic_ns()
            try:r=stop_owned(proc)
            except Exception as exc:r={"pid":proc.pid,"returncode":proc.poll(),"stopped":proc.poll() is not None,"error":str(exc)}
            r.update(role=role,start_monotonic_ns=start,end_monotonic_ns=time.monotonic_ns())
            try:os.killpg(proc.pid,0);r["group_remaining"]=True
            except ProcessLookupError:r["group_remaining"]=False
            except PermissionError:r["group_remaining"]=True
            rows.append(r)
        for h in handles:h.close()
        status["processes"]=rows;status["frame_stamps_ns"]=frames[:500]
        status["all_owned_stopped"]=bool(rows) and all(r["stopped"] and not r["group_remaining"] for r in rows)
        status["cleanup"]="PASS" if status["all_owned_stopped"] and len(rows)==2 and all(r["returncode"]==0 for r in rows) else "FAIL"
        (out/"cleanup_probe.json").write_text(json.dumps(status,indent=2,sort_keys=True)+"\n")
        print("A16_CLEANUP_PROBE="+json.dumps({k:status[k] for k in ("data","cleanup","all_owned_stopped")}),flush=True)
    return 0 if status["all_owned_stopped"] else 2
if __name__=="__main__":raise SystemExit(run(sys.argv[1],sys.argv[2]))
