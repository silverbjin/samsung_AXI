"""A product profile: strict internal contracts, not a physical simulator.

All ROS/Gazebo receipts must originate from the actual A runtime. This module
contains no navigation client, fixture publisher or synthetic success path.
"""
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path

PROFILE = "OWNER_PRODUCT_RECOVERY"
FRAME = "smartdish_tray_optical"
COMMON = {"schema_version","profile","request_id","stack_id","transfer_id"}

class ContractError(ValueError):
    pass

def require(ok, reason):
    if not ok: raise ContractError(reason)

def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def finite_number(x):
    return type(x) in (int,float) and math.isfinite(x)

def valid_id(x):
    return isinstance(x,str) and 0<len(x)<=128 and bool(x.strip())

def parse(raw, extra):
    def unique(pairs):
        obj={}
        for k,v in pairs:
            require(k not in obj,"DUPLICATE_JSON_KEY")
            obj[k]=v
        return obj
    def invalid_constant(_):
        raise ContractError("NONFINITE_JSON")
    try:
        obj=json.loads(raw,object_pairs_hook=unique,parse_constant=invalid_constant)
    except (ValueError,TypeError) as exc:
        raise ContractError("INVALID_JSON") from exc
    require(type(obj) is dict and set(obj)==COMMON|extra,"SCHEMA_FIELDS")
    require(type(obj["schema_version"]) is int and obj["schema_version"]==2
            and obj["profile"]==PROFILE,"PROFILE_VERSION")
    for key in ("request_id","stack_id","transfer_id"):
        require(valid_id(obj[key]),"INVALID_"+key.upper())
    return obj

def parse_transfer(raw):
    obj=parse(raw,{"operation","destination_id"})
    require((obj["operation"],obj["destination_id"]) in
            (("LOAD","T03"),("UNLOAD","DISH_RETURN")),"OPERATION_DESTINATION")
    return obj

def parse_capture(raw):
    obj=parse(raw,{"capture_id","min_sim_stamp_ns"})
    require(valid_id(obj["capture_id"]),"INVALID_CAPTURE_ID")
    require(type(obj["min_sim_stamp_ns"]) is int and obj["min_sim_stamp_ns"]>=0,
            "INVALID_MIN_SIM_STAMP")
    return obj

def canonical_rgb(width,height,encoding,step,data):
    require(type(width) is int and type(height) is int and (width,height)==(640,480),
            "FRAME_SIZE")
    require(encoding in ("rgb8","bgr8") and type(step) is int and step>=1920,
            "FRAME_ENCODING_OR_STEP")
    raw=bytes(data)
    require(len(raw)==step*height,"FRAME_STRIDE")
    rgb=b"".join(raw[i*step:i*step+1920] for i in range(height))
    if encoding=="bgr8":
        b=bytearray(rgb)
        b[0::3],b[2::3]=rgb[2::3],rgb[0::3]
        rgb=bytes(b)
    return rgb

@dataclass(frozen=True)
class FrameSample:
    stamp_ns:int
    received_at:float
    frame_id:str
    encoding:str
    rgb:bytes
    rgb_sha256:str

class FrameCache:
    def __init__(self,max_frames=16,freshness_s=2.):
        require(type(max_frames) is int and max_frames>0 and 0<freshness_s<=2.,
                "FRAME_CACHE_CONFIG")
        self.frames=deque(maxlen=max_frames)
        self.freshness=freshness_s
        self.invalid=False

    def observe(self,stamp_ns,frame_id,width,height,encoding,step,data,received_at):
        require(not self.invalid,"FRAME_EPOCH_INVALID")
        require(type(stamp_ns) is int and stamp_ns>0 and frame_id==FRAME
                and finite_number(received_at),"FRAME_ID_OR_STAMP")
        rgb=canonical_rgb(width,height,encoding,step,data)
        h=digest(rgb)
        if self.frames:
            last=self.frames[-1]
            if (stamp_ns<last.stamp_ns or received_at<last.received_at or
                (stamp_ns==last.stamp_ns and h!=last.rgb_sha256)):
                self.invalid=True
                raise ContractError("FRAME_EPOCH_OR_CONFLICT")
            if stamp_ns==last.stamp_ns: return False
        self.frames.append(FrameSample(stamp_ns,received_at,frame_id,encoding,rgb,h))
        return True

    def select(self,min_stamp_ns,now):
        require(not self.invalid,"FRAME_EPOCH_INVALID")
        require(type(min_stamp_ns) is int and min_stamp_ns>=0 and finite_number(now),
                "CAPTURE_TIME_INVALID")
        if self.frames:
            require(now>=self.frames[-1].received_at,"STEADY_CLOCK_REVERSED")
        # Most recent eligible sample; no replacement once capture ID is committed.
        return next((f for f in reversed(self.frames) if f.stamp_ns>min_stamp_ns
                     and 0<=now-f.received_at<=self.freshness),None)

