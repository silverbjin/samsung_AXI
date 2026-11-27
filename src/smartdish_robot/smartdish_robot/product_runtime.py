"""Opt-in A product ROS runtime composition, awaiting E-approved launch.

No CLI or legacy launch changes. E must provide actual CM lifecycle checker
and D's accepted-UUID hook. Call step from one owning executor thread only;
never spin this same node concurrently. No public topic extensions.
"""
from collections import deque
import json
import math
from pathlib import Path
import time
from .product_contract import PROFILE, ContractError, require, canonical_json
from .product_navigation import make_nav_client,validate_goal
from .product_physics import PhysicalOperations
from .product_transfer import ProductTransferController
from .product_goal_gate import DeferredGoal

class ProductRuntime:
    def __init__(self,node,poses,scene,world_dir,evidence_dir,source_sha,
                 *,accepted_hook,cm_active,transfer_timeout=20.,physical=None,shared_clock=None,
                 goal_ready_wait_s=0.,goal_gate=lambda:True,goal_authorize=lambda _:True):
        from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy,qos_profile_sensor_data
        from rosgraph_msgs.msg import Clock
        from nav_msgs.msg import Odometry
        from sensor_msgs.msg import LaserScan
        from geometry_msgs.msg import PoseWithCovarianceStamped
        from std_msgs.msg import String
        self.node=node;self.poses=poses;self.cm_active=cm_active;self.String=String
        self.root=Path(evidence_dir);self.root.mkdir(parents=True,exist_ok=True)
        require((physical is None)==(shared_clock is None),"SHARED_PHYSICAL_CLOCK_PAIR")
        self.physics=physical if physical is not None else PhysicalOperations()
        self.clock=shared_clock if shared_clock is not None else deque(maxlen=4096)
        self.odom_xy=None;self.odom_n=0;self.odom_at=None;self.scan_n=0;self.scan_at=None
        self.amcl=None;self.amcl_at=None;self.motion=None;self.pending=None;self.armed=False
        self.clock_fault=False;self.current_request_id=None;self.nav_fault_logged=False
        self.closed_requests=set()
        self.goal_ready_wait_s=goal_ready_wait_s
        self.goal_gate=goal_gate;self.goal_authorize=goal_authorize
        self.deferred_goal=DeferredGoal(goal_ready_wait_s)
        if physical is None:self.physics.attach(node,self.clock)
        else:require(self.physics.node is node and self.physics.clock is self.clock,"SHARED_PHYSICAL_OWNER")
        qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.VOLATILE)
        self.pubs={key:node.create_publisher(String,"/collection/"+key,qos)
                   for key in ("nav_result","nav_cancel_result","dish_transfer_result")}
        self.subs=[

            node.create_subscription(Odometry,"/odom",self.on_odom,qos_profile_sensor_data),
            node.create_subscription(LaserScan,"/scan",self.on_scan,qos_profile_sensor_data),
            node.create_subscription(PoseWithCovarianceStamped,"/amcl_pose",self.on_amcl,qos_profile_sensor_data),
        ]
        if shared_clock is None:self.subs.append(node.create_subscription(Clock,"/clock",self.on_clock,qos))
        self.nav=make_nav_client(node,poses,self.physics.stop,accepted_hook,
                                 self.nav_result,self.cancel_result,self.preflight,self.arrival_verified)
        self.transfer=ProductTransferController(self.nav,self.physics,scene,world_dir,self.root,
                                                source_sha,timeout_s=transfer_timeout)
        for key,callback in (("nav_goal",self.on_goal),("nav_cancel_request",self.on_cancel),
                             ("dish_transfer_request",self.on_transfer),("status",self.on_status)):
            self.subs.append(node.create_subscription(String,"/collection/"+key,
                lambda m,cb=callback:self.dispatch(m,cb),qos))

    def event(self,name,body):
        row={"event":name,"steady_s":time.monotonic(),"body":body}
        with (self.root/"a_runtime_events.jsonl").open("a") as f:f.write(canonical_json(row).decode()+"\n")

    def publish(self,key,body):
        self.event(key,body)
        m=self.String();m.data=canonical_json(body).decode()
        self.pubs[key].publish(m)

    def on_clock(self,m):
        stamp=m.clock.sec*10**9+m.clock.nanosec
        if self.clock and stamp<self.clock[-1]:self.clock_fault=True
        if not self.clock or stamp>self.clock[-1]:self.clock.append(stamp)

    def on_odom(self,m):
        xy=(m.pose.pose.position.x,m.pose.pose.position.y)
        if not all(math.isfinite(v) for v in xy):return
        self.odom_xy=xy;self.odom_n+=1;self.odom_at=time.monotonic()
        if self.motion:self.motion["max_m"]=max(self.motion["max_m"],math.dist(xy,self.motion["start"]))

    def on_scan(self,m):
        if len(m.ranges)>10:self.scan_n+=1;self.scan_at=time.monotonic()

    def on_amcl(self,m):
        p=m.pose.pose.position
        if m.header.frame_id=="map" and math.isfinite(p.x) and math.isfinite(p.y):
            self.amcl=(p.x,p.y);self.amcl_at=time.monotonic()

    def preflight(self):
        now=time.monotonic()
        publishers=self.node.get_publishers_info_by_topic("/cmd_vel")
        return (not self.clock_fault and not self.physics.callback_error and len(self.clock)>=3
                and self.node.count_publishers("/clock")==1
                and len(publishers)==1 and publishers[0].node_name=="collision_monitor"
                and self.cm_active() is True and self.odom_xy is not None
                and all(x is not None and 0<=now-x<=2. for x in (self.odom_at,self.scan_at,self.amcl_at))
                and self.physics.stop.verified(now))

    def arm_verified(self):
        require(not self.armed and self.preflight() and self.nav.client.server_is_ready(),
                "PRODUCT_A_NOT_READY")
        from .contract import resolve_pose
        home=resolve_pose(self.poses,"HOME")
        require(math.dist(self.amcl,(home.x,home.y))<=.8,"START_NOT_HOME")
        require(self.node.count_publishers("/smartdish/tray/image_raw")==1 and
                self.physics.cache.select(0,time.monotonic()) is not None,"TRAY_RGB_NOT_READY")
        receipt=self.transfer.arm_verified()
        self.armed=True;self.event("READY",receipt)
        return receipt

    def arrival_verified(self,request):
        from .contract import resolve_pose
        target=resolve_pose(self.poses,request["destination_id"])
        m=self.motion
        if m is None or self.amcl is None:return False
        err=math.dist(self.amcl,(target.x,target.y))
        obs={"request_id":request["request_id"],"leg":request["leg"],"odom_max_m":m["max_m"],
             "odom_count":self.odom_n-m["odom_n"],"scan_count":self.scan_n-m["scan_n"],
             "amcl_error_m":err}
        self.event("NAV_ACTUAL_MOTION",obs)
        return (self.preflight() and obs["odom_max_m"]>.25 and obs["odom_count"]>=3
                and obs["scan_count"]>=3 and err<=.8)

    def nav_result(self,d):
        if d["result"]=="SUCCEEDED":self.transfer.note_arrival()
        self.motion=None
        self.publish("nav_result",d)

    def cancel_result(self,d):
        self.motion=None;self.transfer.locked=True
        self.publish("nav_cancel_result",d)

    def dispatch(self,m,cb):
        try:
            d=json.loads(m.data)
            if isinstance(d,dict):cb(d)
        except (ContractError,ValueError,TypeError,KeyError,RuntimeError) as exc:
            self.event("REJECTED_NO_EFFECT",{"handler":cb.__name__,"reason":str(exc)})

    def goal_allowed(self,d):
        return (d["request_id"] not in self.closed_requests and self.armed and self.pending is None and
                self.nav.active is None and self.transfer.can_start_leg(d))

    def on_goal(self,d):
        d=validate_goal(d)
        require(self.goal_allowed(d),"PRODUCT_LEG_NOT_AUTHORIZED")
        if self.goal_ready_wait_s:
            if self.deferred_goal.submit(d,time.monotonic()):
                self.event("GOAL_PENDING_READY",d)
            return
        self.start_goal(d)

    def advance_goal(self):
        d=self.deferred_goal.request
        if d is None:return
        # Never send after a failure or cancellation; D owns request state.
        try:
            result=self.deferred_goal.poll(time.monotonic(),allowed=lambda:self.goal_allowed(d),
                       ready=lambda:self.preflight() and self.nav.client.server_is_ready() and self.goal_gate())
            if result=="WAIT":return
            if result=="CLOSED":
                self.event("GOAL_PENDING_CLOSED",d);return
            if result=="EXPIRED":raise ContractError("GOAL_READY_TIMEOUT_NO_SEND")
            require(result=="SEND" and self.goal_authorize(d) is True,"GOAL_D_AUTHORIZATION_REJECTED")
            require(self.goal_allowed(d) and self.preflight() and self.nav.client.server_is_ready() and self.goal_gate(),"GOAL_READY_CHANGED_NO_SEND")
            self.start_goal(d)
            self.event("GOAL_DISPATCHED_AFTER_READY",d)
        except Exception as exc:
            self.deferred_goal.clear()
            self.closed_requests.add(d["request_id"]);self.transfer.locked=True
            self.nav.abort_pending()
            self.event("GOAL_DISPATCH_FAIL_CLOSED",d|{"reason":str(exc)})
            raise

    def start_goal(self,d):
        require(self.goal_allowed(d),"PRODUCT_LEG_NOT_AUTHORIZED")
        require(self.odom_xy is not None,"ODOM_MISSING")
        self.motion={"start":self.odom_xy,"odom_n":self.odom_n,"scan_n":self.scan_n,"max_m":0.}
        try:
            self.nav.start(d)
            self.current_request_id=d['request_id']
        except Exception:
            self.motion=None;raise

    def on_cancel(self,d):
        self.nav.cancel(d)

    def on_transfer(self,d):
        from .product_contract import parse_transfer
        req=parse_transfer(canonical_json(d))
        require(self.armed and self.nav.active is None and req['request_id']==self.current_request_id and not self.transfer.locked and not self.nav.locked,"PRODUCT_TRANSFER_LOCKED")
        if self.pending is not None or self.transfer.active:return
        self.pending=req

    def on_status(self,d):
        # D's existing status topic; no new UUID or READY public schema.
        if d.get("schema_version")!=2 or d.get("profile")!=PROFILE:return
        if d.get("state") not in ("SAFE_HOLD","SAFE_HOLD_UNVERIFIED","ERROR","ABORTED","CANCELED","CANCELING"):return
        rid=d.get("request_id")
        if not isinstance(rid,str) or not rid:return
        self.closed_requests.add(rid)
        if self.deferred_goal.request is not None and self.deferred_goal.request['request_id']==rid:
            self.event('GOAL_PENDING_CLOSED',self.deferred_goal.request)
            self.deferred_goal.clear()
        if rid==self.current_request_id:
            self.nav.abort_pending()
            self.transfer.locked=True

    def step(self):
        import rclpy
        rclpy.spin_once(self.node,timeout_sec=.05)
        if self.clock_fault or self.physics.callback_error:
            self.transfer.locked=True
            self.nav.abort_pending()
        if self.nav.active is not None:
            try:self.nav.tick()
            except Exception as exc:
                self.transfer.locked=True
                if not self.nav_fault_logged:
                    self.event('NAV_UNVERIFIED_LOCKED',{'reason':str(exc)})
                    self.nav_fault_logged=True
        self.advance_goal()
        if self.pending is not None:
            req=self.pending;self.pending=None
            try:self.publish("dish_transfer_result",self.transfer.run(req))
            except (ContractError,OSError,RuntimeError,ValueError) as exc:
                self.transfer.locked=True
                self.event("TRANSFER_UNVERIFIED_NO_ACK",{"reason":str(exc)})

def make_product_runtime(*,approved=False,poses,scene,world_dir,evidence_dir,source_sha,
                         accepted_hook,cm_active,transfer_timeout=20.):
    require(approved is True,"E_PRODUCT_LAUNCH_APPROVAL_REQUIRED")
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    node=Node("smartdish_navigation_adapter",parameter_overrides=[Parameter("use_sim_time",value=True)])
    return ProductRuntime(node,poses,scene,world_dir,evidence_dir,source_sha,
        accepted_hook=accepted_hook,cm_active=cm_active,transfer_timeout=transfer_timeout)
