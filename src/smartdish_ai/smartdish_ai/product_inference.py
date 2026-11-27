"""Owner product recovery exact-frame join; ROS-free, no motion authority."""
from collections import OrderedDict
import hashlib
import math
import time

PROFILE = "OWNER_PRODUCT_RECOVERY"
FRAME = "smartdish_tray_optical"
KEYS = ("request_id", "stack_id", "transfer_id", "capture_id",
        "image_stamp_ns", "frame_id", "rgb_sha256")
TERMINAL = {"COMPLETED", "ABORTED", "ERROR", "CANCELED",
            "SAFE_HOLD", "SAFE_HOLD_UNVERIFIED"}

def valid_id(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 128

def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)

def valid_profile(msg):
    return (isinstance(msg, dict) and type(msg.get("schema_version")) is int
            and msg["schema_version"] == 2 and msg.get("profile") == PROFILE)

def identity(msg):
    if not valid_profile(msg) or not all(valid_id(msg.get(k)) for k in KEYS[:4]):
        return None
    if (type(msg.get("image_stamp_ns")) is not int or msg["image_stamp_ns"] <= 0
            or msg.get("frame_id") != FRAME or not valid_hash(msg.get("rgb_sha256"))):
        return None
    return tuple(msg[k] for k in KEYS)

