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