class StopMonitor:
    """Continuous measured odom velocity; steady gap and reset fail closed."""
    def __init__(self,max_gap_s=.3,dwell_s=1.):
        require(0<max_gap_s<=.3 and dwell_s>=1.,"STOP_CONFIG")
        self.max_gap=max_gap_s;self.dwell=dwell_s
        self.last_stamp=None;self.last_at=None;self.start=None;self.invalid=False

    def observe(self,stamp_ns,received_at,linear_mps,angular_radps):
        require(not self.invalid,"ODOM_EPOCH_INVALID")
        require(type(stamp_ns) is int and stamp_ns>=0 and
                all(finite_number(v) for v in (received_at,linear_mps,angular_radps)),
                "ODOM_SAMPLE_INVALID")
        if self.last_stamp is not None and (stamp_ns<=self.last_stamp or received_at<=self.last_at):
            self.invalid=True;self.start=None
            raise ContractError("ODOM_EPOCH_INVALID")
        if self.last_at is not None and received_at-self.last_at>self.max_gap:
            self.start=None
        if abs(linear_mps)<=.01 and abs(angular_radps)<=.02:
            if self.start is None:self.start=received_at
        else:self.start=None
        self.last_stamp,self.last_at=stamp_ns,received_at

    def verified(self,now):
        return (not self.invalid and finite_number(now) and self.start is not None
                and self.last_at is not None and 0<=now-self.last_at<=self.max_gap
                and self.last_at-self.start+1e-9>=self.dwell)

def verify_transfer_observation(request,observation,expected_count):
    """Check actual measured sample values supplied by the trusted A backend.

    Nominal tolerances are provisional; not a physical qualification by itself.
    The caller must also check real service results and stop/nav receipts.
    """
    require(type(expected_count) is int and expected_count>0,"INVALID_DISH_COUNT")
    require(observation.get("stack_id")==request["stack_id"],"STACK_ID_MISMATCH")
    ids=observation.get("entity_ids")
    require(type(ids) is list and len(ids)==expected_count
            and all(type(i) is int and i>0 for i in ids) and len(set(ids))==len(ids),
            "ENTITY_ID_COUNT")
    location="ON_ROBOT" if request["operation"]=="LOAD" else "RETURNED"
    tray=expected_count if location=="ON_ROBOT" else 0
    require(observation.get("location")==location and
            type(observation.get("table_count")) is int and observation["table_count"]==0
            and type(observation.get("tray_count")) is int and observation["tray_count"]==tray,
            "LOCATION_COUNT")
    samples=observation.get("samples")
    require(type(samples) is list and len(samples)>=3,"POSE_SAMPLE_COUNT")
    last=None;first=None
    for sample in samples:
        stamp=sample.get("sim_ns")
        require(type(stamp) is int and stamp>=0 and (last is None or stamp>last),
                "POSE_STAMP_ORDER")
        if first is None:first=stamp
        last=stamp
        require(sample.get("entity_ids")==ids,"POSE_ID_DRIFT")
        for key,limit in (("relative_xy_m",.015),("relative_z_error_m",.02),
                          ("relative_speed_mps",.02)):
            values=sample.get(key)
            require(type(values) is list and len(values)==expected_count and
                    all(finite_number(x) and abs(x)<=limit for x in values),
                    "POSE_OR_SPEED_"+key.upper())
    require(last-first>=10**9 and observation.get("event_sim_ns")==last,
            "POSE_DWELL_OR_EVENT")
    return True

