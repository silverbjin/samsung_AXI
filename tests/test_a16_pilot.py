import csv,io,json,math,sys,tempfile,unittest,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from a16_pilot_world import design,SCENES,STEP_NS,TRIGGER_NS,DURATION_NS,TORQUE_NM,hash_json,generate
from a15_pilot_world import design as legacy
from a16_pilot_contract import check_initial,grid,check_trigger,metrics,entity_names,load_poses
from a16_diagnostics import transport_diagnostic
from a16_archive import bundle,batch
def p(x=0,y=0,z=0,q=(0,0,0,1)):
    return dict(x=x,y=y,z=z,qx=q[0],qy=q[1],qz=q[2],qw=q[3])
def fixture(scene):
    meta=design(scene);t0=2_000_000_000
    tracks={n:{} for n in entity_names(meta)}
    for t in range(t0-200_000_000,t0+STEP_NS,STEP_NS):
        row={"tray_platform":p(z=.55),"camera":p(z=1.5,q=(0,math.sqrt(.5),0,math.sqrt(.5)))}
        row.update({d["name"]:p(d["x"],d["y"],d["z"]) for d in meta["initial_dishes"]})
        for n,v in row.items():tracks[n][t]=(t//STEP_NS,v)
    info=dict(width=640,height=480,k=[381.,0,320.,0,381.,240.,0,0,1],stamp_ns=t0)
    chain=["tray_platform"]+[d["name"] for d in meta["initial_dishes"]]
    ecm=[]
    for i,n in enumerate(chain):
        pairs=[]
        if i:pairs.append([10+i-1,10+i])
        if i+1<len(chain):pairs.append([10+i,10+i+1])
        ecm.append(dict(sim_ns=t0,model=n,collision_id=10+i,present=True,pairs=pairs))
    return tracks,meta,t0,info,ecm
class A16(unittest.TestCase):
    def test_layout_matrix(self):
        ds=[design(s) for s in SCENES]
        self.assertEqual(len({d["physical_layout_id"] for d in ds}),8)
        self.assertEqual(len({d["physical_fingerprint"] for d in ds}),8)
        self.assertEqual(len({d["geometry_family_id"] for d in ds}),2)
        self.assertEqual({len(d["initial_dishes"]) for d in ds},{2,3})
        old={tuple((x["radius_m"],x["thickness_m"]) for x in legacy(s)["initial_dishes"]) for s in ("L15-01","L15-02","L15-03","L15-04")}
        self.assertTrue(all(tuple((x["radius_m"],x["thickness_m"]) for x in d["initial_dishes"]) not in old for d in ds))
        for d in ds:
            self.assertEqual(d["geometry_family_id"],hash_json({"version":"A16_FAMILY_V1","geometry":d["family_basis"]}))
            self.assertEqual(d["physical_layout_id"],hash_json({"version":"A16_LAYOUT_V1","family":d["geometry_family_id"],"world_poses_m_rad":d["layout_basis"]}))
            self.assertFalse(d["human_approved"]);self.assertFalse(d["training_eligible"])
        for d in (ds[:4],ds[4:]):
            for group in ("CENTER","ECCENTRIC"):
                self.assertEqual(len({x["nominal_support_margin_m"] for x in d if x["upper_tray_center_group"]==group}),2)
    def test_dynamic_support_positive(self):
        for s in SCENES:
            t,m,t0,i,e=fixture(s);v=check_initial(t,m,t0,i,e)
            self.assertEqual(len(v["support"]),len(m["initial_dishes"]))
    def test_exact_stamp(self):
        t,m,t0,i,e=fixture("L16-05");i["stamp_ns"]-=STEP_NS
        with self.assertRaisesRegex(ValueError,"CAMERA_INFO"):check_initial(t,m,t0,i,e)
    def test_missing_t0_and_end(self):
        t,m,t0,i,e=fixture("L16-05");del t["dish_03"][t0]
        with self.assertRaisesRegex(ValueError,"POSE_WINDOW_GAP"):check_initial(t,m,t0,i,e)
        t,m,t0,i,e=fixture("L16-05")
        with self.assertRaisesRegex(ValueError,"POSE_WINDOW_GAP"):metrics(t,t0,t0+STEP_NS)
    def test_fall_and_outside(self):
        t,m,t0,i,e=fixture("L16-01");t["dish_02"][t0][1]["z"]-=.013
        with self.assertRaisesRegex(ValueError,"NOT_SETTLED"):check_initial(t,m,t0,i,e)
        t,m,t0,i,e=fixture("L16-01")
        for _,v in t["dish_02"].values():v["x"]=.5
        with self.assertRaisesRegex(ValueError,"OUTSIDE_TRAY"):check_initial(t,m,t0,i,e)
    def test_fov_negative(self):
        t,m,t0,i,e=fixture("L16-01");i["k"][2]=10000.
        with self.assertRaisesRegex(ValueError,"CAMERA_FOV"):check_initial(t,m,t0,i,e)
    def test_silent_support(self):
        t,m,t0,i,e=fixture("L16-05")
        for r in e:r["pairs"]=[]
        with self.assertRaisesRegex(ValueError,"SUPPORT_UNOBSERVED"):check_initial(t,m,t0,i,e)
    def test_trigger_gap(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"trigger.tsv";header="sim_ns\titeration\tlink_id\ttorque_y_nm\n"
            rows=[f"{t}\t{t//STEP_NS}\t12\t{TORQUE_NM}\n" for t in range(TRIGGER_NS,TRIGGER_NS+DURATION_NS,STEP_NS)]
            f.write_text(header+"".join(rows));self.assertEqual(check_trigger(f)["command_steps"],500)
            f.write_text(header+"".join(rows[:-1]))
            with self.assertRaisesRegex(ValueError,"TRIGGER_COMMAND_TRACE"):check_trigger(f)
    def test_transport_silence_and_duplicates(self):
        t="x";e=[dict(topic=t,sim_ns=1,pairs=[]),dict(topic=t,sim_ns=2,pairs=[[1,2]])]
        n=[dict(topic=t,sim_time_ns=2,receive_monotonic_ns=1,pairs=[(1,2)]),dict(topic=t,sim_time_ns=2,receive_monotonic_ns=2,pairs=[(1,2)])]
        r=transport_diagnostic(e,[],n,[t],0,2)
        self.assertTrue(r["topics"][t]["silent_ros"]);self.assertEqual(r["topics"][t]["native"]["duplicate_stamp_pair_callbacks"],1)
        self.assertFalse(r["full_delivery_proven"]);self.assertEqual(r["production_contact_health"],"HOLD")
    def test_failure_archive_and_path(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/"build_pose.log").write_text("fixture failure")
            batch(p,"a"*40,"--ci",2)
            self.assertTrue((p/"a16_pilot_evidence.tar.gz.sha256").is_file())
            self.assertTrue((p/"a16_pilot_diagnostics.tar.gz.sha256").is_file())
            b=json.loads((p/"batch_status.json").read_text())
            self.assertEqual(b["exit_code"],2);self.assertFalse(b["training_eligible"])
            (p/"unsafe").symlink_to(p/"build_pose.log")
            with self.assertRaisesRegex(ValueError,"UNSAFE_PATH"):bundle(p,["unsafe"],"bad.tar.gz")
if __name__=="__main__":unittest.main()
