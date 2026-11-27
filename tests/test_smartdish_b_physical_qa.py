import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.smartdish_b_product_evidence_qa import (relative, check_clock, need, QAError, pair_kind, require_session, verify_transfer, safe_name, check_dish, check_clearance, check_rgb_order, intake, scene_ids, shutdown)

class TestPhysicalQA(unittest.TestCase):
    def test_rotation(self):
        q=Rotation.from_euler("z",90,degrees=True).as_quat()[None,:]
        p, angles=relative(np.array([[1.,2.,0.]]),q,np.array([[1.,3.,.5]]),q)
        np.testing.assert_allclose(p,[[1,0,.5]],atol=1e-12)
        np.testing.assert_allclose(angles,[[0,0,0]],atol=1e-12)
    def test_tilt(self):
        a=np.array([[0.,0.,0.,1.]])
        b=Rotation.from_euler("x",.04).as_quat()[None,:]
        _,angles=relative(np.zeros((1,3)),a,np.zeros((1,3)),b)
        self.assertAlmostEqual(angles[0,2],.04)
    def test_clock(self):
        check_clock(np.array([1000000,2000000]),np.array([1,2]),np.array([1000000,1000000]))
    def test_duplicate(self):
        with self.assertRaises(QAError): check_clock(np.array([1,1]),np.array([1,2]),np.array([1000000]*2))
    def test_gap(self):
        with self.assertRaises(QAError): check_clock(np.array([1000000,3000000]),np.array([1,3]),np.array([1000000]*2))
    def test_support(self):
        self.assertEqual(pair_kind("floor::body::floor_collision","waffle_pi::wheel_left_link::wheel_left_collision"),"ground")
        self.assertEqual(pair_kind("waffle_pi::smartdish_product_tray::platform_collision","smartdish_product_dish_00::body::envelope"),"dish")
        self.assertEqual(pair_kind("wall::body::collision","smartdish_product_dish_00::body::envelope"),"unexpected")
    def test_other_session(self):
        with self.assertRaises(QAError): require_session({"source_sha":"a","run_id":"r2"},"a","r1")
    def test_archive_path(self):
        for p in ("../a","/a","a/../b","a\\b"):
            self.assertFalse(safe_name(p))
    def test_invalid_transfer(self):
        with self.assertRaises(QAError): verify_transfer({"operation":"LOAD","entity_ids":["159","164","170"],"status":"ACK","tray_count":3},[159,164,169],3)
    def test_center_gate(self):
        with self.assertRaises(QAError): check_dish(np.array([.016]),np.array([0.]),np.array([0.]),np.array([.02]),np.array([.01]))
    def test_clearance_gate(self):
        with self.assertRaises(QAError): check_clearance(np.array([.049]))

    def test_stale_rgb(self):
        with self.assertRaises(QAError): check_rgb_order(9,10)
        with self.assertRaises(QAError): check_rgb_order(10,10)
        check_rgb_order(11,10)
    def test_dish_tilt_gate(self):
        with self.assertRaises(QAError): check_dish(np.array([.001]),np.array([.036]),np.array([0.]),np.array([.02]),np.array([.01]))
    def test_duplicate_model(self):
        with self.assertRaises(QAError): scene_ids('model {\n  name: "dish"\n  id: 1\n}\nmodel {\n  name: "dish"\n  id: 2\n}')
    def test_wrong_zip(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.zip";p.write_bytes(b"tampered")
            with self.assertRaisesRegex(QAError,"ZIP_SHA"):
                intake(p,Path(td)/"out",(1,1,"a","0"*64,"1"*64,1))
    def test_lifecycle_ack_missing(self):
        with self.assertRaisesRegex(QAError,"ACK_MISSING"):
            shutdown(None,{"lifecycle_shutdown_detail":{"a":{},"b":{},"c":{}},"lifecycle_shutdown":{"a":"ACK","b":"ACK","c":"NO_ACK"}})
    def test_internal_corruption(self):
        import tempfile, io, zipfile, tarfile, hashlib
        from pathlib import Path
        H=lambda b:hashlib.sha256(b).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.zip"; buf=io.BytesIO()
            with tarfile.open(fileobj=buf,mode="w:gz") as t:
                for n,b in [("a04/SHA256SUMS",(H(b"expected")+"  ./data.txt\n").encode()),("a04/data.txt",b"tampered")]:
                    info=tarfile.TarInfo(n);info.size=len(b);t.addfile(info,io.BytesIO(b))
            body=buf.getvalue()
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("a.tar.gz",body);z.writestr("a.tar.gz.sha256",H(body)+"  a.tar.gz\n")
            with self.assertRaisesRegex(QAError,"INNER_SHA"):
                intake(p,Path(td)/"out",(1,1,"a",H(p.read_bytes()),H(body),1))
