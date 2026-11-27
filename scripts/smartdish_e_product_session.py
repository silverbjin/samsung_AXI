"""E actual single restaurant CI session; A startup/physics, C actual node with explicit
CI-only predictor double, D real FSM/Tk UI. No real checkpoint in CI; not Owner runner.
"""
import argparse,faulthandler,hashlib,json,math,os,subprocess,sys,threading,time
from collections import OrderedDict
from pathlib import Path
from smartdish_a04_clearance import save,sha,require
from smartdish_a04_motion import gate_paths,Witness
from smartdish_a04_no_goal import run,endpoints
from smartdish_e_product_boundary import OwnerMailbox,accepted_hook,verify_ready
from smartdish_e_product_odom import RawOdomTrace,audit,ns

MODEL="CI_DOUBLE_PRODUCT_E"
# A04 actual qualified configuration; wall-time budget, not a relaxed physical gate.
NAV_WALL_TIMEOUT_S=240
GOAL_READY_WAIT_S=5.
def require_ci():
    require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("CI")=="true" and
            os.environ.get("GZ_PARTITION","").startswith("smartdish_a04_e_") and not os.environ.get("WSL_DISTRO_NAME"),"E_CI_ONLY")

class ThreadNode:
    """Separate D/C/capture owning executors; no concurrent spin of A node."""
    def __init__(self,node,mailbox=None):
        from rclpy.executors import SingleThreadedExecutor
        self.node=node;self.mailbox=mailbox;self.executor=SingleThreadedExecutor();self.executor.add_node(node)
        self.end=threading.Event();self.error=None
        self.thread=threading.Thread(target=self.work,daemon=True)
        self.started=False
    def start(self):
        require(not self.started,"E_EXECUTOR_STARTED_TWICE")
        self.thread.start();self.started=True
    def work(self):
        try:
            while not self.end.is_set():
                if self.mailbox:self.mailbox.drain()
                self.executor.spin_once(timeout_sec=.02)
        except BaseException as exc:self.error=repr(exc)
    def close(self):
        self.end.set()
        if self.started:self.thread.join(5)
        require(not self.thread.is_alive(),"E_EXECUTOR_NOT_JOINED")
        self.executor.remove_node(self.node);self.executor.shutdown(timeout_sec=2);self.node.destroy_node()

def make_ci_c(out):
    require_ci()
    from rclpy.parameter import Parameter
    from smartdish_ai.product_stability_inference_node import ProductStabilityInferenceNode
    class ObservedC(ProductStabilityInferenceNode):
        def __init__(self):
            self.raw=OrderedDict()
            def load(path,**kwargs):
                require(str(path)=="/CI_DOUBLE_NOT_A_CHECKPOINT","CI_DOUBLE_PATH")
                return self.predict,MODEL
            super().__init__(parameter_overrides=[Parameter("owner_gazebo_integration",value=True),
                 Parameter("model_path",value="/CI_DOUBLE_NOT_A_CHECKPOINT")],predictor_loader=load)
        def _image(self,msg):
            stamp=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
            if stamp not in self.raw:
                self.raw[stamp]=(bytes(msg.data),dict(image_stamp_ns=stamp,frame_id=msg.header.frame_id,
                    width=msg.width,height=msg.height,encoding=msg.encoding,step=msg.step,is_bigendian=msg.is_bigendian))
                while len(self.raw)>16:self.raw.popitem(last=False)
            super()._image(msg)
        def predict(self,rgb,w,h):
            req=self.core.pending["request"];raw,meta=self.raw[req["image_stamp_ns"]]
            require(w==640 and h==480 and hashlib.sha256(rgb).hexdigest()==req["rgb_sha256"],"C_PREDICTOR_RGB_MISMATCH")
            (out/"c_input.rgb").open("xb").write(rgb)
            (out/"c_input_ros_bytes.bin").open("xb").write(raw)
            save(out/"c_predictor_receipt.json",dict(scope="CI_DOUBLE_NOT_ACTUAL_MODEL",model_version=MODEL,
                private_model_loaded=False,invocation_count=1,request=req,raw_metadata=meta,
                rgb_sha256=sha(out/"c_input.rgb"),raw_sha256=sha(out/"c_input_ros_bytes.bin"),steady_s=time.monotonic()))
            return "STABLE",.75
    return ObservedC()

