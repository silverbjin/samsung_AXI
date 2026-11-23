#!/usr/bin/env python3
"""S7 STUDENT TODO: verify evidence from the real Gazebo S7 L2/L3 run.

Important: this file is intentionally incomplete. It must NEVER print PASS
before the student implements and checks every requirement.
"""
import argparse
import json
from pathlib import Path

def evaluate(evidence,ppm_path):
    # TODO 1: verify s7_scene.scenario == stacked and initial static fixture.
    # TODO 2: verify TWO NavigateToPose SUCCEEDED legs (TABLE_3, PICKUP_RETURN).
    # TODO 3: inspect the s6_vision actual RGB metadata and authorization.
    # TODO 4: read the P6 PPM file, hash the raw RGB payload with SHA256.
    # TODO 5: verify collision monitor stop filtered output and odom drift.
    # TODO 6: return a dictionary of observed metrics. Never hardcode PASS.
    raise NotImplementedError('S7_STUDENT_TODO_NOT_COMPLETED_NO_PASS')

def main():
    p=argparse.ArgumentParser(description='S7 student evidence validation TODO, no ROS/Goal')
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--ppm',type=Path,required=True)
    a=p.parse_args()
    e=json.loads(a.evidence.read_text())
    print(evaluate(e,a.ppm))
if __name__=='__main__':
    main()
