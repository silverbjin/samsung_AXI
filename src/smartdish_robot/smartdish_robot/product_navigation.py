"""Private A product navigation boundary; no new public topic or cmd_vel.

Use actual rclpy action handle UUID and status, never a generated success.
E must bind the accepted callback to D's bind_accepted_goal and approve
the full product launch before activation. Legacy adapter is untouched.
"""
from dataclasses import dataclass
import time
from .product_contract import PROFILE, ContractError, valid_id, require

LEGS={"TO_TABLE":"T03","TO_RETURN":"DISH_RETURN","TO_HOME":"HOME"}
TERMINAL={4:"SUCCEEDED",5:"CANCELED",6:"ABORTED"}

def validate_goal(d):
    require(type(d) is dict and type(d.get("schema_version")) is int
            and d["schema_version"]==2 and d.get("profile")==PROFILE,
            "NAV_PROFILE")
    require(valid_id(d.get("request_id")) and d.get("leg") in LEGS
            and d.get("destination_id")==LEGS[d["leg"]],"NAV_CORRELATION")
    return {k:d[k] for k in ("schema_version","profile","request_id","leg","destination_id")}

def actual_uuid(handle):
    raw=bytes(handle.goal_id.uuid)
    require(len(raw)==16 and any(raw),"NAV_ACTUAL_UUID_INVALID")
    return raw.hex()

@dataclass
class Active:
    request:dict
    send_future:object
    deadline:float
    handle:object=None
    uuid:str=None
    result_future:object=None
    cancel_future:object=None
    cancel_requested:bool=False
    cancel_deadline:float=None
    terminal:str=None
    terminal_at:float=None
    stop_deadline:float=None

