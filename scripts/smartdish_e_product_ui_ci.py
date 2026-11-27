"""Actual D Tk widgets and DDS, test operator only; never an Owner approval path."""
import json,os,time,sys
from pathlib import Path
def main():
    if os.environ.get("GITHUB_ACTIONS")!="true" or os.environ.get("WSL_DISTRO_NAME") or not os.environ.get("GZ_PARTITION","").startswith("smartdish_a04_e_"):
        raise RuntimeError("CI_UI_ONLY")
    import tkinter as tk
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter_client import AsyncParameterClient
    from rclpy.qos import QoSProfile,ReliabilityPolicy
    from std_msgs.msg import String
    from sensor_msgs.msg import Image
    from ament_index_python.packages import get_package_share_directory
    from smartdish_service.product_recovery_ui import RecoveryView,read_layout
    from smartdish_service.product_recovery_thresholds import ThresholdTransaction
    out=Path(sys.argv[1]);rclpy.init();node=Node("smartdish_ui")
    root=tk.Tk();qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)
    pubs={k:node.create_publisher(String,"/collection/"+k,qos) for k in ("request","staff_confirm")}
    client=AsyncParameterClient(node,"/smartdish_stability_inference")
    txn=ThresholdTransaction(client);events=[]
    def record(event,body):
        events.append(dict(event=event,steady_s=time.monotonic(),body=body))
        (out/"ui_events.json").write_text(json.dumps(events,indent=2)+"\n")
    def send(topic,body):
        record(topic,body);m=String();m.data=json.dumps(body);pubs[topic].publish(m)
    view=RecoveryView(root,read_layout(Path(get_package_share_directory("smartdish_service"))/"config/ui_layout.yaml"),send,txn.request,True)
    def status(m):
        d=json.loads(m.data);view.on_status(d)
        if d.get("request_id")==view.request_id:record("status",d)
    node.create_subscription(String,"/collection/status",status,qos)
    node.create_subscription(String,"/collection/capture_result",lambda m:view.on_capture(json.loads(m.data)),qos)
    def frame(m):
        if view.frame_cache.add(m):view.render_preview()
    node.create_subscription(Image,"/smartdish/tray/image_raw",frame,qos)
    result={"completed":False};started=False;threshold=False;approved=False;eligible=None
    deadline=time.monotonic()+700
    try:
        while time.monotonic()<deadline:
            root.update()
            for _ in range(5):rclpy.spin_once(node,timeout_sec=0)
            txn.poll()
            if view.ready and not threshold and client.services_are_ready():
                view.select();view.threshold_button.invoke();threshold=True
            if view.threshold_confirmed and not started and str(view.start_button.cget("state"))=="normal":
                record("threshold_set_get",dict(confirmed=True));view.start_button.invoke();started=True
            if view.state=="NEEDS_CONFIRMATION" and str(view.approve.cget("state"))=="normal" and not approved:
                if eligible is None:eligible=time.monotonic();record("preview_ready",dict(capture_id=view.capture_id,text=view.preview_text.get()))
                if time.monotonic()-eligible>=.5:
                    view.approve.invoke();approved=True
            if view.state=="COMPLETED":
                result={"completed":True,"started":started,"staff_test_click":approved,"preview":view.photo is not None};break
            if view.state in ("ERROR","ABORTED","SAFE_HOLD","SAFE_HOLD_UNVERIFIED","CANCELED"):
                result={"completed":False,"state":view.state,"details":view.details.get()};break
            time.sleep(.01)
    finally:
        (out/"ui_result.json").write_text(json.dumps(result,indent=2)+"\n")
        root.destroy();node.destroy_node();rclpy.shutdown()
    if not all(result.get(k) for k in ("completed","started","staff_test_click","preview")):raise RuntimeError("E_UI_CI_NOT_COMPLETE:"+str(result))
if __name__=="__main__":main()