class ProductInference:
    """Single executor only. No retry; restart requires a new mission/run."""
    def __init__(self, predictor, model_version, stable=0., unstable=0.,
                 capacity=16, freshness=2., timeout=5.):
        if type(capacity) is not int or not 1 <= capacity <= 64:
            raise ValueError("C_INVALID_CACHE_CAPACITY")
        if not 0 < freshness <= 2 or not 0 < timeout <= 5:
            raise ValueError("C_INVALID_DEADLINE")
        self.active = None
        self.set_thresholds(stable, unstable)
        self.predictor = predictor
        self.model_version = model_version if predictor is not None else "none"
        self.capacity, self.freshness, self.timeout = capacity, freshness, timeout
        self.frames = OrderedDict()
        self.last_stamp = 0
        self.rewound = False
        self.pending = None
        self.finished_requests = set()
        self.used_captures = set()
        self.used_stamps = set()

    def set_thresholds(self, stable, unstable):
        if self.active is not None:
            raise ValueError("C_MISSION_THRESHOLD_LOCKED")
        if not all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1
                   for x in (stable, unstable)):
            raise ValueError("C_INVALID_CLASS_DECISION_THRESHOLD")
        self.thresholds = (float(stable), float(unstable))
        return self.thresholds

    def mission_status(self, msg):
        if not valid_profile(msg) or not valid_id(msg.get("request_id")):
            return
        req = msg["request_id"]
        state = msg.get("state")
        if not isinstance(state, str) or not state:
            return
        if state in TERMINAL:
            self.finished_requests.add(req)
            if req == self.active:
                self.active = None
                self.pending = None
        elif self.active is None and req not in self.finished_requests:
            self.active = req

    def cache_rgb(self, rgb, width, height, stamp, frame_id, now):
        if (frame_id != FRAME or type(stamp) is not int or stamp <= 0
                or width != 640 or height != 480 or not isinstance(rgb, bytes)
                or len(rgb) != width * height * 3 or self.rewound):
            return False
        if stamp < self.last_stamp:
            self.rewound = True
            self.frames.clear()
            return False
        if stamp == self.last_stamp:
            return False
        self.last_stamp = stamp
        self._prune(now)
        self.frames[stamp] = (rgb, hashlib.sha256(rgb).hexdigest(), now)
        while len(self.frames) > self.capacity:
            self.frames.popitem(last=False)
        return True

    def _prune(self, now):
        for stamp, (_, _, received) in list(self.frames.items()):
            if not 0 <= now - received <= self.freshness:
                del self.frames[stamp]

    def request(self, msg, now):
        return self._event(msg, now, "request")

    def capture(self, msg, now):
        return self._event(msg, now, "capture")

    def _event(self, msg, now, kind):
        if not valid_profile(msg) or not all(valid_id(msg.get(k)) for k in KEYS[:4]):
            return []
        req, cap = msg["request_id"], msg["capture_id"]
        if req in self.finished_requests or cap in self.used_captures:
            return []
        if self.active is not None and self.active != req:
            return []
        self.active = req
        if self.pending is None:
            self.pending = dict(start=now, request=None, capture=None, conflict=False,
                                thresholds=self.thresholds)
        p = self.pending
        if p[kind] is not None:
            if p[kind] != msg:
                p["conflict"] = True
        else:
            p[kind] = dict(msg)
        return self.tick(now)

    def _finish(self, reason, ok=False, label=None, confidence=None):
        p = self.pending
        msg = p["request"] or p["capture"]
        req, cap = msg["request_id"], msg["capture_id"]
        self.finished_requests.add(req)
        self.used_captures.add(cap)
        self.pending = None
        if p["request"] is None:
            return []
        stable, unstable = p["thresholds"]
        status = label if ok and reason == "OK" else "UNKNOWN"
        return [dict(schema_version=2, profile=PROFILE, request_id=req,
                     capture_id=cap, stack_id=msg["stack_id"], transfer_id=msg["transfer_id"],
                     image_stamp_ns=msg.get("image_stamp_ns") if type(msg.get("image_stamp_ns")) is int else None,
                     rgb_sha256=msg.get("rgb_sha256") if valid_hash(msg.get("rgb_sha256")) else None,
                     model_version=self.model_version, inference_ok=ok,
                     raw_status=label, raw_confidence=confidence, status=status,
                     confidence=confidence if status != "UNKNOWN" else None, reason=reason,
                     stable_confidence_min=stable, unstable_confidence_min=unstable)]

    def tick(self, now):
        p = self.pending
        if p is None:
            return []
        if now - p["start"] >= self.timeout or now < p["start"]:
            return self._finish("AI_TIMEOUT")
        if p["request"] is None:
            return []
        req, cap = p["request"], p["capture"]
        key = identity(req)
        if self.rewound or p["conflict"] or key is None:
            return self._finish("FRAME_INVALID")
        if cap is None:
            return []
        if (identity(cap) != key or cap.get("status") != "ACK"
                or cap.get("width") != 640 or cap.get("height") != 480
                or cap.get("encoding") not in ("rgb8", "bgr8")
                or not valid_hash(cap.get("receipt_sha256"))):
            return self._finish("FRAME_INVALID")
        stamp = req["image_stamp_ns"]
        if stamp in self.used_stamps:
            return self._finish("FRAME_INVALID")
        frame = self.frames.get(stamp)
        if frame is None:
            # Do not substitute the most recent frame; wait for DDS reorder.
            return []
        rgb, digest, received = frame
        if digest != req["rgb_sha256"] or not 0 <= now - received <= self.freshness:
            return self._finish("FRAME_INVALID")
        if self.predictor is None:
            return self._finish("MODEL_UNAVAILABLE")
        self.used_stamps.add(stamp)  # reserve before invoking predictor
        started = time.monotonic()
        try:
            label, conf = self.predictor(rgb, 640, 480)
            if (label not in ("STABLE", "UNSTABLE") or type(conf) not in (int, float)
                    or not math.isfinite(conf) or not 0 <= conf <= 1):
                return self._finish("INFERENCE_FAILED")
        except Exception:
            return self._finish("INFERENCE_FAILED")
        if now - p["start"] + time.monotonic() - started >= self.timeout:
            return self._finish("AI_TIMEOUT")
        limit = p["thresholds"][0 if label == "STABLE" else 1]
        return self._finish("OK" if conf >= limit else "LOW_CONFIDENCE",
                            True, label, float(conf))
