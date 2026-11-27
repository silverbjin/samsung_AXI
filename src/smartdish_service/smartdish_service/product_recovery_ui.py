"""Owner recovery UI. No legacy UI changes; no self-generated A/C results."""
import base64
import hashlib
import json
import time
import uuid
from collections import OrderedDict
from .product_recovery_fsm import PROFILE, RecoveryFSM, digest
from .product_admission import product_ai_on_authorized
from .ui_app import read_layout

class FrameCache:
    """Bounded received-monotonic cache of canonical packed RGB, not PNG."""
    def __init__(self,clock=time.monotonic):
        self.clock=clock
        self.frames=OrderedDict()
    def add(self,msg):
        if (msg.header.frame_id!="smartdish_tray_optical" or msg.width!=640 or msg.height!=480
                or msg.encoding not in {"rgb8","bgr8"} or msg.step<1920
                or len(msg.data)!=msg.step*480 or msg.is_bigendian not in (0,1)):
            return False
        stamp=msg.header.stamp.sec*1000000000+msg.header.stamp.nanosec
        if stamp<0:
            return False
        if self.frames and stamp<next(reversed(self.frames)):
            self.frames.clear()
            return False
        raw=bytes(msg.data)
        rgb=b"".join(raw[i*msg.step:i*msg.step+1920] for i in range(480))
        if msg.encoding=="bgr8":
            out=bytearray(len(rgb))
            out[0::3],out[1::3],out[2::3]=rgb[2::3],rgb[1::3],rgb[0::3]
            rgb=bytes(out)
        value=(hashlib.sha256(rgb).hexdigest(),rgb,self.clock())
        if stamp in self.frames and self.frames[stamp][0]!=value[0]:
            self.frames.pop(stamp)
            return False
        self.frames[stamp]=value
        while len(self.frames)>16:
            self.frames.popitem(last=False)
        return True
    def selected(self,ack):
        if (ack.get("status")!="ACK" or ack.get("frame_id")!="smartdish_tray_optical"
                or not digest(ack.get("rgb_sha256"))):
            return None
        v=self.frames.get(ack.get("image_stamp_ns"))
        if v is None or v[0]!=ack["rgb_sha256"] or self.clock()-v[2]>2:
            return None
        return v[1]

