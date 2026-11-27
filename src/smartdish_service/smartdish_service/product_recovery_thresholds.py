"""C atomic parameter transaction; never infer success from a set request alone."""
import time
from .product_recovery_fsm import RecoveryFSM

class ThresholdTransaction:
    NAMES=("stable_confidence_min","unstable_confidence_min")
    def __init__(self,client,clock=time.monotonic):
        self.client=client
        self.clock=clock
        self.pending=None
    def request(self,values,done):
        from rclpy.parameter import Parameter
        if self.pending is not None or not self.client.wait_for_services(timeout_sec=0.0):
            done(False,None)
            return
        try:
            values=RecoveryFSM.validate_thresholds(values)
            future=self.client.set_parameters_atomically([
                Parameter(k,value=float(v)) for k,v in zip(self.NAMES,values)])
            self.pending=(future,self.clock()+5,"set",done,values)
        except (ValueError,RuntimeError,TypeError):
            done(False,None)
    def poll(self):
        if self.pending is None:
            return
        future,deadline,stage,done,expected=self.pending
        if self.clock()>=deadline:
            self.pending=None
            done(False,None)
            return
        if not future.done():
            return
        self.pending=None
        try:
            result=future.result()
            if stage=="set" and result.result.successful:
                self.pending=(self.client.get_parameters(list(self.NAMES)),deadline,"get",done,expected)
                return
            if stage=="get" and len(result.values)==2 and all(v.type==3 for v in result.values):
                actual=RecoveryFSM.validate_thresholds(tuple(v.double_value for v in result.values))
                done(actual==expected,actual)
                return
        except (ValueError,RuntimeError,AttributeError,TypeError):
            pass
        done(False,None)
