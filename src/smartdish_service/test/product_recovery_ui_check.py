"""Xvfb Tk functional check, synthetic frame explicitly fixture-only."""
import hashlib
import os
import subprocess
import tkinter as tk
import unittest
from types import SimpleNamespace as NS
from smartdish_service.product_recovery_ui import FrameCache, RecoveryView
from smartdish_service.product_recovery_fsm import PROFILE

LAYOUT={"tables":{"T03":{"rect":[585,110,745,178],"enabled":True}},
        "areas":{"HOME":[40,380,290,430],"DISH_RETURN":[480,380,770,430]}}
RGB=bytes([11,22,33])*(640*480)
STAMP=1000000101
def frame():
    return NS(header=NS(frame_id="smartdish_tray_optical",stamp=NS(sec=1,nanosec=101)),
              width=640,height=480,encoding="bgr8",step=1924,is_bigendian=0,
              data=(bytes([33,22,11])*640+b"pad!")*480)
def ack(request_id):
    return dict(schema_version=2,profile=PROFILE,request_id=request_id,stack_id="stack-1",
                transfer_id="transfer-1",capture_id="capture-1",status="ACK",
                image_stamp_ns=STAMP,frame_id="smartdish_tray_optical",
                rgb_sha256=hashlib.sha256(RGB).hexdigest())

class UiTest(unittest.TestCase):
    def test_frame_cache_hash_and_freshness(self):
        now=[0.0]
        c=FrameCache(clock=lambda:now[0])
        self.assertTrue(c.add(frame()))
        self.assertEqual(c.selected(ack("r")),RGB)
        self.assertIsNone(c.selected(dict(ack("r"),rgb_sha256="f"*64)))
        now[0]=3.0
        c.add(frame())
        self.assertIsNone(c.selected(ack("r")))
    def test_actual_buttons_and_selected_preview(self):
        root=tk.Tk()
        try:
            sent=[]
            transactions=[]
            def threshold(pair,done):
                transactions.append((pair,done))
            view=RecoveryView(root,LAYOUT,lambda topic,body:sent.append((topic,body)),threshold,True)
            root.update()
            view.select()
            self.assertEqual(str(view.start_button.cget("state")),"disabled")
            view.on_status(dict(schema_version=2,profile=PROFILE,request_id="",state="IDLE",stack_id="stack-1"))
            view.stable.set("NaN")
            view.threshold_button.invoke()
            self.assertFalse(transactions)
            view.stable.set("0.00")
            view.unstable.set("1.00")
            view.threshold_button.invoke()
            self.assertEqual(transactions[-1][0],(0.,1.))
            self.assertEqual(str(view.start_button.cget("state")),"disabled")
            transactions[-1][1](True,(0.,1.))
            self.assertEqual(str(view.start_button.cget("state")),"normal")
            view.stable.set("0.01")
            self.assertEqual(str(view.start_button.cget("state")),"disabled")
            view.stable.set("0.00")
            view.threshold_button.invoke()
            transactions[-1][1](True,(0.,1.))
            view.start_button.invoke()
            rid=view.request_id
            self.assertEqual(sent[-1][0],"request")
            self.assertEqual(str(view.threshold_button.cget("state")),"disabled")
            self.assertEqual(str(view.approve.cget("state")),"disabled")
            def status(state,**kw):
                return dict(schema_version=2,profile=PROFILE,request_id=rid,stack_id="stack-1",
                            capture_id="capture-1",state=state,**kw)
            view.on_status(status("NEEDS_CONFIRMATION",action_allowed=True,remaining_s=60,
                                  ai_status="STABLE",confidence=0.8,thresholds=[0,1]))
            self.assertEqual(str(view.approve.cget("state")),"disabled")
            view.frame_cache.add(frame())
            view.on_capture(ack(rid))
            root.update()
            self.assertIsNotNone(view.photo)
            self.assertEqual(str(view.approve.cget("state")),"normal")
            if os.getenv("D_UI_SCREENSHOT"):
                subprocess.run(["scrot","-o",os.environ["D_UI_SCREENSHOT"]],check=True)
            view.approve.invoke()
            self.assertEqual(sent[-1][1]["action"],"APPROVE_CONTINUE")
            self.assertEqual(sent[-1][1]["capture_id"],"capture-1")
            n=len(sent)
            view.approve.invoke()
            self.assertEqual(len(sent),n)
            view.on_status(status("SAFE_HOLD",action_allowed=False,reason="AI_TIMEOUT"))
            view.approve.invoke()
            self.assertEqual(len(sent),n)
        finally:
            root.destroy()

if __name__=="__main__": unittest.main(verbosity=2)
