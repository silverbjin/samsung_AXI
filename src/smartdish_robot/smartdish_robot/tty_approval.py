"""Tiny ROS-independent operator approval I/O (also tested under a real PTY).

Do not use TextIOWrapper(..., 'r+') on /dev/tty: ttys are not seekable.
This function never accepts approval from env, stdin pipes or ROS topics.
"""
import os

APPROVAL_TEXT = "YES-SMARTDISH-A-GOALS"


def require_operator_approval():
    try:
        fd = os.open("/dev/tty", os.O_RDWR)
    except OSError as exc:
        raise RuntimeError("OPERATOR_TTY_REQUIRED_NO_GOAL") from exc
    try:
        os.write(fd, ("SmartDish A: Gazebo/Nav2 실제 주행 전 환경 확인 후 "
                      + APPROVAL_TEXT + " 입력: ").encode("utf-8"))
        answer = bytearray()
        while len(answer) < 128:
            char = os.read(fd, 1)
            if not char or char == b"\n":
                break
            answer.extend(char)
        if answer.decode("utf-8", errors="replace").strip() != APPROVAL_TEXT:
            raise RuntimeError("OPERATOR_APPROVAL_DENIED_NO_GOAL")
    except OSError as exc:
        raise RuntimeError("OPERATOR_TTY_READ_FAILED_NO_GOAL") from exc
    finally:
        os.close(fd)
