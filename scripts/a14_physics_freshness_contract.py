"""R02-2: validate per-step change-state challenge, not GT."""
import csv
from collections import defaultdict
from pathlib import Path

STEP=1_000_000
MAX_ROWS=100000

def evaluate(rows, topics, start, end, *, diagnostic=False):
    """Open-left interval (start,end], exact 1ms grid; no missing/duplicate steps."""
    expected=list(range(start+STEP,end+1,STEP))
    if not topics or start<0 or end<=start or (end-start)%STEP or len(expected)>MAX_ROWS:
        raise ValueError("R02_FRESHNESS_WINDOW_INVALID")
    by=defaultdict(list)
    for row in rows:
        if start<row["sim_ns"]<=end:
            by[row["topic"]].append(row)
    result={}
    for topic in topics:
        seq=by[topic]
        ids={(r["sensor_id"],r["collision_id"]) for r in seq}
        valid=(len(ids)==1 and all(i>0 for pair in ids for i in pair)
               and [r["sim_ns"] for r in seq]==expected
               and all(r["present"] and r["armed"] and r["dt_ns"]==STEP for r in seq)
               and all(b["iteration"]==a["iteration"]+1 for a,b in zip(seq,seq[1:])))
        controls=[r for r in seq if r["late_control"]]
        normal=[r for r in seq if not r["late_control"]]
        positives=sum(r["post_state"] in ("NO_CHANGE","PERIODIC") for r in normal)
        control_ok=all(r["post_state"]=="ONE_TIME" for r in controls)
        mode_ok=(bool(controls) and control_ok) if diagnostic else not controls
        passed=valid and bool(normal) and positives==len(normal) and mode_ok
        result[topic]={"pass":passed,"steps":len(seq),"expected":len(expected),
                       "normal_refresh_steps":positives,"late_negative_steps":len(controls),
                       "late_negative_detected":control_ok if controls else None,
                       "ids":[list(p) for p in sorted(ids)]}
    return {"refresh_contract_pass":all(r["pass"] for r in result.values()) and set(by)==set(topics),
            "scope":"PHYSICS_CONTACT_COMPONENT_STATE_REFRESH_ONLY",
            "diagnostic_mode":diagnostic,"start_ns":start,"end_ns":end,"sensors":result,
            "engine_geometry_registration_proven":False,"ros_full_delivery_proven":False,
            "production_contact_health":"HOLD","rule_candidate":"UNKNOWN","human_approved":False,
            "ground_truth":"NOT_OPERATOR_APPROVED"}

def read_rows(path):
    rows=[]
    with Path(path).open() as f:
        for r in csv.DictReader(f,delimiter="\t"):
            if len(rows)>=MAX_ROWS or r["sim_ns"]=="OVERFLOW":
                raise ValueError("R02_FRESHNESS_OVERFLOW")
            row={k:int(r[k]) for k in ("sim_ns","iteration","dt_ns","sensor_id","collision_id")}
            row.update(topic=r["topic"],post_state=r["post_state"])
            for k in ("present","armed","late_control"):
                if r[k] not in ("0","1"): raise ValueError("R02_FRESHNESS_INVALID_FLAG")
                row[k]=r[k]=="1"
            rows.append(row)
    return rows