class TransactionJournal:
    """Persist pending before side effects; crash/failed result requires manual recovery.

    Only one A-owned controller may call the physical backend. File lock
    serializes ledger writers, not Gazebo's external service calls.
    """
    def __init__(self,root):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"transfer_journal.json"
        self.lockpath=self.root/"transfer_journal.lock"

    @contextmanager
    def _lock(self):
        with self.lockpath.open("a+b") as f:
            fcntl.flock(f,fcntl.LOCK_EX)
            yield

    def _read(self):
        if not self.path.exists():return {"locked":False,"entries":{}}
        data=json.loads(self.path.read_text())
        require(type(data) is dict and type(data.get("locked")) is bool
                and type(data.get("entries")) is dict,"JOURNAL_CORRUPT")
        return data

    def _write(self,data):
        tmp=self.path.with_suffix(".tmp")
        with tmp.open("wb") as f:
            f.write(canonical_json(data));f.flush();os.fsync(f.fileno())
        os.replace(tmp,self.path)
        fd=os.open(self.root,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    @property
    def locked(self):
        with self._lock():return self._read()["locked"]

    def begin(self,request):
        request=parse_transfer(canonical_json(request))
        key=request["transfer_id"]
        with self._lock():
            d=self._read()
            old=d["entries"].get(key)
            if old:
                require(old["request"]==request,"TRANSFER_ID_CONFLICT")
                require(old["state"]!="PENDING","TRANSFER_PENDING_RECOVERY_REQUIRED")
                return old["result"]
            require(not d["locked"],"TRANSFER_LOCKED")
            d["entries"][key]={"state":"PENDING","request":request}
            d["locked"]=True
            self._write(d)
            return None

    def finish(self,request,result,evidence=None):
        request=parse_transfer(canonical_json(request))
        key=request["transfer_id"]
        with self._lock():
            d=self._read();entry=d["entries"].get(key)
            require(entry is not None and entry["state"]=="PENDING"
                    and entry["request"]==request,"NO_PENDING_TRANSFER")
            require(all(result.get(k)==request[k] for k in COMMON|{"operation"}),
                    "TRANSFER_RESULT_ID_MISMATCH")
            require(result.get("status") in ("ACK","FAILED") and "receipt_sha256" not in result,
                    "TRANSFER_RESULT_INVALID")
            raw=canonical_json(result if evidence is None else {"result":result,"evidence":evidence});h=digest(raw)
            receipt=self.root/(h+".json")
            if receipt.exists():
                require(receipt.read_bytes()==raw,"RECEIPT_COLLISION")
            else:
                with receipt.open("xb") as f:
                    f.write(raw);f.flush();os.fsync(f.fileno())
            entry.update(state=result["status"],result=dict(result,receipt_sha256=h))
            d["locked"]=result["status"]!="ACK"
            self._write(d)
            return entry["result"]

    def load_receipt(self,request_id,stack_id,transfer_id,require_actual=True):
        """Read a committed LOAD receipt; never trust a DDS ACK alone."""
        with self._lock():
            d=self._read()
            e=d["entries"].get(transfer_id)
            require(not d["locked"] and e is not None and e["state"]=="ACK",
                    "LOAD_RECEIPT_NOT_READY")
            p=e["request"];r=e["result"]
            require(p["operation"]=="LOAD" and p["request_id"]==request_id
                    and p["stack_id"]==stack_id and r["location"]=="ON_ROBOT",
                    "LOAD_RECEIPT_ID_MISMATCH")
            require(not any(x["request"]["operation"]=="UNLOAD" and
                            x["request"]["request_id"]==request_id for x in d["entries"].values()),
                    "UNLOAD_ALREADY_STARTED")
            h=r["receipt_sha256"]
            require(isinstance(h,str) and len(h)==64 and all(c in "0123456789abcdef" for c in h),
                    "RECEIPT_HASH_INVALID")
            raw=(self.root/(h+".json")).read_bytes()
            require(digest(raw)==h,"RECEIPT_HASH_MISMATCH")
            receipt=json.loads(raw)
            if require_actual:
                require(receipt.get("result")=={k:v for k,v in r.items() if k!="receipt_sha256"}
                        and receipt.get("evidence",{}).get("kind")=="ACTUAL_NAV2_TERMINAL_AND_GAZEBO_LOAD",
                        "LOAD_RECEIPT_SCOPE")
            return r,receipt
