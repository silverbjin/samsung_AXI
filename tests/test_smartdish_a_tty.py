"""A-L2-DBG-02 RED→GREEN: real pseudo-terminal acceptance + refusal (NO ROS)."""
import errno
import os
from pathlib import Path
import pty
import select
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/smartdish_robot"))
from smartdish_robot.tty_approval import APPROVAL_TEXT, require_operator_approval


def _run_tty_case(answer):
    pid, master = pty.fork()
    if pid == 0:
        try:
            require_operator_approval()
        except RuntimeError:
            os._exit(2)
        os._exit(0)

    sent = False
    deadline = time.monotonic() + 4
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], .1)[0]:
                try:
                    message = os.read(master, 4096)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if APPROVAL_TEXT.encode() in message and not sent:
                    os.write(master, (answer + "\n").encode())
                    sent = True
        _, status = os.waitpid(pid, 0)
        return sent, os.waitstatus_to_exitcode(status)
    finally:
        os.close(master)


def test_real_tty_explicit_correct_approval_is_accepted():
    assert _run_tty_case(APPROVAL_TEXT) == (True, 0)


def test_real_tty_wrong_approval_is_denied():
    assert _run_tty_case("NO") == (True, 2)


def test_tty_implementation_does_not_use_nonseekable_r_plus():
    src = (ROOT / "src/smartdish_robot/smartdish_robot/tty_approval.py").read_text()
    assert "os.open(\"/dev/tty\", os.O_RDWR)" in src
    assert "os.read(fd, 1)" in src
    assert "fdopen(" not in src
