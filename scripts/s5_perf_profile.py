#!/usr/bin/env python3
"""Read-only, stage-labelled Gazebo Harmonic RTF observer for S5 live GUI.

Gazebo /world/restaurant/stats is the ONLY RTF source. Sampling does not
publish cmd_vel, change Gazebo physics or create ROS nodes. Each row is
labelled using the existing same-session owner run log. Optional process CPU
percentages are approximate lifetime-average ps readings, not instantaneous
or a GPU rendering proof. Absence of samples is NOT a performance PASS.
"""
import argparse
import csv
import datetime
import json
import os
from pathlib import Path
import re
import select
import signal
import statistics
import subprocess
import time

RUNNING=True
RTF=re.compile(r'^\s*real_time_factor:\s*([0-9eE+.-]+)')
PHASE_MARKERS=(
    ('S5_OWNER_GOALS_AUTHORIZED', 'owner_authorized'),
    ('S3_NAV02_REAL_GOAL_ACCEPTED=TABLE_3', 'normal_delivery'),
    ('S3_NAV02_GOAL_SUCCEEDED=TABLE_3', 'table3_arrived'),
    ('S3_NAV02_REAL_GOAL_ACCEPTED=PICKUP_RETURN', 'soup_return'),
    ('S3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN', 'pickup_arrived'),
    ('S4_PHYSICAL_FIXTURE_LIDAR_POINTS', 'safety_fixture'),
    ('S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS', 'safety_pass'),
    ('S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS', 'complete'),
)
MOVING=('normal_delivery','soup_return')


def phase_from_line(previous,line):
    for key,phase in PHASE_MARKERS:
        if key in line:
            return phase
    return previous


def summarize(rows):
    """Percent and phase comparison, fail closed on missing moving samples."""
    groups={'all':rows,'moving':[r for r in rows if r['phase'] in MOVING]}
    for stage in sorted({r['phase'] for r in rows}):
        groups['phase_'+stage]=[r for r in rows if r['phase']==stage]
    result={}
    for name,subset in groups.items():
        samples=sorted(float(r['rtf']) for r in subset if r.get('rtf') is not None)
        if not samples:
            result[name]={'sample_count':0,'median':None,'p10':None,'above_90_count':0}
            continue
        result[name]={
            'sample_count':len(samples),
            'median':round(statistics.median(samples),4),
            'p10':round(samples[int((len(samples)-1)*.1)],4),
            'above_90_count':sum(x>=.9 for x in samples),
            'mean':round(statistics.mean(samples),4),
        }
    moving=result['moving']
    result['moving_target_median_ge_90'] = (
        moving['sample_count']>=25 and moving['median']>=.9)
    result['moving_measurement_sufficient']=moving['sample_count']>=25
    result['claim']='OWNER_WSL2_MEASUREMENT_ONLY_NOT_CI_GPU_PROOF'
    return result


