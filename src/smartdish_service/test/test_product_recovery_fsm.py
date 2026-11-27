"""L0 only: fixtures are not real A/C, Gazebo or Nav2 evidence."""
import unittest
from smartdish_service.product_recovery_fsm import RecoveryFSM, PROFILE

class Clock:
    now = 0.0
    def __call__(self): return self.now

class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.fsm = RecoveryFSM(clock=self.clock, model_version="fixture-resnet18")
        self.fsm.arm("stack-01", (0.0, 0.0))
        self.request = dict(schema_version=2, profile=PROFILE, request_id="r1",
                            table_id="T03", table_wait_s=10, dropoff_wait_s=5, ai_enabled=True)
    def body(self, **kw):
        return dict(schema_version=2, profile=PROFILE, request_id="r1", **kw)
    def start(self, ai=True):
        self.request["ai_enabled"] = ai
        self.assertTrue(self.fsm.handle_request(self.request))
    def nav(self, leg):
        return self.fsm.on_nav_result(self.body(leg=leg, goal_uuid={"TO_TABLE":"1"*32,"TO_RETURN":"2"*32,"TO_HOME":"3"*32}[leg],
                           result="SUCCEEDED", terminal_status="SUCCEEDED", stop_verified=True))
    def load(self):
        self.start()
        self.assertTrue(self.nav("TO_TABLE"))
        self.clock.now += 10
        self.fsm.tick()
        self.assertEqual(self.fsm.state, "LOADING")
        return self.body(stack_id="stack-01", transfer_id=self.fsm.transfer_id, operation="LOAD",
                         status="ACK", reason="", entity_ids=["dish-1"], location="ON_ROBOT",
                         tray_count=1, table_count=0, receipt_sha256="a"*64, event_sim_ns=100)
    def capture(self):
        self.assertTrue(self.fsm.on_transfer(self.load()))
        self.assertEqual(self.fsm.state, "CAPTURING")
        return self.body(stack_id="stack-01", transfer_id=self.fsm.transfer_id,
                         capture_id=self.fsm.capture_id, status="ACK", reason="",
                         image_stamp_ns=101, frame_id="smartdish_tray_optical",
                         rgb_sha256="b"*64, width=640, height=480, encoding="rgb8", receipt_sha256="c"*64)
    def inference(self):
        self.assertTrue(self.fsm.on_capture(self.capture()))
        return self.body(stack_id="stack-01", transfer_id=self.fsm.transfer_id,
                         capture_id=self.fsm.capture_id, image_stamp_ns=101, rgb_sha256="b"*64,
                         status="STABLE", confidence=0.2, model_version="fixture-resnet18",
                         inference_ok=True, raw_status="STABLE", raw_confidence=0.2,
                         reason="", stable_confidence_min=0.0, unstable_confidence_min=0.0)
    def test_physical_ack_before_next_step(self):
        data=self.load()
        self.assertEqual(self.fsm.state,"LOADING")
        self.assertFalse(self.fsm.on_transfer(dict(data, transfer_id="wrong")))
        self.assertTrue(self.fsm.on_transfer(data))
        self.assertFalse(self.fsm.on_transfer(data))
        self.assertEqual(self.fsm.state,"CAPTURING")
    def test_manual_approval_and_unload(self):
        self.assertTrue(self.fsm.on_stability(self.inference()))
        self.assertEqual(self.fsm.state,"NEEDS_CONFIRMATION")
        self.assertFalse(any(t=="/collection/nav_goal" and d["leg"]=="TO_RETURN" for t,d in self.fsm.drain()))
        self.assertTrue(self.fsm.on_staff(self.body(stack_id="stack-01",capture_id=self.fsm.capture_id,action="APPROVE_CONTINUE")))
        self.assertTrue(self.nav("TO_RETURN"))
        self.clock.now+=5
        self.fsm.tick()
        self.assertEqual(self.fsm.state,"UNLOADING")
        self.assertTrue(self.fsm.on_transfer(self.body(stack_id="stack-01",transfer_id=self.fsm.transfer_id,
                        operation="UNLOAD",status="ACK",reason="",entity_ids=["dish-1"],location="RETURNED",
                        tray_count=0,table_count=0,receipt_sha256="d"*64,event_sim_ns=200)))
        self.assertEqual(self.fsm.state,"TO_HOME")
        self.assertTrue(self.nav("TO_HOME"))
        self.assertEqual(self.fsm.state,"COMPLETED")
    def test_ai_timeout_not_approvable(self):
        data=self.inference()
        self.clock.now+=5
        self.assertFalse(self.fsm.on_stability(data))
        self.assertEqual(self.fsm.state,"SAFE_HOLD")
        self.assertFalse(self.fsm.on_staff(self.body(stack_id="stack-01",capture_id=self.fsm.capture_id,action="APPROVE_CONTINUE")))
    def test_staff_late(self):
        self.assertTrue(self.fsm.on_stability(self.inference()))
        self.clock.now+=60
        self.assertFalse(self.fsm.on_staff(self.body(stack_id="stack-01",capture_id=self.fsm.capture_id,action="APPROVE_CONTINUE")))
        self.assertEqual(self.fsm.state,"SAFE_HOLD")
    def test_unknown_uuid_timeout_lockout(self):
        self.start()
        self.clock.now+=120
        self.fsm.tick()
        self.assertEqual(self.fsm.state,"SAFE_HOLD_UNVERIFIED")
        self.assertFalse(self.fsm.handle_request(dict(self.request,request_id="r2")))
    def test_invalid_thresholds(self):
        for pair in [(-0.1,0),(0,1.1),(float("nan"),0),(True,0)]:
            with self.assertRaises(ValueError): RecoveryFSM.validate_thresholds(pair)
        self.assertEqual(RecoveryFSM.validate_thresholds((0,1)),(0.0,1.0))
    def test_hard_failure_cannot_continue(self):
        data=self.inference()
        self.assertFalse(self.fsm.on_stability(dict(data,inference_ok=False)))
        self.assertEqual(self.fsm.state,"SAFE_HOLD")
    def test_ai_off_recovery_requires_load(self):
        self.start(False)
        self.assertTrue(self.nav("TO_TABLE"))
        self.clock.now+=10
        self.fsm.tick()
        self.assertEqual(self.fsm.state,"LOADING")
        self.assertFalse(any(t=="/collection/ai_check_request" for t,d in self.fsm.drain()))

    def test_cancel_exact_uuid_and_stop(self):
        self.start()
        self.assertTrue(self.fsm.bind_goal_uuid("TO_TABLE","1"*32))
        self.clock.now+=120
        self.fsm.tick()
        self.assertEqual(self.fsm.state,"CANCELING")
        cancel=[d for t,d in self.fsm.drain() if t=="/collection/nav_cancel_request"]
        self.assertEqual(len(cancel),1)
        self.assertEqual(cancel[0]["goal_uuid"],"1"*32)
        self.assertFalse(self.fsm.on_cancel(self.body(leg="TO_TABLE",goal_uuid="2"*32,status="ACK",terminal_status="CANCELED",stop_verified=True)))
        self.assertTrue(self.fsm.on_cancel(self.body(leg="TO_TABLE",goal_uuid="1"*32,status="ACK",terminal_status="CANCELED",stop_verified=True)))
        self.assertEqual(self.fsm.state,"ABORTED")
    def test_reused_goal_uuid_rejected(self):
        self.assertTrue(self.fsm.on_stability(self.inference()))
        self.assertTrue(self.fsm.on_staff(self.body(stack_id="stack-01",capture_id=self.fsm.capture_id,action="APPROVE_CONTINUE")))
        self.assertFalse(self.fsm.on_nav_result(self.body(leg="TO_RETURN",goal_uuid="1"*32,result="SUCCEEDED",terminal_status="SUCCEEDED",stop_verified=True)))
    def test_snapshot_mismatch(self):
        data=self.inference()
        self.assertFalse(self.fsm.on_stability(dict(data,stable_confidence_min=0.5)))
        self.assertEqual(self.fsm.state,"SAFE_HOLD")
    def test_stale_capture(self):
        data=self.capture()
        self.assertFalse(self.fsm.on_capture(dict(data,image_stamp_ns=100)))
        self.assertEqual(self.fsm.state,"SAFE_HOLD")
    def test_no_rearm_after_unverified_motion(self):
        self.start()
        self.clock.now+=120
        self.fsm.tick()
        self.assertFalse(self.fsm.arm("new-stack",(0,0)))

if __name__=="__main__": unittest.main()