def review_waits(trace_root,d_events,request_id):
    """Independent received callback continuous wait between actual D state and request."""
    data=[json.loads(x) for x in (trace_root/"odom_full.jsonl").open()]
    out=[]
    for state,op,seconds in (("WAIT_LOADING","LOAD",10),("WAIT_UNLOADING","UNLOAD",5)):
        starts=[r for r in d_events if r["topic"]=="/collection/status" and r["body"].get("state")==state and r["body"].get("request_id")==request_id]
        ends=[r for r in d_events if r["topic"]=="/collection/dish_transfer_request" and r["body"].get("operation")==op and r["body"].get("request_id")==request_id]
        require(starts and len(ends)==1,"WAIT_EVENT_COUNT_"+op)
        a,b=starts[0]["steady_ns"],ends[0]["steady_ns"]
        require(b-a>=seconds*10**9 and all(a<=r["steady_ns"]<=b for r in starts),"WAIT_TOO_SHORT_"+op)
        states=[r["body"]["state"] for r in d_events if r["topic"]=="/collection/status" and r["body"].get("request_id")==request_id and a<=r["steady_ns"]<=b]
        require(states[-1]==("LOADING" if op=="LOAD" else "UNLOADING") and set(states[:-1])=={state},"WAIT_STATE_ORDER_"+op)
        rows=[r for r in data if not r["duplicate"] and a-300_000_000<=r["steady_ns"]<=b]
        require(rows and rows[0]["steady_ns"]<=a and b-rows[-1]["steady_ns"]<=300_000_000 and
                all(0<y["steady_ns"]-x["steady_ns"]<=300_000_000 for x,y in zip(rows,rows[1:])) and
                all(math.hypot(*r["linear"])<=.01 and math.hypot(*r["angular"])<=.02 for r in rows),"WAIT_RAW_STOP_"+op)
        out.append(dict(operation=op,wait_s=(b-a)/1e9,request=ends[0]["body"],steady_ns=b,samples=len(rows)))
    return out

