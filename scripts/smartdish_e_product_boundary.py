"""E product-recovery integration boundaries; no ROS dependency or motion side effect."""
from concurrent.futures import Future, TimeoutError
from queue import Empty, Queue
from threading import Lock
import hashlib
import json
import math
from pathlib import Path

TRANSFER_SECONDS = 20.0
CANCEL_SECONDS = 15.0

class OwnerMailbox:
    """Call D exclusively on its executor thread. Timeout never authorizes a goal."""
    def __init__(self):
        self._queue = Queue()
        self._lock = Lock()
        self._closed = False

    def call(self, fn, *args, timeout=2.0):
        future = Future()
        with self._lock:
            if self._closed:
                raise RuntimeError("D_EXECUTOR_CLOSED")
            self._queue.put((future, fn, args))
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise RuntimeError("D_HOOK_TIMEOUT") from None

    def drain(self):
        """Only D's owning thread calls this method, never A or ROS callbacks on other threads."""
        while True:
            try:
                future, fn, args = self._queue.get_nowait()
            except Empty:
                return
            if not future.set_running_or_notify_cancel():
                continue
            try:
                future.set_result(fn(*args))
            except Exception as exc:
                future.set_exception(exc)

    def close(self):
        with self._lock:
            self._closed = True
            while True:
                try:
                    future, _, _ = self._queue.get_nowait()
                except Empty:
                    break
                future.cancel()

def verify_ready(receipt, receipt_path, scene, source_sha):
    """Read original A-generated physical receipt, not manifest-only readiness.
    Caller separately establishes live CM/clock/scan/odom/AMCL and robot RGB.
    """
    raw = Path(receipt_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt.get("receipt_sha256"):
        raise RuntimeError("A_READY_DIGEST_MISMATCH")
    expected = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    if json.loads(raw) != expected:
        raise RuntimeError("A_READY_CONTENT_MISMATCH")
    if (expected.get("kind") != "ACTUAL_STARTUP_ENTITY_AND_STOP"
            or expected.get("source_sha") != source_sha
            or expected.get("run_id") != scene.get("run_id")
            or expected.get("world_sha256") != scene.get("world_sha256")):
        raise RuntimeError("A_READY_PROVENANCE_MISMATCH")
    obs = expected.get("observation")
    if not isinstance(obs, dict) or scene.get("scenario") not in ("stacked", "empty"):
        raise RuntimeError("A_READY_OBSERVATION_INVALID")
    count = 3 if scene["scenario"] == "stacked" else 0
    if (not isinstance(obs.get("stack_id"), str) or not obs["stack_id"]
            or obs["stack_id"] != scene.get("stack_id")
            or type(obs.get("robot_entity_id")) is not int or obs["robot_entity_id"] <= 0
            or type(obs.get("tray_count")) is not int or obs["tray_count"] != 0
            or type(obs.get("table_count")) is not int or obs["table_count"] != count
            or (count and (type(obs.get("fixture_entity_id")) is not int or obs["fixture_entity_id"] <= 0))
            or (not count and obs.get("fixture_entity_id") is not None)):
        raise RuntimeError("A_READY_PHYSICAL_COUNT_MISMATCH")
    return obs["stack_id"]

def accepted_hook(mailbox, d_node, request_id, leg, actual_uuid):
    """A's actual ActionClient handle is the only UUID source."""
    try:
        return mailbox.call(d_node.bind_accepted_goal, request_id, leg, actual_uuid) is True
    except (RuntimeError, TimeoutError):
        return False
