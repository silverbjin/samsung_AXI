"""Owner recovery contract v1.1. Pure FSM; external READY/UUID adapters pending E.
No synthetic physical results, /cmd_vel, product admission or ROS side effects.
"""
import math
import re
import time
import uuid

PROFILE = "OWNER_PRODUCT_RECOVERY"
LEGS = {"TO_TABLE":"T03", "TO_RETURN":"DISH_RETURN", "TO_HOME":"HOME"}
DEADLINES = {"LOADING":5, "UNLOADING":5, "CAPTURING":5, "AI_CHECK":5,
             "NEEDS_CONFIRMATION":60, "CANCELING":5}
TERMINAL = {"COMPLETED","SAFE_HOLD","SAFE_HOLD_UNVERIFIED","ABORTED"}
SHA = re.compile(r"[a-f0-9]{64}")
def identifier(x):
    return isinstance(x,str) and 0<len(x)<=128 and x.strip()==x
def digest(x):
    return isinstance(x,str) and SHA.fullmatch(x) is not None
def integer(x):
    return type(x) is int and x>=0
def probability(x):
    return type(x) in (float,int) and math.isfinite(x) and 0<=x<=1
def goal_id(x):
    return isinstance(x,str) and re.fullmatch(r"[a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",x) is not None

class RecoveryFSM:
    def __init__(self, *, clock=time.monotonic, model_version=None):
        self.clock=clock
        self.model_version=model_version
        self.state="IDLE"
        self.request_id=""
        self.stack_id=None
        self.capture_id=None
        self.transfer_id=None
        self.goal_uuid=None
        self.leg=None
        self.deadline=None
        self.reason=""
        self.thresholds=None
        self.capture=None
        self.ai=None
        self.entities=None
        self.load_stamp=None
        self.ai_enabled=False
        self.ready=False
        self.used=set()
        self.used_goals=set()
        self.events=[]
        self.wait=(10,5)

    @staticmethod
    def validate_thresholds(pair):
        if not isinstance(pair,(tuple,list)) or len(pair)!=2 or not all(probability(x) for x in pair):
            raise ValueError("INVALID_THRESHOLDS")
        return tuple(float(x) for x in pair)

    def arm(self, stack_id, thresholds):
        """Integration boundary ONLY: caller must verify actual A READY and C get ACK.
        Not a ROS event; cannot clear unknown-motion or failed-transfer lockout.
        """
        if self.state!="IDLE" or not identifier(stack_id):
            return False
        self.thresholds=self.validate_thresholds(thresholds)
        self.stack_id=stack_id
        self.ready=True
        self.status()
        return True

    def drain(self):
        result=self.events[:]
        self.events.clear()
        return result

    def emit(self, topic, **kw):
        self.events.append(("/collection/"+topic,dict(schema_version=2,profile=PROFILE,
                          request_id=self.request_id,**kw)))

    def status(self):
        data=self.ai or {}
        self.emit("status",state=self.state,table_id="T03",stack_id=self.stack_id,
                  capture_id=self.capture_id,remaining_s=None if self.deadline is None else
                  max(0,math.ceil(self.deadline-self.clock())),reason=self.reason,
                  action_allowed=self.state=="NEEDS_CONFIRMATION",
                  ai_status=data.get("status"),confidence=data.get("confidence"),
                  thresholds=self.thresholds, raw_status=data.get("raw_status"),
                  raw_confidence=data.get("raw_confidence"))
    def enter(self,state,seconds=None,reason=""):
        self.state=state
        self.reason=reason
        self.deadline=None if seconds is None else self.clock()+seconds
        self.status()

    def matches(self,d):
        return (isinstance(d,dict) and type(d.get("schema_version")) is int
                and d["schema_version"]==2 and d.get("profile")==PROFILE
                and d.get("request_id")==self.request_id)

    def stack_matches(self,d):
        return self.matches(d) and d.get("stack_id")==self.stack_id

    def handle_request(self,d):
        if self.state!="IDLE" or not self.ready or not isinstance(d,dict):
            return False
        rid=d.get("request_id")
        if (not identifier(rid) or rid in self.used or d.get("profile")!=PROFILE
                or type(d.get("schema_version")) is not int or d["schema_version"]!=2
                or d.get("table_id")!="T03" or type(d.get("ai_enabled")) is not bool
                or type(d.get("table_wait_s")) is not int or not 10<=d["table_wait_s"]<=120
                or type(d.get("dropoff_wait_s")) is not int or not 5<=d["dropoff_wait_s"]<=60
                or (d["ai_enabled"] and not self.model_version)):
            return False
        self.used.add(rid)
        self.request_id=rid
        self.ai_enabled=d["ai_enabled"]
        self.wait=(d["table_wait_s"],d["dropoff_wait_s"])
        self.ready=False
        self.begin_leg("TO_TABLE")
        return True

    def begin_leg(self,leg):
        self.leg=leg
        self.goal_uuid=None
        self.enter(leg,120)
        self.emit("nav_goal",leg=leg,destination_id=LEGS[leg])

    def fail(self,reason):
        if self.state in LEGS:
            if not goal_id(self.goal_uuid):
                self.enter("SAFE_HOLD_UNVERIFIED",reason=reason+"_UUID_UNKNOWN")
            else:
                self.enter("CANCELING",DEADLINES["CANCELING"],reason)
                self.emit("nav_cancel_request",leg=self.leg,goal_uuid=self.goal_uuid,reason=reason)
        elif self.state=="CANCELING":
            self.enter("SAFE_HOLD_UNVERIFIED",reason=reason)
        elif self.state not in TERMINAL:
            self.enter("SAFE_HOLD",reason=reason)

    def expired(self):
        if self.deadline is not None and self.clock()>=self.deadline:
            if self.state in {"WAIT_LOADING","WAIT_UNLOADING"}:
                self.tick()
            else:
                reason={"AI_CHECK":"AI_TIMEOUT","NEEDS_CONFIRMATION":"STAFF_CONFIRM_TIMEOUT",
                        "CAPTURING":"CAMERA_TIMEOUT","CANCELING":"CANCEL_TIMEOUT",
                        "LOADING":"LOAD_FAILED","UNLOADING":"UNLOAD_FAILED"}.get(self.state,"NAV_TIMEOUT")
                self.fail(reason)
            return True
        return False

    def bind_goal_uuid(self,leg,value):
        """A actual accepted Goal adapter boundary; transport awaits E agreement."""
        if self.expired() or self.state not in LEGS or self.leg!=leg or not goal_id(value):
            return False
        if self.goal_uuid is not None:
            return self.goal_uuid==value
        if value.replace('-','') in self.used_goals:
            return False
        self.goal_uuid=value
        return True

    def on_nav_result(self,d):
        if (self.expired() or self.state not in LEGS or not self.matches(d)
                or d.get("leg")!=self.leg or not goal_id(d.get("goal_uuid"))
                or d["goal_uuid"].replace("-","") in self.used_goals
                or (self.goal_uuid is not None and self.goal_uuid!=d["goal_uuid"])):
            return False
        if d.get("result")!="SUCCEEDED" or d.get("terminal_status")!="SUCCEEDED" or d.get("stop_verified") is not True:
            self.goal_uuid=d["goal_uuid"]
            self.fail("NAV_FAILED_OR_NOT_STOPPED")
            return False
        self.used_goals.add(d['goal_uuid'].replace('-',''))
        leg=self.leg
        self.leg=self.goal_uuid=None
        if leg=="TO_TABLE":
            self.enter("WAIT_LOADING",self.wait[0])
        elif leg=="TO_RETURN":
            self.enter("WAIT_UNLOADING",self.wait[1])
        else:
            self.enter("COMPLETED")
        return True

    def transfer(self,operation):
        self.transfer_id=uuid.uuid4().hex
        self.enter("LOADING" if operation=="LOAD" else "UNLOADING",5)
        self.emit("dish_transfer_request",stack_id=self.stack_id,transfer_id=self.transfer_id,
                  operation=operation,destination_id="T03" if operation=="LOAD" else "DISH_RETURN")

    def on_transfer(self,d):
        if (self.expired() or self.state not in {"LOADING","UNLOADING"}
                or not self.stack_matches(d) or d.get("transfer_id")!=self.transfer_id):
            return False
        load=self.state=="LOADING"
        op="LOAD" if load else "UNLOAD"
        if d.get("operation")!=op:
            return False
        entities=d.get("entity_ids")
        if (d.get("status")!="ACK" or not digest(d.get("receipt_sha256"))
                or not integer(d.get("event_sim_ns")) or not isinstance(entities,list)
                or not entities or not all(identifier(e) for e in entities) or len(set(entities))!=len(entities)
                or not integer(d.get("tray_count")) or not integer(d.get("table_count"))
                or d["table_count"]!=0 or d.get("location")!=("ON_ROBOT" if load else "RETURNED")
                or d["tray_count"]!=(len(entities) if load else 0)
                or (not load and (set(entities)!=self.entities or d["event_sim_ns"]<=self.load_stamp))):
            self.fail(op+"_FAILED")
            return False
        if not load:
            self.begin_leg("TO_HOME")
        else:
            self.entities=set(entities)
            self.load_stamp=d["event_sim_ns"]
            if self.ai_enabled:
                self.capture_id=uuid.uuid4().hex
                self.enter("CAPTURING",5)
                self.emit("capture_request",stack_id=self.stack_id,transfer_id=self.transfer_id,
                          capture_id=self.capture_id,min_sim_stamp_ns=self.load_stamp)
            else:
                self.begin_leg("TO_RETURN")
        return True

    def exact_capture(self,d):
        return self.stack_matches(d) and d.get("transfer_id")==self.transfer_id and d.get("capture_id")==self.capture_id

    def on_capture(self,d):
        if self.expired() or self.state!="CAPTURING" or not self.exact_capture(d):
            return False
        if (d.get("status")!="ACK" or not integer(d.get("image_stamp_ns"))
                or d["image_stamp_ns"]<=self.load_stamp or d.get("frame_id")!="smartdish_tray_optical"
                or not digest(d.get("rgb_sha256")) or not digest(d.get("receipt_sha256"))
                or d.get("width")!=640 or d.get("height")!=480 or d.get("encoding") not in {"rgb8","bgr8"}):
            self.fail("FRAME_INVALID")
            return False
        self.capture={k:d[k] for k in ("image_stamp_ns","frame_id","rgb_sha256")}
        self.enter("AI_CHECK",5)
        self.emit("ai_check_request",stack_id=self.stack_id,transfer_id=self.transfer_id,
                  capture_id=self.capture_id,**self.capture)
        return True

    def on_stability(self,d):
        if self.expired() or self.state!="AI_CHECK" or not self.exact_capture(d):
            return False
        if any(d.get(k)!=self.capture[k] for k in ("image_stamp_ns","rgb_sha256")):
            return False
        raw=d.get("raw_status")
        score=d.get("raw_confidence")
        try:
            pair=self.validate_thresholds((d.get("stable_confidence_min"),d.get("unstable_confidence_min")))
        except ValueError:
            self.fail("THRESHOLD_INVALID")
            return False
        if (d.get("inference_ok") is not True or d.get("model_version")!=self.model_version
                or raw not in {"STABLE","UNSTABLE"} or not probability(score) or pair!=self.thresholds):
            self.fail("INFERENCE_FAILED")
            return False
        expected=raw if score>=pair[0 if raw=="STABLE" else 1] else "UNKNOWN"
        confidence=d.get("confidence")
        if (d.get("status")!=expected or (expected!="UNKNOWN" and
                (not probability(confidence) or confidence!=score))
                or (expected=="UNKNOWN" and confidence is not None and
                    (not probability(confidence) or confidence!=score))):
            self.fail("INFERENCE_INVALID")
            return False
        self.ai=dict(d)
        self.enter("NEEDS_CONFIRMATION",60)
        return True

    def on_staff(self,d):
        if self.expired() or self.state in TERMINAL or self.state=="IDLE" or not self.stack_matches(d):
            return False
        if "capture_id" not in d or d.get("capture_id")!=self.capture_id:
            return False
        if d.get("action")=="ABORT":
            self.fail("STAFF_ABORT")
            return True
        if d.get("action")=="APPROVE_CONTINUE" and self.state=="NEEDS_CONFIRMATION":
            self.begin_leg("TO_RETURN")
            return True
        return False

    def on_cancel(self,d):
        if (self.expired() or self.state!="CANCELING" or not self.matches(d)
                or d.get("leg")!=self.leg or d.get("goal_uuid")!=self.goal_uuid):
            return False
        if (d.get("status")=="ACK" and d.get("terminal_status") in {"CANCELED","ABORTED","SUCCEEDED"}
                and d.get("stop_verified") is True):
            self.enter("ABORTED",reason=self.reason)
            return True
        self.enter("SAFE_HOLD_UNVERIFIED",reason="CANCEL_UNVERIFIED")
        return False

    def tick(self):
        if self.deadline is None:
            return
        if self.clock()>=self.deadline and self.state in {"WAIT_LOADING","WAIT_UNLOADING"}:
            self.transfer("LOAD" if self.state=="WAIT_LOADING" else "UNLOAD")
        elif not self.expired():
            self.status()
