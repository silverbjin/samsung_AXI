"""SmartDish D service state machine. No ROS, Gazebo or synthetic Nav2 successes.

All input events originate from the v1.0 JSON contract. Unit tests inject a
clock and simulated results; such tests are MOCK_ONLY, never real navigation.
"""
import math
import time
import uuid
import re

ACTIVE_STATES = frozenset({
    "TO_TABLE", "WAIT_LOADING", "AI_CHECK", "NEEDS_CONFIRMATION",
    "TO_RETURN", "WAIT_UNLOADING", "TO_HOME",
})
LEG_DESTINATIONS = {
    "TO_TABLE": "T03",
    "TO_RETURN": "DISH_RETURN",
    "TO_HOME": "HOME",
}
VALID_RESULTS = {"SUCCEEDED", "FAILED", "CANCELED"}
VALID_STABILITY = {"STABLE", "UNSTABLE", "UNKNOWN"}
VALID_ACTIONS = {"APPROVE_CONTINUE", "ABORT"}


class MissionManager:
    """Single-ACTIVE, fail-closed, monotonic-clock service logic.

    events is an outgoing queue of (ROS topic, JSON object); users of this
    module must publish events without inventing navigation results.
    """

    def __init__(self, clock=None, ai_available=False, ai_timeout_s=5.0,
                 approved_model_sha256=None):
        self.clock = clock if clock is not None else time.monotonic
        self.ai_available = bool(ai_available)
        # Pure-FSM synthetic tests may inject a fixture digest. The deployed
        # ROS Manager can obtain one ONLY from product_admission gate.
        self.approved_model_sha256 = (
            approved_model_sha256
            if isinstance(approved_model_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", approved_model_sha256)
            else None
        )
        self.ai_timeout_s = float(ai_timeout_s)
        self.state = "IDLE"
        self.request_id = ""
        self.table_id = ""
        self.table_wait_s = 10
        self.dropoff_wait_s = 5
        self.ai_enabled = False
        self.current_leg = None
        self.capture_id = None
        self.deadline = None
        self.reason = ""
        self._last_remaining = None
        self._events = []
        self._used_request_ids = set()

    def drain(self):
        events = self._events[:]
        self._events.clear()
        return events

    def _publish(self, topic, body):
        self._events.append((topic, body))

    def _remaining(self):
        if self.state not in {"WAIT_LOADING", "WAIT_UNLOADING"}:
            return None
        return max(0, int(math.ceil(self.deadline - self.clock())))

    def _status(self):
        self._last_remaining = self._remaining()
        self._publish("/collection/status", {
            "request_id": self.request_id,
            "state": self.state,
            "table_id": self.table_id,
            "remaining_s": self._last_remaining,
            "reason": self.reason,
        })

    def _error_for_request(self, request_id, reason):
        # An independent rejection must never change an active mission.
        self._publish("/collection/status", {
            "request_id": request_id if isinstance(request_id, str) and request_id else "INVALID",
            "state": "ERROR",
            "table_id": "T03",
            "remaining_s": None,
            "reason": reason,
        })

    @staticmethod
    def _valid_request(data):
        if not isinstance(data, dict):
            return False
        rid = data.get("request_id")
        if (not isinstance(rid, str) or not (1 <= len(rid) <= 128)
                or rid.strip() != rid):
            return False
        if data.get("table_id") != "T03":
            return False
        for key, upper in (("table_wait_s", 120), ("dropoff_wait_s", 60)):
            value = data.get(key)
            if type(value) is not int or not (1 <= value <= upper):
                return False
        return type(data.get("ai_enabled")) is bool

    def handle_request(self, data):
        rid = data.get("request_id") if isinstance(data, dict) else None
        if self.state in ACTIVE_STATES:
            self._error_for_request(rid, "BUSY")
            return False
        if not self._valid_request(data):
            self._error_for_request(rid, "INVALID_REQUEST")
            return False
        if rid in self._used_request_ids:
            self._error_for_request(rid, "DUPLICATE_REQUEST_ID")
            return False
        if data["ai_enabled"] and not self.ai_available:
            self._error_for_request(rid, "AI_NOT_AVAILABLE")
            return False
        self._used_request_ids.add(rid)
        self.request_id = rid
        self.table_id = "T03"
        self.table_wait_s = data["table_wait_s"]
        self.dropoff_wait_s = data["dropoff_wait_s"]
        self.ai_enabled = data["ai_enabled"]
        self.deadline = None
        self.capture_id = None
        self.current_leg = None
        self.reason = ""
        self._begin_leg("TO_TABLE")
        return True

    def _begin_leg(self, leg):
        assert leg in LEG_DESTINATIONS
        self.state = leg
        self.current_leg = leg
        self.deadline = None
        self.reason = ""
        self._status()
        self._publish("/collection/nav_goal", {
            "request_id": self.request_id,
            "leg": leg,
            "destination_id": LEG_DESTINATIONS[leg],
        })

    def on_nav_result(self, data):
        if not isinstance(data, dict):
            return False
        if (self.state not in LEG_DESTINATIONS
                or data.get("request_id") != self.request_id
                or data.get("leg") != self.current_leg
                or data.get("result") not in VALID_RESULTS):
            return False
        result = data["result"]
        if result == "FAILED":
            self.state = "ERROR"
            self.reason = str(data.get("reason") or "NAV_FAILED")
            self.current_leg = None
            self._status()
        elif result == "CANCELED":
            self.state = "CANCELED"
            self.reason = str(data.get("reason") or "NAV_CANCELED")
            self.current_leg = None
            self._status()
        elif self.current_leg == "TO_TABLE":
            self._start_wait("WAIT_LOADING", self.table_wait_s)
        elif self.current_leg == "TO_RETURN":
            self._start_wait("WAIT_UNLOADING", self.dropoff_wait_s)
        else:
            self.current_leg = None
            self.state = "COMPLETED"
            self.reason = ""
            self._status()
        return True

    def _start_wait(self, state, seconds):
        self.state = state
        self.current_leg = None
        self.deadline = self.clock() + seconds
        self.reason = ""
        self._status()

    def _start_ai_check(self):
        self.state = "AI_CHECK"
        self.capture_id = f"{self.request_id}-AI-{uuid.uuid4().hex[:10]}"
        self.deadline = self.clock() + self.ai_timeout_s
        self._status()
        self._publish("/collection/ai_check_request", {
            "request_id": self.request_id,
            "capture_id": self.capture_id,
        })

    def _needs_confirmation(self, reason):
        self.state = "NEEDS_CONFIRMATION"
        self.reason = reason
        self.deadline = None
        self._status()

    def on_stability(self, data):
        if not isinstance(data, dict) or self.state != "AI_CHECK":
            return False
        if (data.get("request_id") != self.request_id
                or data.get("capture_id") != self.capture_id
                or data.get("status") not in VALID_STABILITY):
            return False
        # Deadline must be enforced at message receipt too: a late STABLE
        # cannot sneak in before the 0.2s ROS timer callback.
        if self.clock() >= self.deadline:
            self._needs_confirmation("AI_TIMEOUT")
            return False
        status = data["status"]
        # The v1.0 contract requires confidence and model_version. A missing
        # or fabricated STABLE must never authorize motion; wait for timeout.
        if "confidence" not in data or "model_version" not in data:
            return False
        confidence = data["confidence"]
        if confidence is not None and (
                type(confidence) not in (int, float)
                or not math.isfinite(confidence)
                or not 0.0 <= confidence <= 1.0):
            return False
        model = data["model_version"]
        if not isinstance(model, str) or not model:
            return False
        if status == "STABLE":
            # A correlated ROS message is NOT an authorized model signature.
            # Product admission must inject a reviewed SHA, and the C response
            # must match its published model version and confidence floor.
            if (confidence is None or confidence < 0.80
                    or self.approved_model_sha256 is None
                    or model != "resnet18-" + self.approved_model_sha256[:12]):
                return False
            self._begin_leg("TO_RETURN")
        else:
            self._needs_confirmation(f"AI_{status}")
        return True

    def on_staff_confirm(self, data):
        if not isinstance(data, dict) or self.state != "NEEDS_CONFIRMATION":
            return False
        if (data.get("request_id") != self.request_id
                or data.get("action") not in VALID_ACTIONS):
            return False
        if data["action"] == "APPROVE_CONTINUE":
            self._begin_leg("TO_RETURN")
        else:
            self.state = "CANCELED"
            self.reason = "STAFF_ABORT"
            self._status()
        return True

    def tick(self):
        now = self.clock()
        if self.state in {"WAIT_LOADING", "WAIT_UNLOADING"}:
            if now >= self.deadline:
                if self.state == "WAIT_LOADING":
                    if self.ai_enabled:
                        self._start_ai_check()
                    else:
                        self._begin_leg("TO_RETURN")
                else:
                    self._begin_leg("TO_HOME")
            elif self._remaining() != self._last_remaining:
                self._status()
        elif self.state == "AI_CHECK" and now >= self.deadline:
            self._needs_confirmation("AI_TIMEOUT")
