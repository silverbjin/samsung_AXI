#!/usr/bin/env python3
"""CI-only pseudo-TTY delay injector around the *real* S5 Gazebo run.

No mock ROS, no synthetic sensor data, no alternate Nav2/CM control.
Runs the unchanged S5 scenario with --live-owner, waits for the true
operator prompt, delays 12s, and types the same YES as field operator.
"""
import argparse
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--robot-sdf',type=Path,required=True)
    parser.add_argument('--map',type=Path,required=True)
    parser.add_argument('--params',type=Path,required=True)
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--approval-delay-sec',type=float,default=12.0)
    args=parser.parse_args()
    if os.environ.get('CI','').lower()!='true':
        raise SystemExit('S5_CI_TTY_HARNESS_ONLY_IN_CI')
    if args.approval_delay_sec < 10.0:
        raise SystemExit('S5_CI_APPROVAL_DELAY_MUST_EXCEED_8S')
    master,slave=os.openpty()
    cmd=[sys.executable,str(Path(__file__).with_name('ci_s3_amcl_smoke.py')),
         '--s5-integrated','--exercise-goals','--menu-safety',
         '--no-initial-pose-publish','--gui','--live-owner',
         '--ci-owner-exit-on-success',
         '--robot-sdf',str(args.robot_sdf),'--map',str(args.map),
         '--params',str(args.params),'--log',str(args.log),
         '--evidence',str(args.evidence)]
    env=os.environ.copy()
    env['SAMSUNGAXI_S5_GOALS_APPROVED']='YES-S5-LIVE-GOALS'
    p=subprocess.Popen(cmd,stdin=slave,stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT,env=env,
                       start_new_session=True,bufsize=0)
    os.close(slave)
    prompted=None
    sent=False
    log_tail=b''
    overall=time.monotonic()+1100
    try:
        while True:
            ready,_,_=select.select([p.stdout],[],[],.25)
            if ready:
                payload=os.read(p.stdout.fileno(),65536)
                if payload:
                    sys.stdout.buffer.write(payload)
                    sys.stdout.buffer.flush()
                    log_tail=(log_tail+payload)[-10000:]
                    if prompted is None and b'S5_OWNER_APPROVAL_PROMPT=' in log_tail:
                        prompted=time.monotonic()
                        print('S5_CI_OWNER_TTY_PROMPT_OBSERVED',flush=True)
                elif p.poll() is not None:
                    break
            if (prompted is not None and not sent and
                    time.monotonic()-prompted>=args.approval_delay_sec):
                os.write(master,b'YES-S5-LIVE-GOALS\n')
                sent=True
                print('S5_CI_DELAYED_TTY_YES_SENT DELAY_SEC='+str(args.approval_delay_sec),flush=True)
            if time.monotonic()>overall:
                raise RuntimeError('S5_CI_GAZEBO_DELAYED_TTY_TIMEOUT')
            if p.poll() is not None and not ready:
                break
        rc=p.wait(timeout=10)
        if rc!=0:
            raise RuntimeError('S5_CI_OWNER_REAL_GAZEBO_EXIT_NONZERO:'+str(rc))
        if not sent:
            raise RuntimeError('S5_CI_TTY_PROMPT_OR_APPROVAL_MISSING')
        print('S5_CI_DELAYED_OWNER_REAL_GAZEBO_PASS',flush=True)
    finally:
        if p.poll() is None:
            os.killpg(p.pid,signal.SIGINT)
            try:p.wait(timeout=12)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGTERM)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid,signal.SIGKILL)
                    p.wait()
        os.close(master)


if __name__=='__main__':main()
