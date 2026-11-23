#!/usr/bin/env python3
"""Bounded independent Gazebo/Qt/WSLg A/B, NO ROS and NO Nav2 Goal.

Do not interpret an alive gz GUI process as successful OpenGL rendering.
Only a human screenshot / visual confirmation can pass GUI visual acceptance.
Stop strictly process groups started by THIS diagnostic, never global pkill.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import zipfile

def profile(base,name):
    e=base.copy()
    e['GZ_PARTITION']='s6_wslg_gui_diagnostic_'+str(os.getpid())
    # One variable changed at a time in the first two comparisons.
    if name=='baseline':
        pass
    elif name=='xcb':
        e['QT_QPA_PLATFORM']='xcb'
    elif name=='xcb_no_wayland':
        e['QT_QPA_PLATFORM']='xcb'
        e.pop('WAYLAND_DISPLAY',None)
    elif name=='xcb_nvidia_d3d12':
        e['QT_QPA_PLATFORM']='xcb'
        e.pop('LIBGL_ALWAYS_SOFTWARE',None)
        e['GALLIUM_DRIVER']='d3d12'
        e['MESA_D3D12_DEFAULT_ADAPTER_NAME']='NVIDIA'
    elif name=='xcb_llvmpipe':
        e['QT_QPA_PLATFORM']='xcb'
        e.pop('GALLIUM_DRIVER',None)
        e.pop('MESA_D3D12_DEFAULT_ADAPTER_NAME',None)
        e['LIBGL_ALWAYS_SOFTWARE']='1'
    else:
        raise ValueError('S6_UNKNOWN_GPU_PROFILE')
    return e

def classify(log,rc,observed_secs):
    if 'Failed to create OpenGL context' in log:
        return 'S6_GUI_OPENGL_CONTEXT_ERROR'
    if 'core dumped' in log.lower() or 'segmentation fault' in log.lower() or rc in (-6,-11,134,139):
        return 'S6_GUI_CRASH'
    if 'could not load the qt platform plugin' in log.lower():
        return 'S6_QT_PLUGIN_ERROR'
    if rc is not None and rc!=0:
        return 'S6_GUI_EXITED_NONZERO'
    if rc==0:
        return 'S6_GUI_EXITED_ZERO_VISUAL_NOT_VERIFIED'
    return 'S6_GUI_STILL_RUNNING_VISUAL_NOT_VERIFIED'

def terminate_group(proc):
    if proc.poll() is not None:
        return proc.returncode
    try:
        os.killpg(proc.pid,signal.SIGINT)
    except ProcessLookupError:
        return proc.poll()
    try:
        return proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:return proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            return proc.wait(timeout=3)

def run_cmd(args,env,seconds):
    start=time.monotonic()
    p=subprocess.Popen(args,env=env,stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT,start_new_session=True,text=True)
    early=None
    try:
        try:out,_=p.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            early=None
            terminate_group(p)
            out,_=p.communicate(timeout=3)
        else:
            early=p.returncode
    finally:
        terminate_group(p)
    return {'exit_before_timeout':early,'elapsed_sec':round(time.monotonic()-start,3),
            'log_tail':out[-6500:]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--profile',choices=['all','baseline','xcb','xcb_no_wayland','xcb_nvidia_d3d12','xcb_llvmpipe'],default='all')
    p.add_argument('--hold-sec',type=int,default=9)
    a=p.parse_args()
    if a.hold_sec<3 or a.hold_sec>25:
        raise SystemExit('S6_GUI_PROBE_INVALID_TIMEOUT_NO_GOAL')
    a.out_dir.mkdir(parents=True,exist_ok=True)
    if not shutil.which('gz'):
        raise SystemExit('S6_GUI_PROBE_GZ_NOT_INSTALLED_NO_GOAL')
    base=os.environ.copy()
    profiles=['baseline','xcb','xcb_no_wayland','xcb_nvidia_d3d12','xcb_llvmpipe'] if a.profile=='all' else [a.profile]
    results={'diagnostic_only':True,'nav_goal_sent':False,'visual_accepted':'NOT_VERIFIED',
             'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'baseline_display':base.get('DISPLAY',''),'baseline_wayland':bool(base.get('WAYLAND_DISPLAY')),
             'modes':[]}
    for name in profiles:
        env=profile(base,name)
        row={'profile':name,'qt':env.get('QT_QPA_PLATFORM','UNSET'),
             'wayland_present':bool(env.get('WAYLAND_DISPLAY')),
             'gallium':env.get('GALLIUM_DRIVER','UNSET'),
             'libgl_software':env.get('LIBGL_ALWAYS_SOFTWARE','UNSET')}
        if shutil.which('glxinfo'):
            probe=subprocess.run(['glxinfo','-B'],env=env,text=True,
                                 capture_output=True,timeout=8)
            row['glxinfo_lines']=[
                s.strip()[:240] for s in (probe.stdout+probe.stderr).splitlines()
                if any(term in s for term in ('OpenGL vendor','OpenGL renderer','OpenGL version','Accelerated:'))][:6]
        run=run_cmd(['gz','sim','-g','-v2','--force-version','8'],env,a.hold_sec)
        row.update({k:v for k,v in run.items() if k!='log_tail'})
        row['classification']=classify(run['log_tail'],run['exit_before_timeout'],run['elapsed_sec'])
        (a.out_dir/(name+'.log')).write_text(run['log_tail'])
        results['modes'].append(row)
        print('S6_GUI_PROBE '+name+' '+row['classification'],flush=True)
    (a.out_dir/'gui_profiles.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
    if shutil.which('nvidia-smi'):
        p=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],
                         capture_output=True,text=True,timeout=8)
        (a.out_dir/'nvidia.txt').write_text((p.stdout+p.stderr)[-1200:])
    ogre=Path.home()/'.gz/rendering/ogre2.log'
    if ogre.is_file():
        (a.out_dir/'ogre2_tail.txt').write_text('\n'.join(ogre.read_text(errors='replace').splitlines()[-100:]))
    with zipfile.ZipFile(str(a.out_dir)+'.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in a.out_dir.iterdir():
            if path.is_file():z.write(path,arcname=path.name)
    print('S6_GUI_PROBE_ZIP='+str(a.out_dir)+'.zip')
    print('S6_GUI_VISUAL_ACCEPTANCE=NOT_VERIFIED')
if __name__=='__main__':main()
