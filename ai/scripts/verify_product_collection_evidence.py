#!/usr/bin/env python3
"""B-only, read-only evidence QA. Candidate interchange, not an approved A/E schema."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
import re
import sys
import tarfile
from pathlib import Path, PurePosixPath
from PIL import Image

PROFILE = "OWNER_PRODUCT_RECOVERY"
FILES = {"evidence.json", "manifest.json", "frame.png", "frame.rgb",
         "c_input.rgb", "load.json", "capture.json", "inference.json", "unload.json"}
HEX = re.compile(r"[0-9a-f]{64}")
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024

class QAError(ValueError):
    pass

def need(ok, code):
    if not ok:
        raise QAError(code)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def unique_pairs(pairs):
    out = {}
    for k, v in pairs:
        need(k not in out, "B_JSON_DUPLICATE_KEY")
        out[k] = v
    return out

def reject_constant(_):
    raise QAError("B_NONFINITE")

def decode(data):
    return json.loads(data, object_pairs_hook=unique_pairs, parse_constant=reject_constant)

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def id_ok(v):
    return isinstance(v, str) and 0 < len(v) <= 128 and v.strip() == v

def number(v):
    return type(v) in (int, float) and math.isfinite(v)

def stamp(v):
    return type(v) is int and v > 0

def vector(v, n):
    need(isinstance(v,list) and len(v)==n and all(number(x) for x in v), "B_POSE_FORMAT")
    return v

def safe_path(name):
    p = PurePosixPath(name)
    return bool(name and not p.is_absolute() and p.as_posix()==name and
                all(x not in ("", ".", "..") for x in name.split("/")) and
                not any(x in name for x in ("\\", ":", "\x00")))

def bounded_read(path, limit):
    need(path.is_file() and not path.is_symlink(), "B_INPUT_MISSING_OR_LINK")
    with path.open("rb") as f:
        data = f.read(limit+1)
    need(len(data)<=limit, "B_SIZE_LIMIT")
    return data

def read_archive(archive, sidecar):
    need("test4" not in archive.name.lower() and "test4" not in sidecar.name.lower(),
         "B_PROTECTED_INPUT")
    blob = bounded_read(archive, MAX_ARCHIVE)
    sha = digest(blob)
    side = bounded_read(sidecar, 1024).decode("utf-8").rstrip("\n")
    need(side in (sha+"  "+archive.name, sha+" *"+archive.name), "B_ARCHIVE_SHA")
    files, total = {}, 0
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for member in tar:
            name = member.name
            need(safe_path(name), "B_ARCHIVE_PATH")
            need(name not in files, "B_ARCHIVE_DUPLICATE")
            need(member.isfile() and not member.issparse(), "B_ARCHIVE_TYPE")
            need(name in FILES, "B_ARCHIVE_UNAPPROVED_MEMBER")
            total += member.size
            need(0 <= member.size <= MAX_FILE and total <= MAX_TOTAL, "B_SIZE_LIMIT")
            reader = tar.extractfile(member)
            need(reader is not None, "B_ARCHIVE_READ")
            body = reader.read(member.size+1)
            need(len(body)==member.size, "B_FILE_SIZE")
            files[name] = body
    need(set(files)==FILES, "B_FILE_SET")
    index = decode(files["manifest.json"])
    need(isinstance(index,dict) and set(index)==FILES-{"manifest.json"}, "B_INDEX_SET")
    for name in sorted(index):
        item = index[name]
        need(type(item["size_bytes"]) is int and item["size_bytes"]==len(files[name]), "B_FILE_SIZE")
        need(item["sha256"]==digest(files[name]), "B_FILE_HASH")
    return sha, files

def distance(a,b):
    return math.dist(a,b)

def relative(tray, q, dish):
    # Inverse rotation of world delta by unit quaternion; no declared local coordinates trusted.
    x,y,z,w = vector(q,4)
    need(abs(x*x+y*y+z*z+w*w-1)<=1e-6, "B_TRAY_QUATERNION")
    u = [-x,-y,-z]
    v = [a-b for a,b in zip(vector(dish,3),vector(tray,3))]
    def cross(a,b):
        return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    t = [2*a for a in cross(u,v)]
    return [a+w*b+c for a,b,c in zip(v,t,cross(u,t))]

def verify(m, f, expected):
    need(re.fullmatch(r"[0-9a-f]{40}",expected) and m["source_sha"]==expected, "B_SOURCE_SHA")
    need(type(m["schema_version"]) is int and m["schema_version"]==2 and
         m["profile"]==PROFILE and m["world_id"]=="restaurant", "B_PROFILE")
    need(all(id_ok(m[k]) for k in ("request_id","stack_id","run_id")), "B_ID_FORMAT")
    need(m["scope"] in ("SYNTHETIC_FIXTURE","ACTUAL_PRODUCT_CANDIDATE"), "B_SCOPE")
    need(m["evidence_class"]=="INTEGRATION_EVIDENCE_ONLY", "B_LABEL_POLICY")
    need(m["license_status"]=="OWNED", "B_RIGHTS_MISSING")
    need(m["label"] is None and m["ground_truth"]=="NOT_OPERATOR_APPROVED", "B_LABEL_POLICY")
    need(m["camera_mount"]=="ROBOT" and type(m["camera_publishers"]) is int and
         m["camera_publishers"]==1 and type(m["clock_publishers"]) is int and
         m["clock_publishers"]==1, "B_CAMERA_SOURCE")
    entities=m["entity_ids"]
    need(isinstance(entities,list) and entities and all(id_ok(i) for i in entities)
         and len(entities)==len(set(entities)), "B_ENTITY_SET")
    load, cap, c, unload = (m[k] for k in ("load","capture","inference","unload"))
    for name,receipt in zip(("load","capture","inference","unload"),(load,cap,c,unload)):
        need(f[name+".json"]==canonical(receipt), "B_RECEIPT_BYTES")
        need(all(type(receipt[k]) is type(m[k]) and receipt[k]==m[k]
                 for k in ("schema_version","profile","request_id","stack_id")), "B_ID_MISMATCH")
    for receipt, op, location, count in ((load,"LOAD","ON_ROBOT",len(entities)),
                                         (unload,"UNLOAD","RETURNED",0)):
        need(receipt["operation"]==op and receipt["status"]=="ACK" and
             receipt["location"]==location and receipt["entity_ids"]==entities and
             type(receipt["tray_count"]) is int and receipt["tray_count"]==count and
             type(receipt["table_count"]) is int and receipt["table_count"]==0, "B_TRANSFER")
    need(id_ok(load["transfer_id"]) and id_ok(unload["transfer_id"]) and
         load["transfer_id"]!=unload["transfer_id"], "B_TRANSFER_ID")
    need(id_ok(cap["capture_id"]) and cap["transfer_id"]==load["transfer_id"] and
         c["transfer_id"]==load["transfer_id"] and c["capture_id"]==cap["capture_id"], "B_ID_MISMATCH")
    tl,tf,ti,tu=(load["event_sim_ns"],cap["image_stamp_ns"],c["inference_sim_ns"],unload["event_sim_ns"])
    need(all(stamp(t) for t in (tl,tf,ti,tu)) and tl<tf<=ti<tu, "B_TIME_ORDER")
    causal=m["causal_monotonic_ns"]
    need(isinstance(causal,list) and len(causal)==5 and all(stamp(t) for t in causal)
         and all(a<b for a,b in zip(causal,causal[1:])), "B_CAUSAL_ORDER")
    recv, infer=m["frame_received_monotonic_ns"],m["inference_received_monotonic_ns"]
    need(stamp(recv) and stamp(infer) and 0<=infer-recv<=2_000_000_000, "B_FRESHNESS")
    need(recv==causal[1] and infer==causal[2], "B_CAUSAL_ORDER")
    need(cap["status"]=="ACK" and cap["frame_id"]=="smartdish_tray_optical" and
         cap["width"]==640 and cap["height"]==480 and cap["encoding"] in ("rgb8","bgr8"), "B_FRAME")
    raw=f["frame.rgb"]
    need(len(raw)==640*480*3 and cap["rgb_sha256"]==digest(raw), "B_RGB_HASH")
    need(m["png_sha256"]==digest(f["frame.png"]), "B_PNG_HASH")
    with Image.open(io.BytesIO(f["frame.png"])) as im:
        need(im.format=="PNG" and im.mode=="RGB" and im.size==(640,480), "B_PNG_FORMAT")
        need(im.tobytes()==raw, "B_PNG_RGB_MISMATCH")
    need(c["image_stamp_ns"]==tf and c["frame_id"]==cap["frame_id"] and
         c["rgb_sha256"]==digest(raw) and f["c_input.rgb"]==raw, "B_C_INPUT_HASH")
    need(type(c["calls"]) is int and c["calls"]==1, "B_INFERENCE_COUNT")
    need(c["inference_ok"] is True and c["status"] in ("STABLE","UNSTABLE","UNKNOWN") and
         c["raw_status"] in ("STABLE","UNSTABLE") and id_ok(c["model_version"]), "B_INFERENCE")
    for key in ("raw_confidence","stable_confidence_min","unstable_confidence_min"):
        need(number(c[key]) and 0<=c[key]<=1, "B_INFERENCE_CONFIDENCE")
    threshold=c["stable_confidence_min" if c["raw_status"]=="STABLE" else "unstable_confidence_min"]
    status=c["raw_status"] if c["raw_confidence"]>=threshold else "UNKNOWN"
    need(c["status"]==status, "B_INFERENCE_THRESHOLD")
    if status!="UNKNOWN":
        need(number(c["confidence"]) and c["confidence"]==c["raw_confidence"], "B_INFERENCE_CONFIDENCE")
    poses=m["poses"]
    need(isinstance(poses,list) and len(poses)>=6 and len(poses)<=10000, "B_POSE_COUNT")
    ts=[p["sim_ns"] for p in poses]
    need(all(stamp(t) for t in ts) and all(a<b for a,b in zip(ts,ts[1:])), "B_POSE_TIME")
    need(ts[0]<tl and tl in ts and tf in ts and ts[-1]==tu, "B_POSE_COVERAGE")
    for p in poses:
        need(set(p["entities"])==set(entities), "B_ENTITY_SET")
        for dish in entities:
            relative(p["tray_xyz"],p["tray_xyzw"],p["entities"][dish])
    loaded=[p for p in poses if tl<=p["sim_ns"]<tu]
    need(len(loaded)>=4, "B_POSE_COVERAGE")
    first,last=loaded[0],loaded[-1]
    need(distance(first["tray_xyz"],last["tray_xyz"])>.25, "B_TRAY_NOT_MOVED")
    for dish in entities:
        initial,final=poses[0]["entities"][dish],poses[-1]["entities"][dish]
        base=relative(first["tray_xyz"],first["tray_xyzw"],first["entities"][dish])
        # Fixture tolerances only; E must approve actual geometry/timing.
        need(abs(base[0])<=.25 and abs(base[1])<=.25 and 0<=base[2]<=.35, "B_TRAY_BOUNDS")
        need(distance(initial,first["entities"][dish])>.25 and
             distance(last["entities"][dish],final)>.25, "B_DISH_NOT_MOVED")
        for p in loaded:
            loc=relative(p["tray_xyz"],p["tray_xyzw"],p["entities"][dish])
            need(distance(base,loc)<=.05, "B_TRAY_RELATIVE")
        need(distance(first["entities"][dish],last["entities"][dish])>.25, "B_DISH_NOT_MOVED")
    nav=m["nav"]
    need(isinstance(nav,list) and [n["leg"] for n in nav]==["TO_TABLE","TO_RETURN","TO_HOME"], "B_NAV_LEGS")
    uuids=[n["goal_uuid"] for n in nav]
    need(all(isinstance(u,str) and re.fullmatch(r"[0-9a-f]{32}",u) and int(u,16)>0 for u in uuids)
         and len(set(uuids))==3, "B_NAV_UUID")
    approval=m["approval_sim_ns"]
    need(stamp(approval) and ti<=approval<nav[1]["start_sim_ns"] and
         nav[0]["end_sim_ns"]<tl and nav[1]["end_sim_ns"]<tu<nav[2]["start_sim_ns"], "B_NAV_CAUSAL")
    for n in nav:
        a,z=n["start_sim_ns"],n["end_sim_ns"]
        need(stamp(a) and stamp(z) and a<z and n["request_id"]==m["request_id"] and
             n["terminal_status"]=="SUCCEEDED" and n["stop_verified"] is True, "B_NAV_TERMINAL")
        od=n["odom"]; scans=n["scan_stamps_ns"]
        ost=[v["sim_ns"] for v in od]
        for times in (ost,scans):
            need(len(times)>=3 and all(stamp(t) and a<=t<=z for t in times) and
                 all(x<y for x,y in zip(times,times[1:])), "B_NAV_SAMPLES")
        need(all(number(v[k]) for v in od for k in ("x","y")), "B_NAV_ODOM")
        need(math.hypot(od[-1]["x"]-od[0]["x"],od[-1]["y"]-od[0]["y"])>.25, "B_NAV_ODOM")

def audit(archive, sidecar, expected_source_sha):
    out={"qa_schema_version":1,"verdict":"FAIL","scope":"UNVERIFIED",
         "first_error":None,"training_allowed":False,"product_accepted":False,
         "evidence_class":"INTEGRATION_EVIDENCE_ONLY","archive_sha256":None,
         "source_sha":None,"run_id":None}
    try:
        sha,files=read_archive(Path(archive),Path(sidecar))
        out["archive_sha256"]=sha
        m=decode(files["evidence.json"])
        verify(m,files,expected_source_sha)
        out.update(scope=m["scope"],source_sha=m["source_sha"],run_id=m["run_id"])
        if m["scope"]=="SYNTHETIC_FIXTURE":
            out["verdict"]="PASS"
        else:
            out.update(verdict="HOLD",first_error="B_ACTUAL_SCHEMA_REVIEW_REQUIRED")
    except QAError as e:
        out["first_error"]=str(e)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,OverflowError,
            IndexError,tarfile.TarError,EOFError,Image.DecompressionBombError):
        out["first_error"]="B_MALFORMED_OR_MISSING_EVIDENCE"
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--sidecar",required=True,type=Path)
    p.add_argument("--source-sha",required=True)
    a=p.parse_args()
    out=audit(a.archive,a.sidecar,a.source_sha)
    print(json.dumps(out,sort_keys=True,allow_nan=False))
    return {"PASS":0,"HOLD":2,"FAIL":1}[out["verdict"]]

if __name__=="__main__":
    sys.exit(main())
