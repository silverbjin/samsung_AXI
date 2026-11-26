import csv,io,json,math,sys,tempfile,unittest,hashlib,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import a18_pilot_world as w
from a18_pilot_contract import check_initial,grid,check_trigger,metrics,entity_names,load_poses
from a18_archive import bundle,batch
EXPECTED_LAYOUTS=["ced9fa734c8c9110db91e77a3d73db955112c6d2d15222875341da0fd7941f63","adbac65266a7a9e3f67225ae17543ea372ae6abf82814813475e4cd37c4fd4af","5f732eccb47f352f5db66a60c80425727e9c67039d71e90208beb582a0f1ab23","883b6fd0d613d3b876a083429acd7e8edf37ccc360ab62870631c055bf6c591e","60208d61ba164f675b9800706005e9b1abad585cde9c04398bdcb8933ccbd8be","8dfe91ad7d475a6ddd119c56bbbedc940742a744e27aad1b39c3953dc0a8765a","e8ba668093425a15633e68a3ad48214cd30aab4c7ef6c4c9a9056f9e6fc3b2fa","282347ce4df946d168e788b17bba34a02ce7bbc82ac45ae026ffcee6f0e34ee5"]
EXPECTED_SIGNATURES=["29aa55a4cd1f7dac2c08b107616e6c68fd448cb5715924501c17414f0c3464ce","7f82c9c9cbba225058741f826b966cca0d7837780b89bc4744e216afee9ef590","e4efc6c4a2b490fffae99d1bafc3b89a6f590d20edd2ef109a5ce3965ddc90c0","dc06ef3baae989bdda5127aec8694c581ba4876ebb32089482afc4c1662ee442","48cda392530a70789b64925106ec35686dbb0cb0c80bd7c7a93128d5df6995f0","91f71071fd1e19df0c8bc88a9c1733af7d768ee3ec71cc3a3dc50f13eaf33169","e9f071df463b093f071f935e34b5f83815b7f7396e9791c779f59b3a5e23831c","feb4bba9d2a789ea1dd034fa2eb0b94a8dcb0005351cdb6918d5e15dec8a54bc"]
def p(x=0,y=0,z=0,q=(0,0,0,1)):return dict(x=x,y=y,z=z,qx=q[0],qy=q[1],qz=q[2],qw=q[3])
def fixture(scene):
    meta=w.design(scene);t0=2_000_000_000;tracks={n:{} for n in entity_names(meta)}
    for t in range(t0-200_000_000,t0+w.STEP_NS,w.STEP_NS):
        row={"tray_platform":p(z=.55),"camera":p(z=1.5,q=(0,math.sqrt(.5),0,math.sqrt(.5)))}
        row.update({d["name"]:p(d["x"],d["y"],d["z"]) for d in meta["initial_dishes"]})
        for n,v in row.items():tracks[n][t]=(t//w.STEP_NS,v)
    info=dict(width=640,height=480,k=[381.,0,320.,0,381.,240.,0,0,1],stamp_ns=t0)
    chain=["tray_platform"]+[d["name"] for d in meta["initial_dishes"]];ecm=[]
    for i,n in enumerate(chain):
        pairs=[]
        if i:pairs.append([10+i-1,10+i])
        if i+1<len(chain):pairs.append([10+i,10+i+1])
        ecm.append(dict(sim_ns=t0,model=n,collision_id=10+i,present=True,pairs=pairs))
    return tracks,meta,t0,info,ecm
class A18(unittest.TestCase):
    def test_registry_identity(self):
        ds=[w.design(s) for s in w.SCENES];old=w.old_designs()
        self.assertEqual([d["physical_layout_id"] for d in ds],EXPECTED_LAYOUTS)
        self.assertEqual([d["comparison_fingerprint"] for d in ds],EXPECTED_SIGNATURES)
        self.assertEqual(len({d["comparison_fingerprint"] for d in ds}),8)
        self.assertFalse({d["comparison_fingerprint"] for d in ds}&{w.fingerprint(d["initial_dishes"]) for d in old})
        self.assertEqual(len({d["geometry_family_id"] for d in ds+old}),6)
        self.assertEqual(w.phase_scenes(1),("L18-03","L18-04","L18-01","L18-02"));self.assertEqual(w.phase_scenes(2),w.SCENES[4:])
        for d in ds:
            self.assertFalse(d["human_approved"]);self.assertFalse(d["training_eligible"])
            self.assertGreater(d["nominal_min_tray_clearance_m"],0)
            self.assertEqual(d["trigger"]["target"],d["initial_dishes"][-1]["name"]+"/body")
            self.assertAlmostEqual(d["nominal_center_support_margin_m"]-d["initial_dishes"][-1]["radius_m"],d["nominal_full_containment_margin_m"])
    def test_registry_invalid_family_and_duplicate(self):
        r=w.read_registry();r["families"]["F1"]["id"]="0"*64
        with patch.object(w,"read_registry",return_value=r):
            with self.assertRaisesRegex(ValueError,"FAMILY_MISMATCH"):w.design("L18-01")
        r=w.read_registry();r["layouts"][2]["x"]=[-.097,0.]
        with patch.object(w,"read_registry",return_value=r):
            with self.assertRaisesRegex(ValueError,"HISTORICAL_LAYOUT_DUPLICATE"):w.design("L18-03")
    def test_identity_ignores_observation_seed(self):
        d=w.design("L18-01");ds=d["initial_dishes"]
        fp=w.fingerprint(ds);d.update(seed=99,source_class="OWNER_WSL2",observation_id="another")
        ds[0]["color"]="different";self.assertEqual(w.fingerprint(ds),fp)
    def test_actual_sdf_generation_all_candidates(self):
        for s in w.SCENES:
            with tempfile.TemporaryDirectory() as td:
                out=Path(td);a=out/"p.so";b=out/"h.so";a.write_bytes(b"fixture");b.write_bytes(b"fixture")
                d=w.generate(s,out,a,b);root=ET.parse(out/"scenario.sdf")
                self.assertEqual(len(d["contact_topics"]),len(d["initial_dishes"])+2)
                for dish in d["initial_dishes"]:
                    m=root.find("./world/model[@name='"+dish["name"]+"']")
                    self.assertEqual(m.findtext("static"),"false")
                    self.assertEqual([float(x) for x in m.findtext("pose").split()],[dish[k] for k in ("x","y","z","roll","pitch","yaw")])
                    for role in ("collision","visual"):
                        cyl=m.find("link/"+role+"/geometry/cylinder")
                        self.assertEqual(float(cyl.findtext("radius")),dish["radius_m"])
                        self.assertEqual(float(cyl.findtext("length")),dish["thickness_m"])
                    self.assertEqual(float(m.findtext("link/inertial/mass")),dish["mass_kg"])
                    self.assertEqual(float(m.findtext("link/collision/surface/friction/ode/mu")),dish["friction_mu"])
                self.assertEqual(root.findtext("./world/plugin[@name='smartdish::A16Pilot']/target_model"),d["initial_dishes"][-1]["name"])
    def test_2_3_dish_support(self):
        for s in w.SCENES:
            t,m,t0,i,e=fixture(s);v=check_initial(t,m,t0,i,e)
            self.assertEqual(len(v["support"]),len(m["initial_dishes"]))
            self.assertAlmostEqual(v["actual_t0_support_geometry"]["center_support_margin_m"],m["nominal_center_support_margin_m"])
            self.assertAlmostEqual(v["actual_t0_support_geometry"]["full_containment_margin_m"],m["nominal_full_containment_margin_m"])
    def test_failure_exact_stamp_and_missing_support(self):
        t,m,t0,i,e=fixture("L18-08");i["stamp_ns"]-=w.STEP_NS
        with self.assertRaisesRegex(ValueError,"CAMERA_INFO"):check_initial(t,m,t0,i,e)
        t,m,t0,i,e=fixture("L18-08")
        for r in e:r["pairs"]=[]
        with self.assertRaisesRegex(ValueError,"SUPPORT_UNOBSERVED"):check_initial(t,m,t0,i,e)
    def test_failure_pose_gap_fov_and_drift(self):
        t,m,t0,i,e=fixture("L18-08");del t["dish_03"][t0]
        with self.assertRaisesRegex(ValueError,"POSE_WINDOW_GAP"):check_initial(t,m,t0,i,e)
        t,m,t0,i,e=fixture("L18-08");i["k"][2]=10000
        with self.assertRaisesRegex(ValueError,"CAMERA_FOV"):check_initial(t,m,t0,i,e)
        t,m,t0,i,e=fixture("L18-08")
        for _,v in t["dish_03"].values():v["x"]+=.003
        with self.assertRaisesRegex(ValueError,"NOMINAL_POSITION_DRIFT"):check_initial(t,m,t0,i,e)
    def test_pose_limit_with_3_dishes(self):
        t,m,t0,i,e=fixture("L18-08");self.assertEqual(len(t),5);self.assertLess(5*12301,100000)
        self.assertEqual(len(grid(t,t0-200_000_000,t0)),201)
        with tempfile.TemporaryDirectory() as td:
            pth=Path(td)/"poses.tsv";pth.write_text("sim_ns\titeration\tentity\tentity_id\tx\ty\tz\tqx\tqy\tqz\tqw\nOVERFLOW\n")
            with self.assertRaisesRegex(ValueError,"POSE_LIMIT"):load_poses(pth,m)
    def test_trigger_command_trace(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"trigger.tsv";header="sim_ns\titeration\tlink_id\ttorque_y_nm\n"
            rows=[f"{t}\t{t//w.STEP_NS}\t12\t{w.TORQUE_NM}\n" for t in range(w.TRIGGER_NS,w.TRIGGER_NS+w.DURATION_NS,w.STEP_NS)]
            f.write_text(header+"".join(rows));self.assertEqual(check_trigger(f)["command_steps"],500)
            f.write_text(header+"".join(rows[:-1]))
            with self.assertRaisesRegex(ValueError,"TRIGGER_COMMAND_TRACE"):check_trigger(f)
    def test_partial_archive(self):
        with tempfile.TemporaryDirectory() as td:
            pth=Path(td);(pth/"build_pose.log").write_text("실패 시험")
            batch(pth,"a"*40,"--ci",2,1)
            self.assertTrue((pth/"a18_pilot_evidence.tar.gz.sha256").is_file());b=json.loads((pth/"batch_status.json").read_text())
            self.assertEqual(b["exit_code"],2);self.assertEqual(set(b["scenes"]),set(w.SCENES[:4]));self.assertFalse(b["training_eligible"])
    def test_collector_profile_scope(self):
        text=(Path(__file__).resolve().parents[1]/"scripts/a18_pilot_collect.py").read_text()
        self.assertIn('profile==RETAIN',text);self.assertIn('profile==INHERIT',text)
        self.assertIn('observe_server_profile(server,profile_record,"runtime_observation_pre_shutdown")',text)
        self.assertIn('report["cleanup"]=="PASS"',text)
if __name__=="__main__":unittest.main()
