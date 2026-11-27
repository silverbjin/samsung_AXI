"""Bounded pre-send gate. No ROS, no goal retry, no invented UUID.
Only one correlated request can wait for existing readiness conditions.
"""
import math

class DeferredGoal:
    def __init__(self,seconds):
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<=seconds<=5.:
            raise ValueError("GOAL_READY_BUDGET")
        self.seconds=seconds;self.request=None;self.deadline=None

    def submit(self,request,now):
        if not self.seconds:raise ValueError("GOAL_DEFER_DISABLED")
        if self.request is not None:
            if self.request==request:return False
            raise ValueError("GOAL_PENDING_CONFLICT")
        self.request=dict(request);self.deadline=now+self.seconds
        return True

    def clear(self):
        self.request=None;self.deadline=None

    def poll(self,now,*,allowed,ready):
        if self.request is None:return "EMPTY"
        if not allowed():self.clear();return "CLOSED"
        if now>=self.deadline:self.clear();return "EXPIRED"
        if not ready():return "WAIT"
        self.clear()
        return "SEND"
