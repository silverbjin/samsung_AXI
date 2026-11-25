#!/usr/bin/env python3
"""A-13 evidence checks only: never turn scenario hints into B ground truth."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

from smartdish_tray_world import TRAY_WIDTH, TRAY_DEPTH


def digest(path: Path):
    path=Path(path)
    h=hashlib.sha256(); count=0
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1<<20),b""):
            h.update(part);count+=len(part)
    return h.hexdigest(),count


def pose_from_transform(trans):
    name=trans.child_frame_id
    if not name:
        return None
    import re
    match=re.search(r"(^|[/:\s])(?P<n>dish_[0-9]{2})(?=$|[/:\s])",name)
    if not match:
        return None
    q=trans.transform.rotation
    p=trans.transform.translation
    vals=(p.x,p.y,p.z,q.x,q.y,q.z,q.w)
    if not all(math.isfinite(float(x)) for x in vals):
        raise ValueError("A13_NONFINITE_PHYSICS_POSE")
    norm=sum(float(x)**2 for x in (q.x,q.y,q.z,q.w))
    if abs(norm-1)>0.08:
        raise ValueError("A13_INVALID_POSE_QUATERNION")
    tilt=math.degrees(math.acos(max(-1.,min(1.,1.-2*(q.x*q.x+q.y*q.y)/norm))))
    return match.group("n"), {"x":round(p.x,5),"y":round(p.y,5),
                              "z":round(p.z,5),"qx":q.x,"qy":q.y,
                              "qz":q.z,"qw":q.w,
                              "tilt_deg":round(tilt,3)}


def classify_motion(initial,final,all_dishes,platform_z):
    if set(initial)!=set(all_dishes) or set(final)!=set(all_dishes):
        raise ValueError("A13_MISSING_PHYSICS_ENTITY")
    rows=[]
    for name in all_dishes:
        a,b=initial[name],final[name]
        dz=a["z"]-b["z"]
        dx=math.hypot(b["x"]-a["x"],b["y"]-a["y"])
        outside=abs(b["x"])>TRAY_WIDTH/2 or abs(b["y"])>TRAY_DEPTH/2
        rows.append({"name":name,"drop_m":round(dz,4),
                     "horizontal_shift_m":round(dx,4),
                     "final_tilt_deg":b["tilt_deg"],
                     "final_center_outside_tray":outside,
                     "final_center_below_tray":b["z"]<platform_z-.08})
    fallen=any(x["drop_m"]>.12 or x["final_center_below_tray"] for x in rows)
    held=all(abs(x["drop_m"])<.08
             and x["horizontal_shift_m"]<.12
             and not x["final_center_outside_tray"]
             and not x["final_center_below_tray"] for x in rows)
    outcome="FALL_OBSERVED" if fallen else "HELD_OBSERVED" if held else "INDETERMINATE"
    return {"observation":outcome,"per_dish":rows,
            "label":"REVIEW_REQUIRED","ground_truth":"NOT_OPERATOR_APPROVED"}


def verify_timing(capture_ns,observation_start_ns,observation_end_ns,
                  captured_pose_ns,distinct_frame_stamps):
    if any(type(x) is not int for x in (capture_ns,observation_start_ns,
                                       observation_end_ns,captured_pose_ns)):
        raise ValueError("A13_TIMESTAMP_INVALID")
    if capture_ns<=0 or capture_ns>observation_start_ns:
        raise ValueError("A13_IMAGE_AFTER_PHYSICS_OBSERVATION")
    if observation_start_ns>=observation_end_ns or observation_end_ns-observation_start_ns<9_000_000_000:
        raise ValueError("A13_PHYSICS_DURATION_TOO_SHORT")
    if abs(captured_pose_ns-capture_ns)>250_000_000:
        raise ValueError("A13_IMAGE_POSE_SYNC_MISSING")
    if len(set(distinct_frame_stamps))<3 or list(distinct_frame_stamps)!=sorted(distinct_frame_stamps):
        raise ValueError("A13_STALE_OR_REORDERED_FRAMES")
    if distinct_frame_stamps[0] > observation_start_ns:
        raise ValueError("A13_CAPTURE_NOT_BEFORE_OBSERVATION")


def verify_trial(trial_dir: Path):
    root=Path(trial_dir)
    required=["tray_rgb.png","capture_metadata.json","initial_state.json",
              "physics_observations.jsonl","final_state.json","trial_summary.json"]
    for name in required:
        p=root/name
        if not p.is_file() or p.stat().st_size<=0:
            raise ValueError("A13_EMPTY_OR_MISSING_EVIDENCE_"+name)
    image=root/"tray_rgb.png"
    physical=root/"physics_observations.jsonl"
    if image.resolve()==physical.resolve():
        raise ValueError("A13_IMAGE_USED_AS_PHYSICS_EVIDENCE")
    capture=json.loads((root/"capture_metadata.json").read_text())
    row=json.loads((root/"trial_summary.json").read_text())
    physics_hash,physics_size=digest(physical)
    image_hash,image_size=digest(image)
    if not image_size or not physics_size:
        raise ValueError("A13_EMPTY_PHYSICS_OR_IMAGE")
    if row.get("physics_sha256")!=physics_hash or row.get("physics_size_bytes")!=physics_size:
        raise ValueError("A13_PHYSICS_SHA_MISMATCH")
    if row.get("image_sha256")!=image_hash:
        raise ValueError("A13_IMAGE_SHA_MISMATCH")
    if capture.get("ground_truth")!="NOT_OBSERVED" or row.get("label")!="REVIEW_REQUIRED":
        raise ValueError("A13_UNAPPROVED_LABEL_LEAK")
    verify_timing(row["capture_stamp_ns"],row["observation_start_ns"],
                  row["observation_end_ns"],row["pose_at_capture_ns"],
                  row["image_stamp_samples"])
    observations=[json.loads(s) for s in physical.read_text().splitlines()]
    if len(observations)<4 or any("pose" not in x or "sim_ns" not in x for x in observations):
        raise ValueError("A13_UNVERIFIED_POSE_TRACE")
    return True


def manifest(dir_path: Path):
    dir_path=Path(dir_path)
    output=[]
    for path in sorted(dir_path.rglob("*")):
        if not path.is_file() or path.name in ("SHA256SUMS","smartdish_a_tray_evidence.tar.gz"):
            continue
        sha,size=digest(path)
        output.append({"path":path.relative_to(dir_path).as_posix(),
                       "sha256":sha,"size_bytes":size})
    return output
