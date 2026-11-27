"""E/B-QA-06: loss-visible, un-decimated same-monitor odom trace and independent dwell review.
No ROS import, no motion authority, no synthetic fallback. Monotonic and sim time separate.
"""
import hashlib
import json
import math
import re
import time
from pathlib import Path

LEGS=("TO_TABLE","TO_RETURN","TO_HOME")
PROFILE="OWNER_PRODUCT_RECOVERY"
MAX_GAP_NS=300_000_000
DWELL_NS=1_000_000_000

def need(ok,reason):
    if not ok: raise ValueError(reason)

def ns(seconds):
    need(type(seconds) in (float,int) and math.isfinite(seconds) and seconds>=0,"STEADY_INVALID")
    return round(seconds*1_000_000_000)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class RawOdomTrace:
    def __init__(self,root,source_sha,run_id):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        need(bool(re.fullmatch("[0-9a-f]{40}",source_sha)) and isinstance(run_id,str) and bool(run_id),"TRACE_ID")
        self.identity=dict(source_sha=source_sha,run_id=run_id,profile=PROFILE)
        self.odom_file=(self.root/"odom_full.jsonl").open("x",buffering=1)
        self.event_file=(self.root/"nav_events.jsonl").open("x",buffering=1)
        self.count=0;self.events=0;self.last_stamp=None

    def odom(self,msg,received):
        # Called at original StopMonitor subscription before any duplicate filtering.
        stamp=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
        lin=msg.twist.twist.linear;ang=msg.twist.twist.angular
        p=msg.pose.pose.position;q=msg.pose.pose.orientation
        self.count+=1
        row=self.identity|dict(seq=self.count,sim_ns=stamp,steady_ns=ns(received),
            frame_id=msg.header.frame_id,child_frame_id=msg.child_frame_id,
            linear=[lin.x,lin.y,lin.z],angular=[ang.x,ang.y,ang.z],
            position=[p.x,p.y,p.z],orientation=[q.x,q.y,q.z,q.w],
            duplicate=stamp==self.last_stamp)
        self.odom_file.write(json.dumps(row,allow_nan=False,separators=(",",":"))+"\n")
        self.last_stamp=stamp

    def nav(self,kind,body,at,extra):
        self.events+=1
        row=self.identity|dict(seq=self.events,kind=kind,steady_ns=ns(at),
            request_id=body["request_id"],leg=body["leg"],goal_uuid=body["goal_uuid"])|extra
        self.event_file.write(json.dumps(row,allow_nan=False,separators=(",",":"))+"\n")

    def close(self):
        self.odom_file.close();self.event_file.close()
        manifest=self.identity|dict(scope="EVERY_RECEIVED_STOP_MONITOR_ODOM_CALLBACK",
            odom_callbacks=self.count,nav_events=self.events,
            odom_sha256=sha(self.root/"odom_full.jsonl"),nav_sha256=sha(self.root/"nav_events.jsonl"))
        (self.root/"odom_manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n")
        return manifest

def rows(path,identity,expected_count):
    out=[]
    with Path(path).open() as stream:
        for i,line in enumerate(stream,1):
            r=json.loads(line)
            need(all(r.get(k)==v for k,v in identity.items()),"SESSION_OR_SOURCE_MISMATCH")
            need(type(r.get("seq")) is int and r["seq"]==i,"TRACE_SEQUENCE_GAP")
            need(type(r.get("steady_ns")) is int and r["steady_ns"]>=0,"TRACE_STEADY_INVALID")
            need(not out or r["steady_ns"]>=out[-1]["steady_ns"],"TRACE_STEADY_REVERSED")
            out.append(r)
    need(len(out)==expected_count and bool(out),"TRACE_COUNT")
    return out

