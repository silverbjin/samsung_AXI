"""ROS-free single-request inference contract for testable fail-closed behavior.

It intentionally does not issue Navigation Goals or publish /cmd_vel.
"""
from __future__ import annotations

import json
import math
import time
from typing import Callable

LABELS = ("STABLE", "UNSTABLE")


class InferenceCore:
    def __init__(self, predictor: Callable | None = None, model_version: str = "none",
                 confidence_min: float = 0.80, max_image_age_s: float = 2.0):
        if not 0.5 <= confidence_min <= 1.0 or not 0 < max_image_age_s <= 60:
            raise ValueError("C_INVALID_INFERENCE_PARAMETERS")
        self.predictor = predictor
        self.model_version = model_version if predictor is not None else "none"
        self.confidence_min = confidence_min
        self.max_image_age_s = max_image_age_s
        self.frame = None
        self.frame_seq = 0
        self.last_used_seq = 0
        self.seen_requests: set[tuple[str, str]] = set()
        self.last_stamp_ns = None

    def cache_rgb(self, rgb: bytes, width: int, height: int,
                  *, received_at: float | None = None, stamp_ns: int | None = None) -> bool:
        if not isinstance(width, int) or not isinstance(height, int) or not (16 <= width <= 4096 and 16 <= height <= 4096):
            return False
        if not isinstance(rgb, bytes) or len(rgb) != width * height * 3:
            return False
        if stamp_ns is not None:
            if not isinstance(stamp_ns, int) or stamp_ns < 0:
                return False
            if self.last_stamp_ns is not None and stamp_ns <= self.last_stamp_ns:
                return False
            self.last_stamp_ns = stamp_ns
        self.frame_seq += 1
        self.frame = (rgb, width, height, time.monotonic() if received_at is None else received_at)
        return True

    def handle_request(self, request_json: str, *, now: float | None = None) -> dict | None:
        try:
            request = json.loads(request_json)
        except (TypeError, ValueError):
            return None  # Missing IDs: impossible to address a correlated response.
        if not isinstance(request, dict):
            return None
        req_id, capture_id = request.get("request_id"), request.get("capture_id")
        if not isinstance(req_id, str) or not isinstance(capture_id, str) or not req_id.strip() or not capture_id.strip():
            return None
        if len(req_id) > 128 or len(capture_id) > 128:
            return None
        key = (req_id, capture_id)
        if key in self.seen_requests:
            return None
        self.seen_requests.add(key)
        result = {"request_id": req_id, "capture_id": capture_id,
                  "status": "UNKNOWN", "confidence": None, "model_version": self.model_version}
        if self.predictor is None:
            return result
        current = time.monotonic() if now is None else now
        if self.frame is None or self.frame_seq <= self.last_used_seq:
            return result
        rgb, width, height, received_at = self.frame
        age = current - received_at
        if not 0 <= age <= self.max_image_age_s:
            return result
        self.last_used_seq = self.frame_seq  # never reuse the same frame across new captures
        try:
            predicted, conf = self.predictor(rgb, width, height)
            if predicted not in LABELS or isinstance(conf, bool) or not isinstance(conf, (int, float)):
                return result
            conf = float(conf)
            if not math.isfinite(conf) or not 0 <= conf <= 1 or conf < self.confidence_min:
                return result
        except Exception:
            return result  # Real failure is logged by ROS wrapper; never fabricate STABLE.
        result.update(status=predicted, confidence=round(conf, 6))
        return result
