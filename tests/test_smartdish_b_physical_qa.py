import unittest
import numpy as np
from scipy.spatial.transform import Rotation
from scripts.smartdish_b_product_evidence_qa import (relative, check_clock, need, QAError, pair_kind, require_session, verify_transfer, safe_name)

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
        with self.assertRaises(QAError): need(.016<=.015,"DISH_CENTER")
    def test_clearance_gate(self):
        with self.assertRaises(QAError): need(.049>.05,"CLEARANCE")
