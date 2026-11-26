#!/usr/bin/env python3
"""R02-3 opt-in adapter for the preserved A13/A14 RGB(t0) production collector.
Only the actual runtime world gets a metadata observer; no fake contacts.
A14 original candidate remains fail-closed. This entry point is single-trial only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import smartdish_a_tray_live as live
import smartdish_a14_physics as physics
from a14_physics_freshness_contract import evaluate, read_rows, STEP
from a14_production_health_probe import read_ecm
from a14_production_health_contract import pair_set

LIMIT=100000

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_json(path,row):
    Path(path).write_text(json.dumps(row,sort_keys=True,indent=2)+"\n")

def expected_sensors(sdf):
    expected={}
    for model in ET.parse(sdf).getroot().find("./world").findall("model"):
        for link in model.findall("link"):
            for sensor in link.findall("sensor"):
                if sensor.get("type")!="contact": continue
                topic=sensor.findtext("contact/topic")
                if not topic or topic in expected: raise ValueError("R02_3_SENSOR_IDENTITY_INVALID")
                expected[topic]={"model":model.get("name"),"sensor":sensor.get("name"),
                                 "collision":sensor.findtext("contact/collision")}
    if not expected: raise ValueError("R02_3_NO_EXPECTED_SENSORS")
    return expected

def instrument_runtime(runtime, manifest, plugin, directory):
    tree=ET.parse(runtime); world=tree.getroot().find("./world")
    before=ET.tostring(tree.getroot())
    if world.find("./plugin[@name='smartdish::A14ProductionHealth']") is not None:
        raise ValueError("R02_3_DUPLICATE_OBSERVER")
    p=ET.SubElement(world,"plugin",filename=str(plugin),name="smartdish::A14ProductionHealth")
    ET.SubElement(p,"output").text=str((directory/"ecm_contact_steps.tsv").resolve())
    # No late negative controls in the real RGB(t0) collection.
    ET.SubElement(p,"late_control").text="false"
    tree.write(runtime,encoding="utf-8",xml_declaration=True)
    check=ET.parse(runtime); w=check.getroot().find("./world")
    w.remove(w.find("./plugin[@name='smartdish::A14ProductionHealth']"))
    if ET.tostring(check.getroot())!=before: raise ValueError("R02_3_WORLD_MUTATION")
    manifest["sensor_preflight_sha256"]=digest(runtime)
    manifest["r02_3_observer_plugin_sha256"]=digest(plugin)
    write_json(directory/"sensor_preflight_manifest.json",manifest)

def cross_check(expected,rows,raw,start,end):
    by={}
    for row in raw:
        t=row["sim_time_ns"]; topic=row["topic"]
        if not start<t<=end or topic not in expected: continue
        if row["timestamp_source"]!="ROS_CONTACT_HEADER_STAMP":
            raise ValueError("R02_3_INVALID_ROS_CONTACT_STAMP")
        pairs=pair_set({"pairs":[[x["collision1_id"],x["collision2_id"]] for x in row["contacts"]]})
        by.setdefault((topic,t),set()).update(pairs)
    stats={t:{"steps":0,"positive_steps":0,"matched_positive_steps":0,
              "empty_steps":0,"unmatched_positive_steps":0} for t in expected}
    for row in rows:
        t=row["sim_ns"];topic=row["topic"]
        if not start<t<=end: continue
        if topic not in expected or any(row[k]!=v for k,v in expected[topic].items()):
            raise ValueError("R02_3_SDF_IDENTITY_MISMATCH")
        if not row["present"]: raise ValueError("R02_3_MISSING_CONTACT_COMPONENT")
        pairs=pair_set(row)
        if len(row["pairs"])!=row["count"] or any(row["collision_id"] not in p for p in pairs):
            raise ValueError("R02_3_INVALID_ECM_PAIR")
        s=stats[topic];s["steps"]+=1
        if pairs:
            s["positive_steps"]+=1
            if pairs<=by.get((topic,t),set()): s["matched_positive_steps"]+=1
            else: s["unmatched_positive_steps"]+=1
        else: s["empty_steps"]+=1
    passed=(any(s["matched_positive_steps"] for s in stats.values()) and
            all(s["steps"] and (not s["positive_steps"] or s["matched_positive_steps"])
                for s in stats.values()))
    return passed,stats

def install_adapter(plugin):
    """Explicit process-local hooks; baseline files/entry points unchanged."""
    original_split=live.split_scene_for_sensor_warmup
    original_retain=physics.retain_contact_sample
    original_build=physics.build_v2
    def split(sdf):
        runtime,manifest=original_split(sdf)
        instrument_runtime(runtime,manifest,plugin,Path(sdf).parent)
        return runtime,manifest
    def retain(state,row,*args,**kwargs):
        raw=state.setdefault("r02_3_raw_contacts",[])
        if len(raw)>=LIMIT: state["r02_3_raw_overflow"]=True
        else: raw.append(row)
        return original_retain(state,row,*args,**kwargs)
    def build(directory,config,state,topics,source_sha):
        qa=original_build(directory,config,state,topics,source_sha)
        directory=Path(directory)
        raw=state.get("r02_3_raw_contacts",[])
        raw_path=directory/"r02_3_ros_contacts.jsonl"
        raw_path.write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in raw))
        clock_path=directory/"r02_3_clock_samples.json"
        write_json(clock_path,{"samples":state.get("clock_events",[]),
                   "observation_start_ns":state["a14_observation_start_ns"],
                   "observation_end_ns":state["a14_observation_end_ns"],
                   "source":"ROS_CLOCK_CALLBACK_COALESCED_100MS_AND_CAPTURE_BOUNDARIES"})
        report={"schema":1,"source_sha":source_sha,"scene_id":config["scene_id"],
                "scope":"PRODUCTION_RGB_T0_OBSERVATION_SAME_RUN",
                "integration_evidence_pass":False,"production_contact_health":"HOLD",
                "ground_truth":"NOT_OPERATOR_APPROVED","rule_candidate":"UNKNOWN",
                "human_approved":False,"first_error":None,
                "capture_ns":state["a14_capture_ns"],"start_ns":state["a14_observation_start_ns"],
                "end_ns":state["a14_observation_end_ns"],"plugin_sha256":digest(plugin),
                "runtime_world_sha256":digest(directory/"sensor_preflight.sdf"),
                "scenario_sha256":digest(directory/"scenario.sdf"),
                "raw_ros_sha256":digest(raw_path),"clock_samples_sha256":digest(clock_path)}
        try:
            start,end=report["start_ns"],report["end_ns"]
            if not 0<report["capture_ns"]<=start or end-start<10_000_000_000:
                raise ValueError("R02_3_T0_OR_WINDOW_INVALID")
            if state.get("r02_3_raw_overflow") or state.get("a14_contact_overflow"):
                raise ValueError("R02_3_CONTACT_OVERFLOW")
            expected=expected_sensors(directory/"scenario.sdf")
            if set(topics)!=set(expected): raise ValueError("R02_3_TOPIC_SET_MISMATCH")
            path=directory/"ecm_contact_steps.tsv"
            report["ecm_sha256"]=digest(path)
            refresh=evaluate(read_rows(path),list(expected),start,end)
            report["refresh"]=refresh
            rows,overflow=read_ecm(path)
            if overflow: raise ValueError("R02_3_ECM_OVERFLOW")
            ok,stats=cross_check(expected,rows,raw,start,end)
            report["transport"]=stats
            if not refresh["refresh_contract_pass"] or not ok:
                raise ValueError("R02_3_REFRESH_OR_POSITIVE_TRANSPORT_INCOMPLETE")
            report["integration_evidence_pass"]=True
        except Exception as exc:
            report["first_error"]=str(exc)
        report_path=directory/"r02_3_health_result.json"
        write_json(report_path,report)
        # Always keep GT HOLD, even if the legacy rule could suggest a class.
        qa["rule_candidate"]="UNKNOWN";qa["quality_verdict"]="HOLD"
        qa["invalid_reasons"]=sorted(set(qa["invalid_reasons"]+["A14_R02_CONTACT_HEALTH_REVIEW_REQUIRED"]))
        qa["r02_3_integration_evidence_pass"]=report["integration_evidence_pass"]
        qa["evidence_sha256"]["r02_3_health_result"]=digest(report_path)
        write_json(directory/"a14_gt_candidate.json",qa)
        print("R02_3_PRODUCTION_INTEGRATION_EVIDENCE_PASS="+str(report["integration_evidence_pass"]).lower(),flush=True)
        return qa
    live.split_scene_for_sensor_warmup=split
    physics.retain_contact_sample=retain
    physics.build_v2=build
    return original_split,original_retain,original_build

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sha",required=True)
    p.add_argument("--plugin",required=True,type=Path)
    p.add_argument("--scene",choices=("ST-02","UN-01"),required=True)
    p.add_argument("--gui",action="store_true")
    a=p.parse_args()
    plugin=a.plugin.resolve()
    if not plugin.is_file(): p.error("R02_3_PLUGIN_NOT_FOUND")
    originals=install_adapter(plugin)
    try:
        live.run(argparse.Namespace(mode="single",scene=a.scene,seed=211,
                    expected_sha=a.sha,a14_static=True,gui=a.gui))
    finally:
        live.split_scene_for_sensor_warmup,physics.retain_contact_sample,physics.build_v2=originals
if __name__=="__main__":
    main()