class RecoveryView:
    def __init__(self,root,layout,send,request_thresholds,ai_available=False):
        import tkinter as tk
        from tkinter import ttk
        self.tk=tk
        self.root=root
        self.send=send
        self.request_thresholds=request_thresholds
        self.ai_available=ai_available
        self.request_id=""
        self.stack_id=None
        self.capture_id=None
        self.state="IDLE"
        self.ready=False
        self.pending=False
        self.selected=False
        self.frame_cache=FrameCache()
        self.capture_ack=None
        self.photo=None
        root.title("SmartDish · Owner 제품 복구")
        root.geometry("840x740")
        root.minsize(400,320)
        sc=tk.Canvas(root,highlightthickness=0)
        sb=ttk.Scrollbar(root,orient="vertical",command=sc.yview)
        sc.configure(yscrollcommand=sb.set)
        sb.pack(side="right",fill="y")
        sc.pack(side="left",fill="both",expand=True)
        body=ttk.Frame(sc,padding=12)
        window=sc.create_window(0,0,window=body,anchor="nw")
        body.bind("<Configure>",lambda e:sc.configure(scrollregion=sc.bbox("all")))
        sc.bind("<Configure>",lambda e:sc.itemconfigure(window,width=e.width))
        ttk.Label(body,text="식기 회수 · T03 / OWNER ONLY",font=("TkDefaultFont",16,"bold")).pack(anchor="w")
        self.status=tk.StringVar(value="IDLE / 실제 READY 대기")
        self.details=tk.StringVar(value="")
        self.preview_text=tk.StringVar(value="선택된 실제 RGB 없음")
        self.settings=tk.StringVar(value="C 설정 확인 필요")
        ttk.Label(body,textvariable=self.status,font=("TkDefaultFont",13,"bold")).pack(anchor="w",pady=4)
        ttk.Label(body,textvariable=self.details,wraplength=370).pack(anchor="w")
        canvas=tk.Canvas(body,width=350,height=202,background="#edf2f6")
        canvas.pack(anchor="w",pady=6)
        for tid,spec in layout["tables"].items():
            coords=[x*0.43 for x in spec["rect"]]
            rect=canvas.create_rectangle(*coords,fill="#ffc272" if tid=="T03" else "#d7dde4")
            label=canvas.create_text((coords[0]+coords[2])/2,(coords[1]+coords[3])/2,text=tid)
            if tid=="T03":
                for tag in (rect,label): canvas.tag_bind(tag,"<Button-1>",lambda e:self.select())
        for name,coords in layout["areas"].items():
            coords=[x*0.43 for x in coords]
            canvas.create_rectangle(*coords,fill="#cfe5e1")
            canvas.create_text((coords[0]+coords[2])/2,(coords[1]+coords[3])/2,text=name)
        self.table=tk.StringVar(value="T03 미선택")
        ttk.Label(body,textvariable=self.table).pack(anchor="w")
        fields=ttk.Frame(body)
        fields.pack(anchor="w")
        self.table_wait=tk.StringVar(value="10")
        self.dropoff_wait=tk.StringVar(value="5")
        self.ai=tk.BooleanVar(value=ai_available)
        self.stable=tk.StringVar(value="0.00")
        self.unstable=tk.StringVar(value="0.00")
        for i,(name,var,low,high,step) in enumerate((
            ("적재 대기(s)",self.table_wait,10,120,1),
            ("반납 대기(s)",self.dropoff_wait,5,60,1),
            ("STABLE min",self.stable,0,1,0.01),
            ("UNSTABLE min",self.unstable,0,1,0.01))):
            ttk.Label(fields,text=name).grid(row=i,column=0,sticky="w")
            w=ttk.Spinbox(fields,from_=low,to=high,increment=step,textvariable=var,width=9)
            w.grid(row=i,column=1)
            if i>=2:
                if i==2: self.threshold_widgets=[]
                self.threshold_widgets.append(w)
        self.ai_check=ttk.Checkbutton(body,text="AI ON (Owner 실험만)",variable=self.ai,command=self.refresh)
        self.ai_check.pack(anchor="w")
        self.threshold_button=ttk.Button(body,text="C 기준 적용 / 재조회",command=self.apply_thresholds)
        self.threshold_button.pack(anchor="w")
        ttk.Label(body,textvariable=self.settings,wraplength=370).pack(anchor="w")
        self.threshold_confirmed=False
        self.start_button=ttk.Button(body,text="T03 식기 회수 시작",command=self.start)
        self.start_button.pack(anchor="w",pady=4)
        buttons=ttk.Frame(body)
        buttons.pack(anchor="w")
        self.approve=ttk.Button(buttons,text="직원 승인",command=lambda:self.staff("APPROVE_CONTINUE"))
        self.abort=ttk.Button(buttons,text="중단 ABORT",command=lambda:self.staff("ABORT"))
        self.approve.pack(side="left",padx=3)
        self.abort.pack(side="left",padx=3)
        self.preview=ttk.Label(body)
        self.preview.pack(anchor="w")
        ttk.Label(body,textvariable=self.preview_text,wraplength=370).pack(anchor="w")
        self.refresh()

    def select(self):
        if self.state=="IDLE":
            self.selected=True
            self.table.set("T03 선택")
            self.refresh()
    def refresh(self):
        idle=self.state=="IDLE" and not self.pending
        def state(w,enabled): w.configure(state="normal" if enabled else "disabled")
        state(self.start_button,idle and self.ready and self.selected and (not self.ai.get() or self.threshold_confirmed))
        state(self.ai_check,idle and self.ai_available)
        state(self.threshold_button,idle and self.ai_available)
        for w in self.threshold_widgets: state(w,idle and self.ai_available)
        state(self.approve,self.state=="NEEDS_CONFIRMATION" and getattr(self,"approval_allowed",False))
        state(self.abort,self.state not in {"IDLE","COMPLETED","SAFE_HOLD","SAFE_HOLD_UNVERIFIED","ABORTED","ERROR","CANCELED","CANCELING"} and bool(self.capture_id))
    def apply_thresholds(self):
        if self.state!="IDLE" or self.pending or not self.ai_available:
            return
        try:
            values=RecoveryFSM.validate_thresholds((float(self.stable.get()),float(self.unstable.get())))
        except ValueError:
            self.settings.set("입력 오류: 0.00~1.00 유한 실수")
            return
        self.pending=True
        self.threshold_confirmed=False
        self.refresh()
        def done(ok,actual):
            self.pending=False
            self.threshold_confirmed=bool(ok and actual==values)
            self.settings.set("C set/get ACK "+str(actual) if self.threshold_confirmed else "C 기준 적용/재조회 실패")
            self.refresh()
        self.request_thresholds(values,done)
    def start(self):
        if self.state!="IDLE" or self.pending or not self.ready or not self.selected:
            return
        if self.ai.get() and (not self.ai_available or not self.threshold_confirmed):
            return
        try:
            a,b=int(self.table_wait.get()),int(self.dropoff_wait.get())
            if not 10<=a<=120 or not 5<=b<=60: raise ValueError()
        except ValueError:
            self.settings.set("대기시간: 10~120 / 5~60 정수")
            return
        self.request_id=uuid.uuid4().hex
        self.state="REQUEST_PENDING"
        self.status.set("REQUEST_PENDING")
        self.refresh()
        self.send("request",dict(schema_version=2,profile=PROFILE,request_id=self.request_id,
                  table_id="T03",table_wait_s=a,dropoff_wait_s=b,ai_enabled=bool(self.ai.get())))
        print("D_PRODUCT_UI_CLICK request_id="+self.request_id,flush=True)
    def on_status(self,d):
        if d.get("profile")!=PROFILE or d.get("schema_version")!=2:
            return
        if self.state=="IDLE" and not self.request_id and d.get("state")=="IDLE" and d.get("stack_id"):
            self.ready=True
            self.stack_id=d["stack_id"]
            self.status.set("IDLE / READY")
            self.refresh()
            return
        if d.get("request_id")!=self.request_id or not self.request_id:
            return
        self.state=d["state"]
        self.stack_id=d.get("stack_id")
        self.capture_id=d.get("capture_id")
        self.approval_allowed=d.get("action_allowed") is True
        self.status.set(self.state+" · "+str(d.get("remaining_s") if d.get("remaining_s") is not None else "—"))
        self.details.set("stack="+str(self.stack_id)+" / capture="+str(self.capture_id)+"\n"
                         +"AI="+str(d.get("ai_status"))+" confidence="+str(d.get("confidence"))+"\n"
                         +"raw="+str(d.get("raw_status"))+" "+str(d.get("raw_confidence"))+" / thresholds="+str(d.get("thresholds"))+"\n"
                         +"reason="+str(d.get("reason","")))
        print("D_PRODUCT_UI_APPLIED request_id="+self.request_id+" state="+self.state,flush=True)
        self.refresh()
        self.render_preview()
    def on_capture(self,d):
        if (d.get("profile")==PROFILE and d.get("schema_version")==2
                and d.get("request_id")==self.request_id and d.get("stack_id")==self.stack_id):
            self.capture_ack=dict(d)
            self.render_preview()
    def render_preview(self):
        if not self.capture_ack or self.capture_ack.get("capture_id")!=self.capture_id:
            return
        data=self.frame_cache.selected(self.capture_ack)
        if data is None:
            return
        ppm=b"P6\n640 480\n255\n"+data
        photo=self.tk.PhotoImage(data=base64.b64encode(ppm).decode("ascii"),format="PPM")
        self.photo=photo.subsample(2,2)
        self.preview.configure(image=self.photo)
        self.preview_text.set("capture="+str(self.capture_id)+"\nRGB SHA="+self.capture_ack["rgb_sha256"])
    def staff(self,action):
        if action=="APPROVE_CONTINUE" and not (self.state=="NEEDS_CONFIRMATION" and getattr(self,"approval_allowed",False)):
            return
        if not self.capture_id or not self.request_id or self.state in {"IDLE","CANCELING","COMPLETED","SAFE_HOLD","SAFE_HOLD_UNVERIFIED","ABORTED","ERROR","CANCELED"}:
            return
        self.send("staff_confirm",dict(schema_version=2,profile=PROFILE,request_id=self.request_id,
                  capture_id=self.capture_id,stack_id=self.stack_id,action=action))
        self.approval_allowed=False
        self.refresh()
        print("D_PRODUCT_UI_STAFF_CLICK request_id="+self.request_id+" action="+action,flush=True)

