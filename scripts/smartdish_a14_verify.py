#!/usr/bin/env python3
"""A14 review-only QA for one REAL A13 opt-in trial; no label approvals."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

NEEDED=("tray_rgb.png","capture_metadata.json","scenario.sdf",
        "scenario.scenario.json","geometry_layout.json",
        "physics_observations.jsonl","physics_observations_v2.jsonl",
        "tray_pose_timeline.jsonl","contact_events.jsonl",
        "contact_sensor_status.json","a14_gt_candidate.json",
        "trial_summary.json")

def filehash(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def verify_trial(directory:Path,sha:str):
    if not re.fullmatch("[0-9a-f]{40}",sha):
        raise RuntimeError("A14_SOURCE_SHA_FORMAT_INVALID")
    directory=Path(directory)
    for name in NEEDED:
        p=directory/name
        if not p.is_file() or p.is_symlink():
            raise RuntimeError("A14_REQUIRED_EVIDENCE_MISSING_"+name)
    qa=json.loads((directory/"a14_gt_candidate.json").read_text())
    summary=json.loads((directory/"trial_summary.json").read_text())
    layout=json.loads((directory/"geometry_layout.json").read_text())
    if qa.get("source_sha")!=sha or summary.get("source_sha")!=sha:
        raise RuntimeError("A14_SOURCE_SHA_MISMATCH")
    if qa.get("physics_profile")!="STATIC_GRAVITY" or layout.get("physics_profile")!="STATIC_GRAVITY":
        raise RuntimeError("A14_PHYSICS_PROFILE_NOT_SUPPORTED")
    if (qa.get("human_approved") is not False or
        qa.get("ground_truth")!="NOT_OPERATOR_APPROVED" or
        qa.get("label_status")!="REVIEW_REQUIRED" or
        (directory/"approval_ledger.jsonl").exists()):
        raise RuntimeError("A14_HUMAN_GT_BOUNDARY_VIOLATION")
    if qa["world_sdf_sha256"]!=filehash(directory/"scenario.sdf"):
        raise RuntimeError("A14_SDF_SOURCE_SHA_MISMATCH")
    original=directory/"physics_observations.jsonl"
    if qa["original_a13_physics_sha256"]!=filehash(original):
        raise RuntimeError("A14_ORIGINAL_PHYSICS_SHA_MISMATCH")
    if qa["rgb_image_sha256"]!=filehash(directory/"tray_rgb.png"):
        raise RuntimeError("A14_ORIGINAL_RGB_SHA_MISMATCH")
    for name,path in (
        ("tray_pose_timeline","tray_pose_timeline.jsonl"),
        ("physics_observations_v2","physics_observations_v2.jsonl"),
        ("contact_events","contact_events.jsonl")):
        if qa["evidence_sha256"].get(name)!=filehash(directory/path):
            raise RuntimeError("A14_TRACE_SHA_MISMATCH_"+name)
    trace=[json.loads(x) for x in (directory/"physics_observations_v2.jsonl").read_text().splitlines()]
    relative=bool(trace) and all(
        x["world_frame_id"]=="world" and x["tray_frame_id"]=="tray_platform/body" and
        x["transform_mode"]=="DYNAMIC_DISH_VS_STATIC_TRAY" and
        x["relative"]["quaternion_norm"]>.98 for x in trace)
    velocity=relative and all(
        x["velocity"]["provenance"] in (
            "UNAVAILABLE_FIRST_SAMPLE","DERIVED_POSE_FINITE_DIFFERENCE")
        for x in trace)
    aligned=relative and all(
        x["sim_time_ns"]>0 and x["stamp_source"]=="ROS_TF_HEADER_STAMP"
        for x in trace)
    contact=qa["contact_status"]
    qc={
        "A14_SOURCE_SHA_PASS":True,
        "A14_TRAY_RELATIVE_POSE_PASS":relative,
        "A14_VELOCITY_PROVENANCE_PASS":velocity,
        "A14_CONTACT_EVIDENCE_PASS":contact in ("CONTACT_OBSERVED","NO_CONTACT_OBSERVED"),
        "A14_TIME_ALIGNMENT_PASS":aligned and not any(
            r.startswith(("A14_POSE_GAP","A14_T0_POSE","A14_TRACE_TRUNCATED",
                          "A14_TIME_REPEATED","A14_SHORT_OBSERVATION"))
            for r in qa["invalid_reasons"]),
        "A14_PHYSICS_TRACE_INTEGRITY_PASS":True,
        "A14_GT_CANDIDATE_REVIEW_REQUIRED":True,
    }
    # QA field is review-only. Distinguish a valid UNKNOWN for boundary cases
    # from missing sensor evidence. Fail-closed on a material contract break.
    overall="PASS" if (all(qc.values()) and qa["quality_verdict"]=="PASS") else "HOLD"
    return {"schema":2,"source_sha":sha,"scene_id":qa["scene_id"],
            "gt_candidate":qa["rule_candidate"],
            "human_approved":False,
            "quality_verdict":overall,"contact_status":contact,
            "checks":qc,"invalid_reasons":qa["invalid_reasons"],
            "dataset_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--trial",type=Path,required=True)
    p.add_argument("--sha",required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    try:
        row=verify_trial(a.trial,a.sha)
    except Exception as exc:
        row={"source_sha":a.sha,"quality_verdict":"HOLD",
             "first_error":str(exc),"human_approved":False}
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(row,sort_keys=True,indent=2)+"\n")
    for k,v in row.get("checks",{}).items():
        print(k if v else k.replace("_PASS","_HOLD"),flush=True)
    print("A14_GT_CANDIDATE_REVIEW_REQUIRED" if row.get("gt_candidate")
          else "A14_CANDIDATE_HOLD",flush=True)
    print("A14_QA_STATUS="+row["quality_verdict"],flush=True)
    if row["quality_verdict"]!="PASS":
        print("A14_FIRST_FAILURE="+json.dumps(row.get("invalid_reasons",row.get("first_error"))),
              file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    sys.exit(main())