def read_cpu():
    """Non-intrusive indication, using ps lifetime-average CPU not peak load."""
    try:
        out=subprocess.run(['ps','-eo','comm=,pcpu=,rss='],
                           capture_output=True,text=True,timeout=2,check=True).stdout
        values={'gz_cpu_pct':0.,'nav_cpu_pct':0.,'gz_rss_mb':0.}
        for line in out.splitlines():
            parts=line.split()
            if len(parts)!=3:
                continue
            name,raw_cpu,raw_rss=parts
            try:
                cpu=float(raw_cpu)
                rss=float(raw_rss)/1024
            except ValueError:
                continue
            if name.startswith(('gz','ruby','rviz')):
                values['gz_cpu_pct']+=cpu
                values['gz_rss_mb']+=rss
            elif ('nav' in name or 'controller' in name or 'planner' in name
                  or name in ('component_conta','behavior_server')):
                values['nav_cpu_pct']+=cpu
        return {k:round(v,2) for k,v in values.items()}
    except (OSError,subprocess.SubprocessError):
        return {'gz_cpu_pct':None,'nav_cpu_pct':None,'gz_rss_mb':None}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run-log',required=True,type=Path)
    p.add_argument('--csv-out',required=True,type=Path)
    p.add_argument('--summary-out',required=True,type=Path)
    p.add_argument('--mode',choices=['baseline','rgbd2'],required=True)
    p.add_argument('--max-sec',type=int,default=1100)
    p.add_argument('--sample-interval',type=float,default=1.0)
    args=p.parse_args()
    for path in (args.csv_out,args.summary_out):
        path.parent.mkdir(parents=True,exist_ok=True)
    phase='startup'
    log_pos=0
    log_fragment=''
    pending=''
    last_rtf=None
    gz=None
    next_retry=0.
    now=time.monotonic()
    started=now
    next_sample=now
    next_cpu=now
    cpu={'gz_cpu_pct':None,'nav_cpu_pct':None,'gz_rss_mb':None}
    rows=[]

    def stop(_signum,_frame):
        global RUNNING
        RUNNING=False

    signal.signal(signal.SIGINT,stop)
    signal.signal(signal.SIGTERM,stop)
    fields=['utc','elapsed_sec','phase','rtf','gz_cpu_pct','nav_cpu_pct','gz_rss_mb']
    with args.csv_out.open('w',newline='',encoding='utf-8') as target:
        writer=csv.DictWriter(target,fieldnames=fields)
        writer.writeheader()
        try:
            while RUNNING and time.monotonic()-started<args.max_sec:
                now=time.monotonic()
                if args.run_log.exists():
                    # Same-session owner output is line-buffered by tee.
                    with args.run_log.open('r',encoding='utf-8',errors='replace') as log:
                        log.seek(log_pos)
                        chunk=log.read()
                        log_pos=log.tell()
                    if chunk:
                        segments=(log_fragment+chunk).split('\n')
                        log_fragment=segments.pop()
                        for line in segments:
                            phase=phase_from_line(phase,line)

                if gz is None or gz.poll() is not None:
                    if gz is not None:
                        try:gz.stdout.close()
                        except (OSError,AttributeError):pass
                        gz=None
                    if now>=next_retry:
                        try:
                            gz=subprocess.Popen(
                                ['gz','topic','-e','-t','/world/restaurant/stats'],
                                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                bufsize=0)
                        except OSError:
                            gz=None
                        next_retry=now+4.
                if gz is not None:
                    readable,_,_=select.select([gz.stdout],[],[],.15)
                    if readable:
                        data=os.read(gz.stdout.fileno(),32768)
                        if data:
                            chunks=(pending+data.decode('utf-8','replace')).split('\n')
                            pending=chunks.pop()
                            for line in chunks:
                                match=RTF.match(line)
                                if match:
                                    try:
                                        rtf=float(match.group(1))
                                        if 0.<=rtf<=10.:last_rtf=rtf
                                    except ValueError:pass
                else:
                    time.sleep(.15)
                now=time.monotonic()
                if now>=next_cpu:
                    cpu=read_cpu()
                    next_cpu=now+5.
                if now>=next_sample:
                    next_sample=now+max(.5,args.sample_interval)
                    if last_rtf is not None:
                        row={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             'elapsed_sec':round(now-started,2),
                             'phase':phase,'rtf':round(last_rtf,6),**cpu}
                        rows.append(row)
                        writer.writerow(row)
                        target.flush()
                        last_rtf=None  # Never replay a stale Gazebo value.
        finally:
            if gz is not None and gz.poll() is None:
                gz.terminate()
                try:gz.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    gz.kill();gz.wait()
            summary={'profile_mode':args.mode,'duration_sec':round(time.monotonic()-started,2),
                     'gz_stats_topic':'/world/restaurant/stats',
                     'process_cpu_definition':'ps lifetime-average percent, indicative only',
                     'rtf':summarize(rows)}
            args.summary_out.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
            print('S5_PERF_PROFILE_SAVED='+str(args.summary_out),flush=True)


if __name__=='__main__':
    main()