class NavigationBoundary:
    """One in-flight action; timer driven; lockout on uncertain motion.

    A timeout while awaiting acceptance retains the future. A late accepted
    handle is canceled exactly; it never becomes a new mission. There is no
    global cancel and no synthetic UUID. Caller must keep spinning until
    quiescent or explicitly record SAFE_HOLD_UNVERIFIED on process exit.
    """
    def __init__(self,client,build_goal,stop_monitor,accepted,result,cancel_result,
                 clock=time.monotonic,timeout=120.,stop_timeout=3.,cancel_timeout=10.,
                 preflight=lambda:False):
        self.client=client;self.build_goal=build_goal;self.stop=stop_monitor
        self.accepted=accepted;self.result=result;self.cancel_result=cancel_result
        self.clock=clock;self.timeout=timeout;self.stop_timeout=stop_timeout
        self.cancel_timeout=cancel_timeout;self.preflight=preflight
        self.active=None;self.locked=False;self.last_receipt=None
        self.used=set();self.used_uuids=set()

    def start(self,request):
        d=validate_goal(request);key=(d["request_id"],d["leg"])
        require(not self.locked and self.active is None and key not in self.used,
                "NAV_BUSY_OR_LOCKED")
        require(self.preflight() is True and self.client.server_is_ready(),"NAV_NOT_READY")
        self.used.add(key);self.last_receipt=None
        try:
            future=self.client.send_goal_async(self.build_goal(d["destination_id"]))
        except Exception:
            self.locked=True;raise
        self.active=Active(d,future,self.clock()+self.timeout)

    def cancel(self,request):
        a=self.active
        require(a is not None and request.get("schema_version")==2 and
                request.get("profile")==PROFILE and
                request.get("request_id")==a.request["request_id"] and
                request.get("leg")==a.request["leg"] and a.uuid is not None
                and request.get("goal_uuid")==a.uuid,"NAV_CANCEL_ID_MISMATCH")
        self._request_cancel(a)

    def abort_pending(self):
        if self.active:self._request_cancel(self.active)
        else:self.locked=True

    def _request_cancel(self,a):
        self.locked=True
        if not a.cancel_requested:
            a.cancel_requested=True;a.cancel_deadline=self.clock()+self.cancel_timeout
        if a.handle is not None and a.cancel_future is None and a.terminal is None:
            a.cancel_future=a.handle.cancel_goal_async()

    def _base(self,a):
        return {k:a.request[k] for k in ("schema_version","profile","request_id","leg")} | {"goal_uuid":a.uuid}

    def tick(self):
        a=self.active
        if a is None:return
        now=self.clock()
        try:
            if now>=a.deadline and not a.terminal:self._request_cancel(a)
            if a.handle is None:
                if not a.send_future.done():return
                handle=a.send_future.result()
                if not handle.accepted:
                    self.locked=True;self.active=None
                    # No accepted goal means no valid UUID/terminal to publish.
                    return
                a.handle=handle;a.uuid=actual_uuid(handle)
                require(a.uuid not in self.used_uuids,"NAV_UUID_REUSED")
                self.used_uuids.add(a.uuid)
                a.result_future=handle.get_result_async()
                if a.cancel_requested:
                    self._request_cancel(a)
                elif self.accepted(a.request["request_id"],a.request["leg"],a.uuid) is not True:
                    self._request_cancel(a)
            if a.cancel_future is not None and a.cancel_future.done():
                response=a.cancel_future.result()
                # A terminal race can return an empty cancellation set; only
                # exact terminal status and post-terminal stop can acknowledge.
                for goal in response.goals_canceling:
                    require(bytes(goal.goal_id.uuid).hex()==a.uuid,"NAV_CANCEL_WRONG_UUID")
            if a.terminal is None and a.result_future.done():
                status=a.result_future.result().status
                require(status in TERMINAL,"NAV_NONTERMINAL_RESULT")
                a.terminal=TERMINAL[status];a.terminal_at=now
                a.stop_deadline=now+self.stop_timeout
            if a.terminal is not None:
                # Stop monitor start must be after terminal; pre-goal dwell
                # never qualifies. If still stationary at terminal, count the
                # interval after terminal rather than resetting odom identity.
                start=self.stop.start
                last=self.stop.last_at
                stopped=(start is not None and last is not None and
                         last-max(start,a.terminal_at)+1e-9>=self.stop.dwell and
                         self.stop.verified(now))
                if stopped:
                    data=self._base(a)|{"terminal_status":a.terminal,"stop_verified":True}
                    if a.cancel_requested:
                        self.cancel_result(data|{"status":"ACK","reason":""})
                    else:
                        success=a.terminal=="SUCCEEDED"
                        self.result(data|{"result":"SUCCEEDED" if success else "FAILED",
                                          "reason":"" if success else "NAV_FAILED"})
                        if success:self.last_receipt=data|{"destination_id":a.request["destination_id"]}
                        else:self.locked=True
                    self.active=None
                elif now>=a.stop_deadline:
                    self.locked=True
                    data=self._base(a)|{"terminal_status":a.terminal,"stop_verified":False,
                                        "reason":"ROBOT_NOT_STOPPED"}
                    if a.cancel_requested:self.cancel_result(data|{"status":"FAILED"})
                    else:self.result(data|{"result":"FAILED"})
                    self.active=None
            elif a.cancel_requested and now>=a.cancel_deadline:
                # Keep polling the exact handle; late terminal cannot unlock.
                self.locked=True
        except Exception:
            self.locked=True
            if a.handle is not None and a.terminal is None:
                try:self._request_cancel(a)
                except Exception:pass
            raise

def make_nav_client(node,poses,stop_monitor,accepted,result,cancel_result,preflight):
    from rclpy.action import ActionClient
    from nav2_msgs.action import NavigateToPose
    from .contract import resolve_pose
    from geometry_msgs.msg import PoseStamped
    import math
    client=ActionClient(node,NavigateToPose,"/navigate_to_pose")
    def build(destination):
        target=resolve_pose(poses,destination)
        p=PoseStamped();p.header.frame_id="map";p.header.stamp=node.get_clock().now().to_msg()
        p.pose.position.x=target.x;p.pose.position.y=target.y
        p.pose.orientation.z=math.sin(target.yaw/2);p.pose.orientation.w=math.cos(target.yaw/2)
        g=NavigateToPose.Goal();g.pose=p
        return g
    return NavigationBoundary(client,build,stop_monitor,accepted,result,cancel_result,
                              preflight=preflight)