def main(argv=None):
    import argparse
    from pathlib import Path
    import tkinter as tk
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.parameter_client import AsyncParameterClient
    from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
    from std_msgs.msg import String
    from sensor_msgs.msg import Image
    from ament_index_python.packages import get_package_share_directory
    p=argparse.ArgumentParser()
    p.add_argument("--owner-gazebo-integration",action="store_true")
    p.add_argument("--layout")
    args,ros_args=p.parse_known_args(argv)
    rclpy.init(args=ros_args)
    node=Node("smartdish_ui")
    qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.VOLATILE)
    pubs={k:node.create_publisher(String,"/collection/"+k,qos) for k in ("request","staff_confirm")}
    c=AsyncParameterClient(node,"/smartdish_stability_inference")
    root=tk.Tk()
    pending=[]
    def send(topic,body):
        m=String()
        m.data=json.dumps(body,allow_nan=False)
        pubs[topic].publish(m)
    def thresholds(values,done):
        if not c.wait_for_services(timeout_sec=0.0):
            done(False,None)
            return
        names=["stable_confidence_min","unstable_confidence_min"]
        f=c.set_parameters_atomically([Parameter(k,value=float(v)) for k,v in zip(names,values)])
        pending.append([f,time.monotonic()+5,"set",done,names])
    view=RecoveryView(root,read_layout(args.layout or Path(get_package_share_directory("smartdish_service"))/"config/ui_layout.yaml"),
                      send,thresholds,product_ai_on_authorized(args.owner_gazebo_integration,owner_gazebo_integration=True))
    def decode(fn):
        def cb(m):
            try:
                d=json.loads(m.data)
                if isinstance(d,dict): fn(d)
            except (ValueError,TypeError,KeyError,tk.TclError): pass
        return cb
    node.create_subscription(String,"/collection/status",decode(view.on_status),qos)
    node.create_subscription(String,"/collection/capture_result",decode(view.on_capture),qos)
    def frame(msg):
        if view.frame_cache.add(msg): view.render_preview()
    node.create_subscription(Image,"/smartdish/tray/image_raw",frame,qos)
    def poll():
        rclpy.spin_once(node,timeout_sec=0)
        for item in pending[:]:
            f,deadline,stage,done,names=item
            if time.monotonic()>=deadline:
                pending.remove(item)
                done(False,None)
            elif f.done():
                pending.remove(item)
                try:
                    result=f.result()
                    if stage=="set" and result.result.successful:
                        pending.append([c.get_parameters(names),deadline,"get",done,names])
                    elif stage=="get" and len(result.values)==2 and all(v.type==3 for v in result.values):
                        done(True,RecoveryFSM.validate_thresholds(tuple(v.double_value for v in result.values)))
                    else: done(False,None)
                except Exception: done(False,None)
        root.after(50,poll)
    root.after(50,poll)
    try: root.mainloop()
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__=="__main__": main()
