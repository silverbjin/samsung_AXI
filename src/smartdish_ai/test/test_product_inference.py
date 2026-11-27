import hashlib
import unittest

from smartdish_ai.product_inference import ProductInference, PROFILE

RGB = bytes([1, 2, 3]) * (640 * 480)
HASH = hashlib.sha256(RGB).hexdigest()

def ids(req="r", cap="c", stamp=100, digest=HASH):
    return dict(schema_version=2, profile=PROFILE, request_id=req,
                stack_id="stack", transfer_id="load", capture_id=cap,
                image_stamp_ns=stamp, frame_id="smartdish_tray_optical",
                rgb_sha256=digest)

def ack(**kwargs):
    return dict(ids(**kwargs), status="ACK", reason="", width=640, height=480,
                encoding="rgb8", receipt_sha256="a"*64)

class ProductTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def predict(rgb, w, h):
            self.calls.append((hashlib.sha256(rgb).hexdigest(), w, h))
            return "UNSTABLE", .506081
        self.c = ProductInference(predict, "CI_DOUBLE")

    def frame(self, stamp=100, rgb=RGB, now=1):
        return self.c.cache_rgb(rgb, 640, 480, stamp, "smartdish_tray_optical", now)

    def test_exact_join_both_orders(self):
        for reverse in (False, True):
            if reverse:
                self.setUp()
            self.frame()
            self.frame(101, bytes(len(RGB)), 1.1)
            events = [(self.c.capture, ack()), (self.c.request, ids())]
            if reverse:
                events.reverse()
            self.assertEqual(events[0][0](events[0][1], 1.2), [])
            out = events[1][0](events[1][1], 1.3)[0]
            self.assertTrue(out["inference_ok"])
            self.assertEqual(out["status"], "UNSTABLE")
            self.assertEqual(self.calls, [(HASH, 640, 480)])
            self.assertEqual(self.c.request(ids(), 1.4), [])
            self.assertEqual(self.c.capture(ack(), 1.4), [])
            self.assertEqual(self.c.request(ids(cap="other"), 1.4), [])
            self.assertEqual(len(self.calls), 1)

    def test_late_frame_and_timeout(self):
        self.c.request(ids(), 1)
        self.c.capture(ack(), 1.1)
        self.frame(now=1.2)
        self.assertTrue(self.c.tick(1.3)[0]["inference_ok"])
        self.assertEqual(len(self.calls), 1)
        self.setUp()
        self.c.request(ids(), 1)
        self.c.capture(ack(), 1.1)
        self.frame(101)
        out = self.c.tick(6)[0]
        self.assertFalse(out["inference_ok"])
        self.assertEqual(out["reason"], "AI_TIMEOUT")
        self.assertEqual(self.calls, [])

    def test_mismatch_and_rewind(self):
        self.frame()
        self.c.capture(ack(digest="b"*64), 1)
        out = self.c.request(ids(), 1.1)[0]
        self.assertEqual(out["reason"], "FRAME_INVALID")
        self.assertFalse(out["inference_ok"])
        self.setUp()
        self.frame(101)
        self.assertFalse(self.frame(99))
        self.c.capture(ack(stamp=101), 1)
        out = self.c.request(ids(stamp=101), 1.1)[0]
        self.assertFalse(out["inference_ok"])
        self.assertEqual(self.calls, [])

    def test_threshold_and_lock(self):
        for bad in (True, float("nan"), float("inf"), -.1, 1.1):
            with self.assertRaises(ValueError):
                self.c.set_thresholds(0, bad)
            self.assertEqual(self.c.thresholds, (0., 0.))
        self.c.set_thresholds(.5, 1)
        self.frame()
        self.c.capture(ack(), 1)
        with self.assertRaises(ValueError):
            self.c.set_thresholds(0, 0)
        out = self.c.request(ids(), 1.1)[0]
        self.assertTrue(out["inference_ok"])
        self.assertEqual(out["status"], "UNKNOWN")
        self.assertEqual(out["raw_confidence"], .506081)
        self.assertEqual(out["reason"], "LOW_CONFIDENCE")
        self.assertEqual(out["unstable_confidence_min"], 1)

    def test_model_errors(self):
        for predictor, reason in ((None, "MODEL_UNAVAILABLE"),
                                  (lambda *a: ("STABLE", float("nan")), "INFERENCE_FAILED")):
            c = ProductInference(predictor, "CI_DOUBLE")
            c.cache_rgb(RGB, 640, 480, 100, "smartdish_tray_optical", 1)
            c.capture(ack(), 1)
            out = c.request(ids(), 1.1)[0]
            self.assertFalse(out["inference_ok"])
            self.assertEqual(out["reason"], reason)
            self.assertIsNone(out["raw_confidence"])

    def test_mission_lock_before_capture_and_release(self):
        self.c.mission_status(dict(ids(), state="WAIT_LOADING"))
        with self.assertRaises(ValueError):
            self.c.set_thresholds(.5, .5)
        self.c.mission_status(dict(ids(), state="COMPLETED"))
        self.assertEqual(self.c.set_thresholds(.5, .5), (.5, .5))
        self.assertEqual(self.c.request(ids(), 2), [])
        self.assertEqual(self.calls, [])

    def test_stale_hash_and_capacity(self):
        self.frame()
        self.c.capture(ack(), 3.1)
        out = self.c.request(ids(), 3.1)[0]
        self.assertEqual(out["reason"], "FRAME_INVALID")
        self.assertEqual(self.calls, [])
        self.setUp()
        self.frame(rgb=bytes(len(RGB)))
        self.c.capture(ack(), 1)
        self.assertEqual(self.c.request(ids(), 1.1)[0]["reason"], "FRAME_INVALID")
        self.assertEqual(self.calls, [])
        self.setUp()
        for stamp in range(1, 21):
            self.frame(stamp=stamp)
        self.assertEqual(len(self.c.frames), 16)

    def test_invalid_profile_and_hold(self):
        self.frame()
        self.assertEqual(self.c.request(dict(ids(), profile="PRODUCT"), 1), [])
        self.c.mission_status(dict(ids(), state="WAIT_LOADING"))
        self.c.mission_status(dict(ids(), state="SAFE_HOLD_UNVERIFIED"))
        with self.assertRaises(ValueError):
            self.c.set_thresholds(0, 0)
        self.assertEqual(self.c.request(ids(req="other"), 1), [])
        self.assertEqual(self.calls, [])

if __name__ == "__main__":
    unittest.main()
