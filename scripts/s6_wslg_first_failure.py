#!/usr/bin/env python3
"""Read-only first-failure classification for S6 owner ZIP. No ROS/Goal."""
import argparse,hashlib,json
from pathlib import Path
from zipfile import ZipFile

def first(lines,terms):
    for idx,line in enumerate(lines):
        if any(term in line for term in terms):
            return {'line':idx+1,'excerpt':line.strip()[:350]}
    return None

def classify(summary,run,status):
    rows=summary.splitlines()
    kv=dict(line.split('=',1) for line in status.splitlines() if '=' in line)
    opengl=first(rows,['Failed to create OpenGL context'])
    abort=first(rows,['Aborted (core dumped)'])
    ros_context=first(rows,["rcl node's context is invalid"])
    return {
        'first_failure':'S6_GUI_OPENGL_CONTEXT_CREATE_FAILED' if opengl else kv.get('FIRST_FAILED_MARKER','UNKNOWN'),
        'phase':'GAZEBO_GUI_INITIALIZATION' if opengl else kv.get('FIRST_FAILED_PHASE','UNKNOWN'),
        'gpu_gui_error':opengl,'gui_abort':abort,'ros_context_after':ros_context,
        'runtime_rc':kv.get('RUN_RC','UNKNOWN'),
        'goal_authorized':kv.get('GOAL_AUTHORIZED','UNKNOWN'),
        'goal_sent':'TRUE' if 'S3_NAV02_REAL_GOAL_ACCEPTED=' in run else kv.get('GOAL_SENT','UNKNOWN'),
        'source_pin':kv.get('PIN','UNKNOWN'),
        'original_owner_marker':kv.get('FIRST_FAILED_MARKER','UNKNOWN'),
        'scope':'ZIP_READ_ONLY_NOT_A_WSL2_RETEST'
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--zip',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    with ZipFile(args.zip) as z:
        def read(name):
            return z.read(name).decode(errors='replace') if name in z.namelist() else ''
        result=classify(read('ci-s3-summary.txt'),read('run.log'),read('status.txt'))
    result['zip_sha256']=hashlib.sha256(args.zip.read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(result['first_failure'])
if __name__=='__main__':main()
