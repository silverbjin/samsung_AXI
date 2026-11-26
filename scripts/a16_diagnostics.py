"""A16 independent native vs ROS contact subscriber diagnostic, NOT loss rate."""
import csv
from collections import Counter,defaultdict
from pathlib import Path
from a16_pilot_contract import need
def pair(a,b):return tuple(sorted((int(a),int(b))))
def load_native(path):
    rows=[]
    with Path(path).open() as f:
        for r in csv.DictReader(f,delimiter="\t"):
            need(r["topic"]!="OVERFLOW" and len(rows)<150000,"A16_NATIVE_OVERFLOW")
            rows.append(dict(topic=r["topic"],sim_time_ns=int(r["sim_ns"]),receive_monotonic_ns=int(r["receive_monotonic_ns"]),pairs=[pair(*x.split(":")) for x in r["pairs"].split(";") if x]))
    return rows
def registration(path,ecm,meta,trigger):
    with Path(path).open() as f:rows=list(csv.DictReader(f,delimiter="\t"))
    by={int(r["entity_id"]):r for r in rows}
    need(len(by)==len(rows) and all(int(r["sim_ns"])==meta["t0_ns"] for r in rows),"A16_REGISTRY_ID_TIME")
    def parent(r):return by[int(r["parent_id"])]
    mappings={}
    for r in ecm:
        if r["sim_ns"]!=meta["t0_ns"]:continue
        s,c=by[r["sensor_id"]],by[r["collision_id"]]
        l=parent(s);m=parent(l)
        need(s["kind"]=="contact_sensor" and c["kind"]=="collision" and parent(c)==l and l["kind"]=="link" and m["kind"]=="model" and m["name"]==r["model"] and s["name"]==r["sensor"] and c["name"]==r["collision"],"A16_REGISTRY_MAPPING")
        need(r["topic"] not in mappings,"A16_REGISTRY_TOPIC_DUPLICATE")
        mappings[r["topic"]]={"sensor_id":r["sensor_id"],"collision_id":r["collision_id"],"link_id":int(l["entity_id"]),"model":m["name"],"model_id":int(m["entity_id"])}
    need(set(mappings)==set(meta["contact_topics"]),"A16_REGISTRY_TOPIC_SET")
    target=by[trigger["target_link_id"]]
    need(target["kind"]=="link" and target["name"]=="body" and parent(target)["name"]==meta["initial_dishes"][-1]["name"],"A16_TRIGGER_LINK_MAPPING")
    return {"ecm_entity_registration_verified":True,"engine_geometry_registration_proven":False,"mappings":mappings}
def transport_diagnostic(ecm,raw,native,topics,start,end):
    def normalize(rows,is_ros):
        groups=defaultdict(list)
        for r in rows:
            t=r["sim_time_ns"]
            if r["topic"] not in topics or not start<t<=end:continue
            ps=[pair(x["collision1_id"],x["collision2_id"]) for x in r["contacts"]] if is_ros else r["pairs"]
            groups[r["topic"]].append((t,tuple(sorted(set(ps))),r["receive_monotonic_ns"]))
        return groups
    a,b=normalize(native,False),normalize(raw,True)
    def describe(rows):
        counts=Counter((t,p) for t,p,_ in rows)
        return {"callbacks":len(rows),"positive_callbacks":sum(bool(p) for _,p,_ in rows),"empty_callbacks":sum(not p for _,p,_ in rows),"duplicate_stamp_pair_callbacks":sum(n-1 for n in counts.values()),"out_of_order_sim_stamp":sum(y[0]<x[0] for x,y in zip(rows,rows[1:])),"receipt_monotonic_reversal":sum(y[2]<x[2] for x,y in zip(rows,rows[1:]))},counts
    results={}
    for topic in topics:
        n,nc=describe(a[topic]);r,rc=describe(b[topic])
        e=[x for x in ecm if x["topic"]==topic and start<x["sim_ns"]<=end]
        positive=sum(bool(x["pairs"]) for x in e)
        results[topic]={"ecm_positive_steps":positive,"ecm_empty_steps":len(e)-positive,"native":n,"ros":r,"native_observed_not_ros_observed":sum((nc-rc).values()),"ros_observed_not_native_observed":sum((rc-nc).values()),"observed_exact_stamp_pair_multiset_intersection":sum((nc&rc).values()),"silent_ros":not r["callbacks"],"silent_native":not n["callbacks"],"negative_control_scope":"ECM_EMPTY_OBSERVATION_NOT_INFERRED_FROM_SILENCE" if not positive else "MIXED_OR_POSITIVE"}
    return {"scope":"TWO_INDEPENDENT_SUBSCRIBERS_NOT_PUBLISHER_SEQUENCE_OR_LOSS_RATE","topics":results,"full_delivery_proven":False,"engine_geometry_registration_proven":False,"production_contact_health":"HOLD","clock_scope":"SIM_HEADER_VS_LOCAL_MONOTONIC_RECEIPT_NO_WALL_LATENCY_INFERENCE"}
