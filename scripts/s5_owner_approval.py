"""ROS-safe terminal-driven S5 owner approval; no ROS imports."""
import select
import sys
import time


def wait_for_owner_approval(spin_once, *, stream=None, timeout_sec=300.0,
                            clock=time.monotonic, poll_sec=0.12):
    """Poll operator input while continuing real Scan/Odom/TF callbacks.

    Wrapper must have a real operator TTY. Invalid, EOF and timeout never
    authorize a Goal. No independent Executor or ROS subscriber is created.
    """
    if stream is None:
        stream=sys.stdin
    try:
        stream.fileno()
    except (AttributeError, OSError, ValueError) as exc:
        raise RuntimeError("S5_OWNER_TTY_INPUT_UNAVAILABLE") from exc
    started=clock()
    print("S5_OWNER_APPROVAL_PROMPT=Type YES-S5-LIVE-GOALS to authorize navigation",
          flush=True)
    while clock()-started < timeout_sec:
        spin_once(poll_sec)
        try:
            readable,_,_=select.select([stream],[],[],0)
        except (OSError,ValueError) as exc:
            raise RuntimeError("S5_OWNER_TTY_INPUT_UNAVAILABLE") from exc
        if not readable:
            continue
        if stream.readline().strip()!="YES-S5-LIVE-GOALS":
            raise RuntimeError("S5_OWNER_GOAL_CONFIRMATION_MISSING")
        return clock()-started
    raise RuntimeError("S5_OWNER_GOAL_CONFIRMATION_TIMEOUT")


def wait_for_fresh_sensors(spin_once, snapshot, *, timeout_sec=8.0,
                            clock=time.monotonic, poll_sec=0.12):
    """Require a new Scan AND Odom callback AFTER owner confirmation.

    snapshot() returns (scan_count, odom_count, scan_arrival_t, odom_arrival_t).
    Never fabricate sensor data or relax original Nav2 pre-goal 8s gate.
    """
    started=clock()
    before_scan,before_odom,_,_=snapshot()
    while clock()-started < timeout_sec:
        spin_once(poll_sec)
        scan_count,odom_count,scan_t,odom_t=snapshot()
        if (scan_count>before_scan and odom_count>before_odom and
                scan_t>started and odom_t>started):
            now=clock()
            return {
                'scan_count_after_approval':scan_count-before_scan,
                'odom_count_after_approval':odom_count-before_odom,
                'scan_age_sec':round(now-scan_t,3),
                'odom_age_sec':round(now-odom_t,3),
            }
    raise RuntimeError('TIMEOUT_S5_OWNER_FRESH_SCAN_ODOM_AFTER_APPROVAL')
