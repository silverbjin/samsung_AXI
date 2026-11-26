import io,tarfile,sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ai/scripts'))
from audit_b_a14 import archive,sha,track,contacts,audit

def tar(items):
    o=io.BytesIO()
    with tarfile.open(fileobj=o,mode='w:gz') as t:
        for n,b in items:
            m=tarfile.TarInfo(n);m.size=len(b);t.addfile(m,io.BytesIO(b))
    return o.getvalue()

def rows(x=.5):
    result=[]
    for i,z in enumerate((.24,.227,.127,.04)):
        t=(501+i*50)*1000000
        result.append(dict(sim_time_ns=t,world_frame_id='world',tray_frame_id='tray_platform/body',stamp_source='ROS_TF_HEADER_STAMP',transform_mode='DYNAMIC_DISH_VS_STATIC_TRAY',relative={'translation_m':dict(x=x,y=0,z=z),'quaternion':dict(w=1,x=0,y=0,z=0)},velocity=dict(frame_id='tray_platform/body',provenance='UNAVAILABLE_FIRST_SAMPLE' if i==0 else 'DERIVED_POSE_FINITE_DIFFERENCE',dt_seconds=.05,linear_m_s=None if i==0 else dict(x=0,y=0,z=(z-(.24,.227,.127,.04)[i-1])/.05),angular_rad_s=dict(x=0,y=0,z=0))))
    return result

class TestAudit(unittest.TestCase):
    def test_archive(self):
        raw=b'raw';items=[('raw',raw),('SHA256SUMS',(sha(raw)+'  raw\n').encode())];b=tar(items)
        self.assertEqual(archive(b,sha(b)),{'raw':raw})
        with self.assertRaisesRegex(ValueError,'ARCHIVE_SHA'):archive(b,'0'*64)
        for bad in [items+[('../escape',b'x')],items+[('raw',raw)],items+[('approval_ledger.jsonl',b'x')],items+[('extra',b'x')],[('raw',b'bad'),items[1]]]:
            v=tar(bad)
            with self.assertRaises(ValueError):archive(v,sha(v))
    def test_wrong_owner(self):
        with self.assertRaisesRegex(ValueError,'ARCHIVE_SHA'):audit(b'fixture')
    def test_pre_t0_motion(self):
        r=track(rows(),600000000,800000000,.35,.28)
        self.assertTrue(r['pre_t0_center_outside_tray']);self.assertFalse(r['t0_exact'])
        self.assertAlmostEqual(r['pre_t0_vertical_velocity_m_s'],-.26)
        self.assertAlmostEqual(r['post_t0_sample_path_m'],.087)
        self.assertFalse(track(rows(.1),600000000,800000000,.35,.28)['pre_t0_center_outside_tray'])
    def test_invalid_velocity(self):
        r=rows();r[1]['velocity']['linear_m_s']['z']=0
        with self.assertRaisesRegex(ValueError,'VELOCITY_VALUE'):track(r,600000000,800000000,.35,.28)
    def test_time_reversal(self):
        r=rows();r[1]['sim_time_ns']=r[0]['sim_time_ns']
        with self.assertRaisesRegex(ValueError,'POSE_TIME'):track(r,600000000,800000000,.35,.28)
    def test_contact_refresh_and_silence(self):
        header='sim_ns\titeration\tdt_ns\ttopic\tmodel\tsensor\tcollision\tsensor_id\tcollision_id\tpresent\tcount\tpairs\tarmed\tpost_state\tlate_control\n'
        a='1000000\t1\t1000000\tt\ttray\ts\tc\t1\t2\t1\t0\t\t1\tNO_CHANGE\t0\n'
        b='2000000\t2\t1000000\tt\ttray\ts\tc\t1\t2\t1\t1\t2:3\t1\tPERIODIC\t0\n'
        ros=[dict(topic='t',sim_time_ns=2000000,timestamp_source='ROS_CONTACT_HEADER_STAMP',contacts=[dict(collision1_id=3,collision2_id=2)])]
        r=contacts((header+a+b).encode(),ros,['t'],0,2000000)
        self.assertEqual(r['transport']['t']['empty_steps'],1)
        self.assertEqual(r['transport']['t']['matched_positive_steps'],1)
        self.assertIn('ONLY',r['scope'])
        with self.assertRaisesRegex(ValueError,'ECM_STEP_REFRESH'):contacts((header+b).encode(),ros,['t'],0,2000000)
if __name__=='__main__':unittest.main()