def session(node,out,phys,g,sources,buffer,state,clock,e,scene,static,target,spin,wait):
    require_ci();gate_paths(e)
    # Only the validated A candidate map (original remains untouched) may be used.
    require(e["map_sha256"]=="b73920d77e7e40577958b672dbf6a6fcc5e3bb1bcaeb4b018663bc5d101ef87a" and
            e["localization_map_sha256"]=="f796cd4571f032c493c750b8ccff1f13ddb480210b8cfec963ef5c50c041e15b","E_A_MAP_PIN_DRIFT")
    from smartdish_robot.product_runtime import ProductRuntime
    from smartdish_robot.product_capture_node import TrayCaptureNode
    from smartdish_service.product_recovery_transport import make_recovery_node
    from smartdish_service.product_admission import product_ai_on_authorized
    from rclpy.parameter import Parameter
    from lifecycle_msgs.srv import GetState
    from std_srvs.srv import Empty
    from rclpy.clock import Clock,ClockType
    from std_msgs.msg import String
    from rclpy.qos import QoSProfile,ReliabilityPolicy
    require(not product_ai_on_authorized(True),"GENERAL_PRODUCT_DENY_DRIFT")
    trace=RawOdomTrace(out/"raw_stop",e["source_sha"],e["run_id"])
    phys.odom_witness=trace.odom
    # Conservative +0.3s margin so independent first postterminal sample spans >=1s.
    phys.stop.dwell=1.3
    m=e["moving"]={"legs":[],"accepted":[],"transfers":[],"nav_quiescent":False,"scope":"ACTUAL_E_CI_DOUBLE"}
    d_events=[];dds=[];workers=[];mailbox=OwnerMailbox();runtime=None;witness=None;ui=None;ui_log=None
    def phase(name,initializing=True):
        row=dict(stage=name,initializing=initializing,steady_s=time.monotonic())
        with (out/"startup_phases.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
        tmp=out/"startup_phase.tmp";tmp.write_text(json.dumps(row));os.replace(tmp,out/"startup_phase.json")
        print("E_STARTUP_PHASE="+name,flush=True)
    phase("CM_CLIENTS_BEGIN")
    stacks=(out/"startup_stacks.log").open("w")
    faulthandler.dump_traceback_later(15,repeat=True,file=stacks)
    cm=node.create_client(GetState,"/collision_monitor/get_state")
    active={"at":0.,"value":False,"future":None}
    amcl_update=node.create_client(Empty,"/request_nomotion_update")
    update={"future":None,"last_request":-1.,"last_response":None,"error":None}
    diagnostic={"last":-1.}
    steady_clock=Clock(clock_type=ClockType.STEADY_TIME)
    def report_ready(now):
        if runtime is None or now-diagnostic["last"]<.5:return
        diagnostic["last"]=now
        def age(t):return None if t is None else now-t
        row=dict(steady_s=now,odom_age_s=age(runtime.odom_at),scan_age_s=age(runtime.scan_at),amcl_age_s=age(runtime.amcl_at),amcl=runtime.amcl,
            stop=phys.stop.verified(now),stop_start=phys.stop.start,stop_last_at=phys.stop.last_at,clock_samples=len(clock),clock_fault=runtime.clock_fault,
            callback_error=phys.callback_error,cm_active=cm_active(),cm_age_s=age(active["at"]),cmd_vel=endpoints(node,"/cmd_vel"),clock=endpoints(node,"/clock"),
            amcl_publishers=endpoints(node,"/amcl_pose"),nomotion_service_ready=amcl_update.service_is_ready(),nomotion_last_request=update["last_request"],nomotion_last_response=update["last_response"],nomotion_error=update["error"],
            action_ready=runtime.nav.client.server_is_ready(),witness_ready=witness is not None and witness.raw.get("waffle_pi") is not None,preflight=runtime.preflight())
        with (out/"runtime_ready.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
    def refresh_amcl():
        now=time.monotonic()
        f=update["future"]
        if f is not None and f.done():
            try:f.result();update["last_response"]=now
            except Exception as exc:update["error"]=repr(exc)
            update["future"]=None
        # Actual AMCL must produce a new pose; service response is not a pose.
        if runtime is not None and phys.stop.verified(now) and (runtime.amcl_at is None or now-runtime.amcl_at>.7) and now-update["last_request"]>=.8 and update["future"] is None and amcl_update.service_is_ready():
            update["future"]=amcl_update.call_async(Empty.Request());update["last_request"]=now
        report_ready(now)
    def check_cm():
        f=active["future"]
        if f is not None and f.done():
            active.update(at=time.monotonic(),value=f.result().current_state.id==3,future=None)
        if active["future"] is None and cm.service_is_ready():active["future"]=cm.call_async(GetState.Request())
    timer=node.create_timer(.4,check_cm,clock=steady_clock)
    refresh_timer=node.create_timer(.2,refresh_amcl,clock=steady_clock)
    def cm_active():
        return active["value"] and time.monotonic()-active["at"]<=2.
    def graph():
        return cm_active() and [p["name"] for p in endpoints(node,"/cmd_vel")]==["collision_monitor"] and [p["name"] for p in endpoints(node,"/cmd_vel_smoothed")]==["velocity_smoother"] and len(endpoints(node,"/clock"))==1
    try:
        phase("D_NODE_BEGIN")
        d=make_recovery_node(owner_ai_requested=True,nav_timeout_s=NAV_WALL_TIMEOUT_S)
        d.logic.model_version=MODEL # CI-only explicit separate identity; no product admission mutation.
        old_emit=d.logic.emit
        def emit(topic,**kw):
            old_emit(topic,**kw)
            full,body=d.logic.events[-1]
            row=dict(topic=full,body=body,steady_ns=time.monotonic_ns())
            d_events.append(row)
            with (out/"d_events.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
        d.logic.emit=emit
        phase("C_NODE_BEGIN")
        c=make_ci_c(out);require(c.core.predictor is not None and c.core.model_version==MODEL,"C_DOUBLE_NOT_READY")
        phase("A_RUNTIME_BEGIN")
        def goal_gate():
            return (graph() and time.monotonic()-state["times"].get("odom",0)<=.3 and
                    time.monotonic()-state["times"].get("scan",0)<=.8)
        def authorize(req):
            def check():
                logic=d.logic
                return (logic.request_id==req["request_id"] and logic.state==req["leg"] and
                        logic.goal_uuid is None and logic.deadline is not None and logic.clock()<logic.deadline)
            return mailbox.call(check) is True
        runtime=ProductRuntime(node,target,scene,static,out/"product_receipts",e["source_sha"],
            accepted_hook=lambda rid,leg,uid:accepted_hook(mailbox,d,rid,leg,uid),
            cm_active=cm_active,physical=phys,shared_clock=clock,
            goal_ready_wait_s=GOAL_READY_WAIT_S,goal_gate=goal_gate,goal_authorize=authorize)
        e["goal_ready_wait_s"]=GOAL_READY_WAIT_S
        runtime.nav.timeout=float(NAV_WALL_TIMEOUT_S)
        runtime.nav.wait_arrival_within_stop_deadline=True
        e["nav_wall_timeout_s"]={"A":runtime.nav.timeout,"D":d.logic.nav_timeout_s}
        require(runtime.nav.timeout==d.logic.nav_timeout_s,"E_NAV_DEADLINE_DRIFT")
        runtime.nav.evidence_hook=trace.nav
        phase("CAPTURE_NODE_BEGIN")
        cap=TrayCaptureNode(parameter_overrides=[Parameter("enabled",value=True),Parameter("evidence_dir",value=str(runtime.root.resolve()))])
        phase("WITNESS_BEGIN")
        witness=Witness(node,out,phys,g,sources,buffer,state,clock)
        phase("DDS_OBSERVER_BEGIN")
        qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)
        def recv(key,msg):
            row=dict(topic=key,body=json.loads(msg.data),steady_ns=time.monotonic_ns())
            dds.append(row)
            with (out/"collection_dds.jsonl").open("a") as f:f.write(json.dumps(row)+"\n")
        for key in ("request","status","nav_goal","nav_result","dish_transfer_request","dish_transfer_result",
                    "capture_request","capture_result","ai_check_request","stability","staff_confirm","nav_cancel_request","nav_cancel_result"):
            node.create_subscription(String,"/collection/"+key,lambda msg,k=key:recv(k,msg),qos)
        # Construct every node, subscription and executor before spinning any worker.
        phase("EXECUTOR_CONSTRUCT_BEGIN")
        for child,mb in ((d,mailbox),(c,None),(cap,None)):workers.append(ThreadNode(child,mb))
        phase("EXECUTOR_START_BEGIN")
        for worker in workers:worker.start()
        phase("INIT_COMPLETE",False)
        faulthandler.cancel_dump_traceback_later();stacks.close()
        wait(lambda:runtime.preflight() and runtime.nav.client.server_is_ready() and graph() and witness.raw.get("waffle_pi") is not None,30,"E_RUNTIME_READY")
        ready=runtime.arm_verified()
        stack=verify_ready(ready,runtime.root/"startup/ready.json",scene,e["source_sha"])
        wait(lambda:runtime.preflight() and graph(),10,"E_AFTER_READY_FRESH")
        require(mailbox.call(d.arm_verified,stack,(0.,0.)) is True,"D_ARM_FAILED")
        e["ready"]=ready;e["motion_authorized"]=True
        original_start=runtime.nav.start;original_result=runtime.nav.result
        def start(req):
            require(graph() and time.monotonic()-state["times"].get("odom",0)<=.3 and time.monotonic()-state["times"].get("scan",0)<=.8,"E_BEFORE_GOAL_SENSOR_STALE")
            ids=list(runtime.transfer.loaded_ids) if req["leg"]=="TO_RETURN" else None
            row=dict(mission="e-product",request_id=req["request_id"],leg=req["leg"],destination_id=req["destination_id"],
                loaded_entity_ids=ids,status="STARTED",start_sim_ns=clock[-1])
            # Record a moving phase only after the real ActionClient send call succeeds.
            original_start(req);e["navigate_to_pose_goals_sent"]+=1
            m["legs"].append(row);witness.begin("e-product_"+req["leg"],ids)
        def nav_event(kind,body,at,extra):
            trace.nav(kind,body,at,extra)
            if kind=="accepted":m["accepted"].append(dict(body,steady_s=at))
            if kind=="terminal":m["legs"][-1]["terminal_steady_s"]=at
            if kind=="stop_verified":
                m["legs"][-1]["post_terminal_stop_dwell_s"]=phys.stop.last_at-max(phys.stop.start,m["legs"][-1]["terminal_steady_s"])
        def result(body):
            row=m["legs"][-1];motion=runtime.motion
            row.update(body,status=body["result"],end_sim_ns=clock[-1],
                odom_displacement_m=motion["max_m"],odom_samples=runtime.odom_n-motion["odom_n"],
                scan_samples=runtime.scan_n-motion["scan_n"],
                amcl_error_m=math.dist(runtime.amcl,(target[row["destination_id"]]["x"],target[row["destination_id"]]["y"])))
            witness.end()
            # Publish exact real terminal failure to D as well; never swallow it
            # in the observation wrapper and leave D waiting for a nonexistent goal.
            original_result(body)
        runtime.nav.start=start;runtime.nav.result=result;runtime.nav.evidence_hook=nav_event
        ui_log=(out/"ui.log").open("w")
        ui=subprocess.Popen([sys.executable,"-u",str(Path(__file__).with_name("smartdish_e_product_ui_ci.py")),str(out)],stdout=ui_log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+650
        while time.monotonic()<deadline:
            require(all(w.error is None for w in workers),"E_CHILD_EXECUTOR_ERROR:"+str([w.error for w in workers]))
            runtime.step()
            if witness.active:
                require(graph() and time.monotonic()-state["times"].get("scan",0)<=.8 and time.monotonic()-state["times"].get("odom",0)<=.3,"E_MOVING_SENSOR_OR_GRAPH")
                witness.sample()
            if ui.poll() is not None:
                require(ui.returncode==0,"E_UI_EXIT:"+str(ui.returncode));break
        else:raise RuntimeError("E_PRODUCT_SESSION_TIMEOUT")
        require(len(m["legs"])==3 and all(x["status"]=="SUCCEEDED" for x in m["legs"]) and runtime.nav.active is None and phys.stop.verified(time.monotonic()) and graph(),"E_FINAL_NAV_STOP_OR_GRAPH")
        # Drain all actual topic callbacks before closing evidence.
        for _ in range(30):runtime.step()
        m["nav_quiescent"]=runtime.nav.active is None and phys.stop.verified(time.monotonic()) and graph()
        require(m["nav_quiescent"],"E_FINAL_QUIESCENCE")
        events=lambda topic:[r for r in dds if r["topic"]==topic]
        transfers=events("dish_transfer_result")
        require(len(transfers)==2 and all(x["body"]["status"]=="ACK" for x in transfers),"E_TRANSFER_ACK_COUNT")
        load,unload=[x["body"] for x in transfers]
        require(load["entity_ids"]==unload["entity_ids"] and len(load["entity_ids"])==3 and unload["tray_count"]==0,"E_TRANSFER_IDS")
        m["transfers"]=[x["body"] for x in transfers]
        capture=events("capture_result");ai=events("stability");staff=events("staff_confirm")
        require(len(capture)==len(ai)==len(staff)==1 and capture[0]["body"]["status"]=="ACK" and ai[0]["body"]["inference_ok"] is True and staff[0]["body"]["action"]=="APPROVE_CONTINUE","E_CAPTURE_AI_STAFF")
        capbody=capture[0]["body"];aibody=ai[0]["body"];sb=staff[0]["body"]
        require(capbody["image_stamp_ns"]>load["event_sim_ns"] and all(capbody[k]==aibody[k] for k in ("capture_id","request_id","transfer_id","stack_id","image_stamp_ns","rgb_sha256")) and sb["capture_id"]==capbody["capture_id"] and sha(out/"c_input.rgb")==capbody["rgb_sha256"],"E_AI_INPUT_CAUSALITY")
        returns=[r for r in d_events if r["topic"]=="/collection/nav_goal" and r["body"]["leg"]=="TO_RETURN"]
        require(len(returns)==1 and len([r for r in d_events if r["topic"]=="/collection/nav_goal"])==3,"E_GOAL_COUNT")
        # UI send records exact monotonic timestamp before publishing. DDS receipt order alone isn't authoritative.
        ui_events=json.loads((out/"ui_events.json").read_text())
        approvals=[x for x in ui_events if x["event"]=="staff_confirm" and x["body"]["action"]=="APPROVE_CONTINUE"]
        require(len(approvals)==1 and ns(approvals[0]["steady_s"])<returns[0]["steady_ns"],"E_GOAL_BEFORE_APPROVAL")
        capture_dir=runtime.root/"captures"/hashlib.sha256(capbody["capture_id"].encode()).hexdigest()
        require(sha(capture_dir/"frame.rgb")==capbody["rgb_sha256"] and sha(capture_dir/"receipt.json")==capbody["receipt_sha256"],"E_CAPTURE_RECEIPT")
        from smartdish_robot.product_contract import canonical_rgb
        c_receipt=json.loads((out/"c_predictor_receipt.json").read_text())
        meta=c_receipt["raw_metadata"]
        require(canonical_rgb(meta["width"],meta["height"],meta["encoding"],meta["step"],(out/"c_input_ros_bytes.bin").read_bytes())==(out/"c_input.rgb").read_bytes(),"E_C_RAW_STRIDE")
        phys.odom_witness=None;trace.close();trace=None
        m["raw_stop_review"]=audit(out/"raw_stop",e["source_sha"],e["run_id"])
        m["wait_review"]=review_waits(out/"raw_stop",d_events,load["request_id"])
        # Actual D emission to A publication is bounded by the contract, not only backend elapsed time.
        for w,ack in zip(m["wait_review"],transfers):
            # DDS observer receive can lag; use actual A publish event for deadline.
            arows=[json.loads(x) for x in (runtime.root/"a_runtime_events.jsonl").open()]
            published=[x for x in arows if x["event"]=="dish_transfer_result" and x["body"]["transfer_id"]==w["request"]["transfer_id"]]
            require(len(published)==1 and 0<=ns(published[0]["steady_s"])-w["steady_ns"]<20_000_000_000,"E_TRANSFER_DEADLINE")
        e["model_scope"]="CI_DOUBLE_NOT_ACTUAL_MODEL";e["private_model_loaded"]=False
        save(out/"moving_progress.json",m)
    except BaseException:
        if runtime:
            runtime.deferred_goal.clear();runtime.transfer.locked=True
        if runtime and runtime.nav.active is not None:
            runtime.nav.abort_pending();deadline=time.monotonic()+15
            while runtime.nav.active is not None and time.monotonic()<deadline:
                try:runtime.step()
                except Exception:break
            m["cancel_drained"]=runtime.nav.active is None
        if runtime and runtime.nav.active is None:
            try:
                until=time.monotonic()+5
                while time.monotonic()<until and not phys.stop.verified(time.monotonic()):runtime.step()
                m["nav_quiescent"]=phys.stop.verified(time.monotonic())
            except Exception:pass
        raise
    finally:
        faulthandler.cancel_dump_traceback_later()
        if not stacks.closed:stacks.close()
        if ui and ui.poll() is None:
            ui.terminate()
            try:ui.wait(timeout=5)
            except subprocess.TimeoutExpired:ui.kill();ui.wait()
        if ui_log:ui_log.close()
        for worker in reversed(workers):worker.close()
        mailbox.close()
        if witness:m["witness"]=witness.close()
        phys.odom_witness=None
        if trace:trace.close()
        node.destroy_timer(refresh_timer)
        node.destroy_timer(timer)
        save(out/"moving_progress.json",m)

def main():
    require_ci()
    p=argparse.ArgumentParser()
    for k in ("out","robot-source","bridge-source","world-source","map","poses","params","observer-plugin"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.mode="candidate";a.motion=True;a.mission="product"
    run(a,product_session=session)
if __name__=="__main__":main()
