"""Synthetic contract tests only; no dataset or real product claim."""
import copy
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from ai.scripts.verify_product_collection_evidence import audit

SHA = "a" * 40
def h(b):
    return hashlib.sha256(b).hexdigest()
def j(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def fixture():
    ids = dict(schema_version=2, profile="OWNER_PRODUCT_RECOVERY",
               request_id="request-1", stack_id="stack-1")
    raw = bytes([10, 20, 30]) * (640 * 480)
    buf = io.BytesIO()
    Image.frombytes("RGB", (640, 480), raw).save(buf, format="PNG")
    png = buf.getvalue()
    def transfer(op, tid, stamp, loc, tray, table):
        return dict(ids, operation=op, transfer_id=tid, status="ACK", reason="OK",
                    event_sim_ns=stamp, entity_ids=["dish-1"], location=loc,
                    tray_count=tray, table_count=table)
    load = transfer("LOAD", "load-1", 12_000_000_000, "ON_ROBOT", 1, 0)
    unload = transfer("UNLOAD", "unload-1", 23_000_000_000, "RETURNED", 0, 0)
    cap = dict(ids, transfer_id="load-1", capture_id="capture-1", status="ACK",
               reason="OK", image_stamp_ns=13_000_000_000,
               frame_id="smartdish_tray_optical", rgb_sha256=h(raw),
               width=640, height=480, encoding="rgb8")
    c = dict(ids, transfer_id="load-1", capture_id="capture-1",
             image_stamp_ns=cap["image_stamp_ns"], frame_id=cap["frame_id"],
             rgb_sha256=h(raw), inference_ok=True, status="STABLE",
             raw_status="STABLE", raw_confidence=.9, confidence=.9,
             model_version="CI_TEST_DOUBLE", reason="OK",
             stable_confidence_min=0., unstable_confidence_min=0.,
             inference_sim_ns=14_000_000_000, calls=1)
    # Synchronized world XYZ + tray quaternion (xyzw); no fake relative position field.
    def pose(t, tray, dish):
        return dict(sim_ns=t, tray_xyz=tray, tray_xyzw=[0,0,0,1],
                    entities={"dish-1":dish})
    poses = [pose(1_000_000_000,[0,0,0],[2,0,.1]),
             pose(12_000_000_000,[1,0,0],[1,0,.1]),
             pose(13_000_000_000,[1,0,0],[1,0,.1]),
             pose(18_000_000_000,[1.5,0,0],[1.5,0,.1]),
             pose(22_000_000_000,[2,0,0],[2,0,.1]),
             pose(23_000_000_000,[2,0,0],[3,0,.1])]
    nav = []
    for i,(leg,start,end) in enumerate([("TO_TABLE",2,3),("TO_RETURN",16,22),("TO_HOME",24,25)]):
        nav.append(dict(request_id="request-1",leg=leg,goal_uuid=f"{i+1:032x}",
                        terminal_status="SUCCEEDED", stop_verified=True,
                        start_sim_ns=start*10**9,end_sim_ns=end*10**9,
                        odom=[dict(sim_ns=(start*10**9+k*(end-start)*500_000_000),
                                   x=k*.3,y=0) for k in range(3)],
                        scan_stamps_ns=[start*10**9, (start+end)*500_000_000,end*10**9]))
    m = dict(ids, source_sha=SHA, run_id="fixture", world_id="restaurant",
             scope="SYNTHETIC_FIXTURE", evidence_class="INTEGRATION_EVIDENCE_ONLY",
             camera_mount="ROBOT", camera_publishers=1, clock_publishers=1,
             entity_ids=["dish-1"], license_status="OWNED",
             ground_truth="NOT_OPERATOR_APPROVED", label=None,
             load=load, capture=cap, inference=c, unload=unload,
             poses=poses, nav=nav, causal_monotonic_ns=[1,2,3,4,5],
             frame_received_monotonic_ns=2, inference_received_monotonic_ns=3,
             approval_sim_ns=15_000_000_000, png_sha256=h(png))
    return m,{"frame.png":png,"frame.rgb":raw,"c_input.rgb":raw}

def pack(root, m, blobs, *, corrupt=False, unsafe=False, duplicate=False):
    files = dict(blobs, **{"evidence.json":j(m)})
    for name in ("load","capture","inference","unload"):
        files[name+".json"]=j(m[name])
    index={n:{"sha256":h(v),"size_bytes":len(v)} for n,v in files.items()}
    if corrupt: index["frame.png"]["sha256"]="0"*64
    files["manifest.json"]=j(index)
    a=root/"evidence.tar.gz"
    with tarfile.open(a,"w:gz") as tar:
        for n,v in files.items():
            t=tarfile.TarInfo(n);t.size=len(v);tar.addfile(t,io.BytesIO(v))
        if unsafe:
            t=tarfile.TarInfo("../escape");t.size=1;tar.addfile(t,io.BytesIO(b"x"))
        if duplicate:
            t=tarfile.TarInfo("frame.rgb");t.size=1;tar.addfile(t,io.BytesIO(b"x"))
    side=root/"evidence.tar.gz.sha256"
    side.write_text(h(a.read_bytes())+"  "+a.name+"\n")
    return a,side

class EvidenceTests(unittest.TestCase):
    def check(self, mutate=None, code=None, **kw):
        m,blobs=fixture()
        if mutate: mutate(m,blobs)
        with tempfile.TemporaryDirectory() as d:
            a,s=pack(Path(d),m,blobs,**kw)
            before=(a.read_bytes(),s.read_bytes())
            result=audit(a,s,SHA)
            self.assertEqual(before,(a.read_bytes(),s.read_bytes()))
            self.assertFalse(result["training_allowed"])
            self.assertFalse(result["product_accepted"])
            if code:
                self.assertEqual(result["first_error"],code,result)
                self.assertEqual(result["verdict"],"FAIL")
            else:
                self.assertEqual(result["verdict"],"PASS",result)
                self.assertEqual(result["scope"],"SYNTHETIC_FIXTURE")
            return result
    def test_valid(self): self.check()
    def test_bad_hash(self): self.check(code="B_FILE_HASH",corrupt=True)
    def test_path(self): self.check(code="B_ARCHIVE_PATH",unsafe=True)
    def test_duplicate(self): self.check(code="B_ARCHIVE_DUPLICATE",duplicate=True)
    def test_rgb(self): self.check(lambda m,b:b.update({"c_input.rgb":b"x"*len(b["frame.rgb"])}),"B_C_INPUT_HASH")
    def test_png(self): self.check(lambda m,b:m.update(png_sha256="0"*64),"B_PNG_HASH")
    def test_station(self): self.check(lambda m,b:m.update(camera_mount="STATION"),"B_CAMERA_SOURCE")
    def test_stack(self): self.check(lambda m,b:m["capture"].update(stack_id="other"),"B_ID_MISMATCH")
    def test_stale(self): self.check(lambda m,b:m["capture"].update(image_stamp_ns=1),"B_TIME_ORDER")
    def test_duplicate_entity(self): self.check(lambda m,b:m.update(entity_ids=["dish-1","dish-1"]),"B_ENTITY_SET")
    def test_pose(self): self.check(lambda m,b:m["poses"][3]["entities"].update({"dish-1":[1,0,.1]}),"B_TRAY_RELATIVE")
    def test_rights(self): self.check(lambda m,b:m.update(license_status=None),"B_RIGHTS_MISSING")
    def test_label(self): self.check(lambda m,b:m.update(label="STABLE"),"B_LABEL_POLICY")
    def test_inference_calls(self): self.check(lambda m,b:m["inference"].update(calls=2),"B_INFERENCE_COUNT")
    def test_uuid(self): self.check(lambda m,b:m["nav"][1].update(goal_uuid=m["nav"][0]["goal_uuid"]),"B_NAV_UUID")
    def test_no_approval(self): self.check(lambda m,b:m.update(approval_sim_ns=17_000_000_000),"B_NAV_CAUSAL")
    def test_source(self): self.check(lambda m,b:m.update(source_sha="b"*40),"B_SOURCE_SHA")
    def test_unload(self): self.check(lambda m,b:m["unload"].update(tray_count=1),"B_TRANSFER")
    def test_clock(self): self.check(lambda m,b:m.update(clock_publishers=2),"B_CAMERA_SOURCE")
    def test_freshness(self): self.check(lambda m,b:m.update(inference_received_monotonic_ns=3_000_000_003),"B_FRESHNESS")
    def test_actual_candidate_hold(self):
        m,b=fixture();m["scope"]="ACTUAL_PRODUCT_CANDIDATE"
        with tempfile.TemporaryDirectory() as d:
            a,s=pack(Path(d),m,b)
            result=audit(a,s,SHA)
            self.assertEqual(result["verdict"],"HOLD",result)
            self.assertFalse(result["product_accepted"])
    def test_sidecar(self):
        m,b=fixture()
        with tempfile.TemporaryDirectory() as d:
            a,s=pack(Path(d),m,b);s.write_text("0"*64+"  "+a.name+"\n")
            self.assertEqual(audit(a,s,SHA)["first_error"],"B_ARCHIVE_SHA")
