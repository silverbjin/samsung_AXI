import sys,math,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from a15_pilot_world import design,SCENES,TRIGGER_NS,STEP_NS,DURATION_NS,TORQUE_NM
from a15_pilot_contract import check_initial,grid,check_trigger,metrics

def p(x=0,y=0,z=0,q=(0,0,0,1)):
    return dict(x=x,y=y,z=z,qx=q[0],qy=q[1],qz=q[2],qw=q[3])
def fixture(scene="L15-01"):
    meta=design(scene);t0=1_800_000_000
    tracks={n:{} for n in ("tray_platform","camera","dish_01","dish_02")}
    for t in range(t0-200_000_000,t0+STEP_NS,STEP_NS):
        row={"tray_platform":p(z=.55),"camera":p(z=1.5,q=(0,math.sqrt(.5),0,math.sqrt(.5)))}
        row.update({d["name"]:p(d["x"],d["y"],d["z"]) for d in meta["initial_dishes"]})
        for n,v in row.items():tracks[n][t]=(t//STEP_NS,v)
    info=dict(width=640,height=480,k=[381.,0,320.,0,381.,240.,0,0,1],stamp_ns=t0)
    ecm=[dict(sim_ns=t0,model=n,collision_id=i,present=True,pairs=pairs) for n,i,pairs in [("tray_platform",10,[[10,11]]),("dish_01",11,[[10,11],[11,12]]),("dish_02",12,[[11,12]])]]
    return tracks,meta,t0,info,ecm

class Pilot(unittest.TestCase):
    def test_layout_pairs_and_common_intervention(self):
        d=[design(s) for s in SCENES]
        self.assertEqual(len({x["geometry_family_id"] for x in d}),2)
        self.assertEqual(d[0]["geometry_family_id"],d[1]["geometry_family_id"])
        self.assertEqual(d[2]["geometry_family_id"],d[3]["geometry_family_id"])
        self.assertEqual(len({x["physical_layout_id"] for x in d}),4)
        self.assertTrue(all(x["trigger"]==d[0]["trigger"] and not x["human_approved"] for x in d))
        for scene in SCENES: self.assertEqual(check_initial(*fixture(scene))["occlusion_review_required"],True)
    def test_missing_t0_pose_rejected(self):
        t,m,t0,i,e=fixture();del t["dish_01"][t0]
        with self.assertRaisesRegex(ValueError,"POSE_WINDOW_GAP"):check_initial(t,m,t0,i,e)
    def test_pre_t0_fall_rejected(self):
        t,m,t0,i,e=fixture();t["dish_02"][t0][1]["z"]-=.013
        with self.assertRaisesRegex(ValueError,"NOT_SETTLED"):check_initial(t,m,t0,i,e)
    def test_outside_tray_rejected(self):
        t,m,t0,i,e=fixture()
        for _,r in t["dish_02"].values():r["x"]=.5
        with self.assertRaisesRegex(ValueError,"OUTSIDE_TRAY"):check_initial(t,m,t0,i,e)
    def test_silent_support_not_positive(self):
        t,m,t0,i,e=fixture()
        for r in e:r["pairs"]=[]
        with self.assertRaisesRegex(ValueError,"SUPPORT_UNOBSERVED"):check_initial(t,m,t0,i,e)
    def test_camera_skew_rejected(self):
        t,m,t0,i,e=fixture();i["stamp_ns"]=t0-300_000_000
        with self.assertRaisesRegex(ValueError,"CAMERA_INFO"):check_initial(t,m,t0,i,e)
    def test_missing_end(self):
        t,m,t0,i,e=fixture()
        with self.assertRaisesRegex(ValueError,"POSE_WINDOW_GAP"):metrics(t,t0,t0+STEP_NS)
    def test_trigger_exact_command(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"trigger.tsv";header="sim_ns\titeration\tlink_id\ttorque_y_nm\n"
            rows=[f"{t}\t{t//STEP_NS}\t12\t{TORQUE_NM}\n" for t in range(TRIGGER_NS,TRIGGER_NS+DURATION_NS,STEP_NS)]
            f.write_text(header+"".join(rows))
            self.assertEqual(check_trigger(f)["command_steps"],500)
            f.write_text(header+"".join(rows[:-1]))
            with self.assertRaisesRegex(ValueError,"TRIGGER_COMMAND_TRACE"):check_trigger(f)
if __name__=="__main__":unittest.main()