def audit(root,source_sha,run_id):
    root=Path(root)
    m=json.loads((root/"odom_manifest.json").read_text())
    identity=dict(source_sha=source_sha,run_id=run_id,profile=PROFILE)
    need(all(m.get(k)==v for k,v in identity.items()),"SESSION_OR_SOURCE_MISMATCH")
    need(m.get("scope")=="EVERY_RECEIVED_STOP_MONITOR_ODOM_CALLBACK","TRACE_SCOPE")
    need(sha(root/"odom_full.jsonl")==m["odom_sha256"] and sha(root/"nav_events.jsonl")==m["nav_sha256"],"TRACE_SHA")
    data=rows(root/"odom_full.jsonl",identity,m["odom_callbacks"])
    events=rows(root/"nav_events.jsonl",identity,m["nav_events"])
    # Duplicate header cannot renew freshness; conflicting duplicates or epoch rewind fail.
    unique=[]
    for r in data:
        need(type(r.get("sim_ns")) is int and r["sim_ns"]>=0,"ODOM_STAMP")
        need(all(isinstance(r.get(k),list) and len(r[k])==n and all(type(x) in (int,float) and math.isfinite(x) for x in r[k]) for k,n in (("linear",3),("angular",3),("position",3),("orientation",4))),"ODOM_VECTOR")
        if unique and r["sim_ns"]==unique[-1]["sim_ns"]:
            need(r.get("duplicate") is True and all(r[k]==unique[-1][k] for k in ("linear","angular","position","orientation","frame_id","child_frame_id")),"ODOM_DUPLICATE_CONFLICT")
            continue
        need(r.get("duplicate") is False and (not unique or r["sim_ns"]>unique[-1]["sim_ns"] and r["steady_ns"]>unique[-1]["steady_ns"]),"ODOM_EPOCH_REVERSED")
        unique.append(r)
    need(len(events)==9,"NAV_EVENT_COUNT")
    rid=events[0]["request_id"]; seen=set(); result=[]
    for i,leg in enumerate(LEGS):
        acc,term,stop=events[3*i:3*i+3]
        uid=acc["goal_uuid"]
        need(isinstance(uid,str) and re.fullmatch("[0-9a-f]{32}",uid) and uid!="0"*32 and uid not in seen,"GOAL_UUID")
        seen.add(uid)
        need([x["kind"] for x in (acc,term,stop)]==["accepted","terminal","stop_verified"] and all(x["leg"]==leg and x["goal_uuid"]==uid and x["request_id"]==rid for x in (acc,term,stop)),"GOAL_EVENT_ID")
        need(term.get("terminal_status")==stop.get("terminal_status")=="SUCCEEDED","GOAL_TERMINAL")
        start=None;last=None;count=0
        for r in unique:
            t=r["steady_ns"]
            if t<term["steady_ns"]:continue
            if t>stop["steady_ns"]:break
            if last is None or t-last>MAX_GAP_NS:start=None
            if math.hypot(*r["linear"])<=.01 and math.hypot(*r["angular"])<=.02:
                if start is None:start=t
            else:start=None
            last=t;count+=1
        need(start is not None and last is not None and last-start>=DWELL_NS and 0<=stop["steady_ns"]-last<=MAX_GAP_NS,"B_STOP_DWELL_RAW_CONTINUOUS_NOT_PROVEN")
        result.append(dict(leg=leg,goal_uuid=uid,postterminal_samples=count,continuous_stop_s=(last-start)/1e9,last_sample_age_s=(stop["steady_ns"]-last)/1e9))
    return identity|dict(verdict="RAW_STOP_DWELL_REPLAY_PASS",legs=result,received_callbacks=len(data),unique_callbacks=len(unique),scope="RECEIVED_CALLBACK_CONTINUITY_NOT_DDS_PUBLICATION_COMPLETENESS")

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path);p.add_argument("--source-sha",required=True);p.add_argument("--run-id",required=True)
    a=p.parse_args()
    print(json.dumps(audit(a.root,a.source_sha,a.run_id),indent=2))
