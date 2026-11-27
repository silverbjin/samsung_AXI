"""Actual Owner Tk UI. No automatic start, threshold or staff approval."""
import json,os,time,sys
from pathlib import Path
from smartdish_e_product_owner_scope import require_owner
def main():
    require_owner(os.environ["SMARTDISH_E_SOURCE_SHA"],os.environ["SMARTDISH_E_OWNER_PRODUCT_RUN"])
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
    from smartdish_service.product_admission import product_ai_on_authorized
    if not product_ai_on_authorized(True,owner_gazebo_integration=True):raise RuntimeError("E_OWNER_UI_ADMISSION")
    out=Path(sys.argv[1]);rclpy.init();node=Node("smartdish_ui")
    root=tk.Tk();qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)
    pubs={k:node.create_publisher(String,"/collection/"+k,qos) for k in ("request","staff_confirm")}
    txn=ThresholdTransaction(AsyncParameterClient(node,"/smartdish_stability_inference"));events=[]
    def record(event,body):
        events.append(dict(event=event,steady_s=time.monotonic(),body=body))
        (out/"ui_events.json").write_text(json.dumps(events,indent=2)+"\n")
    def send(topic,body):
        record(topic,body);m=String();m.data=json.dumps(body,allow_nan=False);pubs[topic].publish(m)
    view=RecoveryView(root,read_layout(Path(get_package_share_directory("smartdish_service"))/"config/ui_layout.yaml"),send,txn.request,True)
    def status(m):
        d=json.loads(m.data);view.on_status(d)
        if d.get("request_id")==view.request_id:record("status",d)
    node.create_subscription(String,"/collection/status",status,qos)
    node.create_subscription(String,"/collection/capture_result",lambda m:view.on_capture(json.loads(m.data)),qos)
    def frame(m):
        if view.frame_cache.add(m):view.render_preview()
    node.create_subscription(Image,"/smartdish/tray/image_raw",frame,qos)
    closed=False
    def close():
        nonlocal closed
        if view.request_id:view.staff("ABORT")
        else:closed=True
        record("operator_window_close",dict(state=view.state))
    root.protocol("WM_DELETE_WINDOW",close)
    result={"completed":False};threshold=False;preview=False
    deadline=time.monotonic()+700
    try:
        while time.monotonic()<deadline:
            root.update()
            for _ in range(5):rclpy.spin_once(node,timeout_sec=0)
            txn.poll()
            if view.threshold_confirmed and not threshold:
                record("threshold_set_get",dict(confirmed=True));threshold=True
            if view.state=="NEEDS_CONFIRMATION" and view.photo is not None and not preview:
                record("preview_ready",dict(capture_id=view.capture_id,text=view.preview_text.get()));preview=True
            if view.state=="COMPLETED":
                requests=[x for x in events if x["event"]=="request"]
                approvals=[x for x in events if x["event"]=="staff_confirm" and x["body"]["action"]=="APPROVE_CONTINUE"]
                result=dict(completed=True,started=len(requests)==1,staff_operator_click=len(approvals)==1,
                            preview=preview and view.photo is not None,threshold_set_get=threshold,automatic_click=False)
                break
            if closed or view.state in ("ERROR","ABORTED","SAFE_HOLD","SAFE_HOLD_UNVERIFIED","CANCELED"):
                result=dict(completed=False,state=view.state,details=view.details.get(),window_closed=closed);break
            time.sleep(.01)
    finally:
        (out/"ui_result.json").write_text(json.dumps(result,indent=2)+"\n")
        root.destroy();node.destroy_node();rclpy.shutdown()
    if not all(result.get(k) for k in ("completed","started","staff_operator_click","preview","threshold_set_get")):
        raise RuntimeError("E_OWNER_UI_NOT_COMPLETE:"+str(result))
if __name__=="__main__":main()
