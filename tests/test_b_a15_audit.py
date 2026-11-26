"""QA03 contract fixtures only — NEVER Owner physical acceptance or GT."""
import io,math,os,tarfile,json,sys,hashlib,csv,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ai/scripts'))
import audit_b_a15 as a
from b_a15_qa_cli import main

def tgz(items):
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode='w:gz') as tf:
        for name,data in items:
            m=tarfile.TarInfo(name);m.size=len(data);tf.addfile(m,io.BytesIO(data))
    return b.getvalue()

def sealed(items):
    checks=''.join(a.sha(body)+'  '+name+'\n' for name,body in items).encode()
    return tgz(items+[('SHA256SUMS',checks)])

def stub_scene(_,name):
    i=a.SCENES.index(name)
    return dict(scene_id=name,trial_id=name,geometry_family_id=('family1' if i<2 else 'family2'),
                physical_layout_id='layout'+str(i),image_sha256='f'+str(i),pixel_sha256='p'+str(i),
                image_ahash64=bin(123+i*10000)[2:].zfill(64))

def minimal_fixture():
    nested={}; pins={};imgs={}
    basic=[(f'file_{i}.log',b'x') for i in range(5)]
    for name in sorted(a.REQUIRED_INNER):basic.append((name,b'x'))
    assert len(basic)==16
    for scene in a.SCENES:
        data=sealed(basic)
        nested[scene]=data;pins[scene]=a.sha(data)
    batch=dict(source_sha=a.A15_SHA,exit_code=0,human_approved=False,ground_truth='UNKNOWN_HOLD',scenes={s:{'data_verdict':'PASS'} for s in a.SCENES})
    items=[('batch_status.json',json.dumps(batch).encode())]
    for scene in a.SCENES:
        items.extend([(scene+'/a15_raw.tar.gz',nested[scene]),
                      (scene+'/a15_raw.tar.gz.sha256',(pins[scene]+'  a15_raw.tar.gz\n').encode())])
    items.extend((f'build_{i}.log',b'a') for i in range(6))
    assert len(items)==15
    data=sealed(items)
    return data,(a.sha(data)+'  a15_pilot_evidence.tar.gz\n').encode(),pins

def pose(x=0.,y=0.,z=.55):
    return dict(x=x,y=y,z=z,qx=0.,qy=0.,qz=0.,qw=1.)

def pose_fixture(broken=None):
    t0=300_000_000;end=t0+4_000_000
    track=[]
    for t in range(t0-200_000_000,end+1,a.STEP_NS):
        for i,name in enumerate(a.NAMES):
            z=.55 if name=='tray_platform' else 1.5 if name=='camera' else .70 if name=='dish_01' else .75
            v=pose(z=z);xx=(t-t0)/1e9 if name=='dish_02' and t>t0 else 0.;v['x']=xx
            if broken=='gap' and t==t0+a.STEP_NS and name=='dish_01':continue
            if broken=='outside' and name=='dish_02':v['x']+=.5
            if broken=='early' and name=='dish_02' and t<t0:v['z']+=.03
            if broken=='quat' and name=='dish_01' and t==t0:v['qw']=2.0
            track.append(dict(sim_ns=t,iteration=t//a.STEP_NS,entity=name,entity_id=i+10,**v))
    o=io.StringIO();wr=csv.DictWriter(o,fieldnames=list(track[0]),delimiter='\t');wr.writeheader();wr.writerows(track)
    meta=dict(initial_dishes=[dict(name='dish_01',radius_m=.06,thickness_m=.02),dict(name='dish_02',radius_m=.06,thickness_m=.02)],platform=dict(width_m=.7,depth_m=.56))
    return o.getvalue().encode(),meta,t0,end

def contact_fixture(bad=None):
    topics=['tray','dish_01','dish_02','floor'];start=1_000_000;end=5_000_000
    head='sim_ns\titeration\tdt_ns\ttopic\tmodel\tsensor\tcollision\tsensor_id\tcollision_id\tpresent\tcount\tpairs\tarmed\tpost_state\tlate_control\n'
    lines=[];ros=[]
    for t in range(start+a.STEP_NS,end+a.STEP_NS,a.STEP_NS):
        for i,topic in enumerate(topics):
            if bad=='gap' and t==3_000_000 and topic=='tray':continue
            pairs='1:2' if topic=='tray' and t==2_000_000 else ''
            lines.append(f'{t}\t{t//a.STEP_NS}\t{a.STEP_NS}\t{topic}\t{topic}\tsensor\tcollision\t{i+1}\t{i+1}\t1\t{int(bool(pairs))}\t{pairs}\t1\tPERIODIC\t0\n')
            if pairs:ros.append(dict(topic=topic,sim_time_ns=t,timestamp_source='ROS_CONTACT_HEADER_STAMP',contacts=[dict(collision1_id=1,collision2_id=2)]))
    return (head+''.join(lines)).encode(),('\n'.join(json.dumps(x) for x in ros)+'\n').encode(),topics,start,end

class ArchiveAndPin(unittest.TestCase):
    def test_full_two_layer_sha_and_fixture_provenance(self):
        raw,side,pins=minimal_fixture()
        with patch.object(a,'scene_audit',stub_scene):
            r=a.audit_owner(raw,side,owner_pin=a.sha(raw),inner_pins=pins)
        self.assertTrue(r['actual_owner_raw_directly_recomputed'])
        self.assertEqual(r['outer_manifest_verified'],15)
        self.assertEqual(r['inner_manifests_verified'],64)
        self.assertEqual(r['approved_count'],0)
        self.assertEqual(r['gates']['B-Q04'],'HOLD')
    def test_production_owner_hash_cannot_use_fixture(self):
        raw,side,_=minimal_fixture()
        with self.assertRaisesRegex(a.QAError,'SIDECAR|SHA'):
            a.audit_owner(raw,side)
    def test_wrong_owner_sidecar(self):
        raw,side,_=minimal_fixture()
        with self.assertRaisesRegex(a.QAError,'SIDECAR'):
            a.verify_sidecar(raw,side,b'wrong.tar.gz'.decode(),a.sha(raw))
    def test_archive_modified(self):
        raw,side,_=minimal_fixture()
        with self.assertRaisesRegex(a.QAError,'SHA'):
            a.read_tar(raw,a.sha(raw+b'tampered'))
    def test_manifest_content_tamper(self):
        s=sealed([('x',b'x')]);bad=tgz([('x',b'y'),('SHA256SUMS',(a.sha(b'x')+'  x\n').encode())])
        with self.assertRaisesRegex(a.QAError,'MANIFEST_CONTENT_SHA'):a.read_tar(bad,a.sha(bad))
    def test_traversal_symlink_duplicate_approval(self):
        for name,body in [('../escape',b'x'),('approval_ledger.jsonl',b'x')]:
            v=sealed([(name,body)])
            with self.assertRaises(a.QAError):a.read_tar(v,a.sha(v))
        v=tgz([('x',b'x'),('x',b'x'),('SHA256SUMS',b'')])
        with self.assertRaisesRegex(a.QAError,'TAR_LINK_DUPLICATE'):a.read_tar(v,a.sha(v))
        b=io.BytesIO()
        with tarfile.open(fileobj=b,mode='w:gz') as t:
            m=tarfile.TarInfo('z');m.type=tarfile.SYMTYPE;m.linkname='../secret';t.addfile(m)
        with self.assertRaisesRegex(a.QAError,'TAR_LINK_DUPLICATE'):a.read_tar(b.getvalue(),a.sha(b.getvalue()))
    def test_outer_missing_required(self):
        b=sealed([('batch_status.json',b'{}')])
        with self.assertRaisesRegex(a.QAError,'MANIFEST_COUNT'):a.read_tar(b,a.sha(b))
    def test_disallow_unlisted_member(self):
        raw,_,_=minimal_fixture();b=a.read_tar(raw,a.sha(raw))
        b['unlisted.bin']=b'xx';v=sealed(list(b.items()))
        with self.assertRaisesRegex(a.QAError,'MANIFEST_COUNT|OUTER_UNLISTED_FILE'):a.read_tar(v,a.sha(v))
    def test_sidecar_filename_relative(self):
        with self.assertRaisesRegex(a.QAError,'SIDECAR'):
            a.verify_sidecar(b'x',(a.sha(b'x')+'  /abs/path\n').encode(), 'x',a.sha(b'x'))

class Physical(unittest.TestCase):
    def test_pose_metric_path_exact(self):
        raw,meta,t0,end=pose_fixture()
        r=a.read_pose_grid(raw,meta,t0,end)
        self.assertEqual(r['dish_02']['samples'],5)
        self.assertAlmostEqual(r['dish_02']['cumulative_relative_path_m'],.004,7)
        self.assertAlmostEqual(r['dish_02']['net_relative_displacement_m'],.004,7)
    def test_pose_missing_step(self):
        raw,meta,t0,end=pose_fixture('gap')
        with self.assertRaisesRegex(a.QAError,'POSE_1MS_GRID_GAP'):a.read_pose_grid(raw,meta,t0,end)
    def test_pose_early_move(self):
        raw,meta,t0,end=pose_fixture('early')
        with self.assertRaisesRegex(a.QAError,'PRE_T0_NOT_SETTLED'):a.read_pose_grid(raw,meta,t0,end)
    def test_pose_outside(self):
        raw,meta,t0,end=pose_fixture('outside')
        with self.assertRaisesRegex(a.QAError,'INITIAL_OUTSIDE_TRAY'):a.read_pose_grid(raw,meta,t0,end)
    def test_pose_bad_quat(self):
        raw,meta,t0,end=pose_fixture('quat')
        with self.assertRaisesRegex(a.QAError,'QUATERNION_NORM'):a.read_pose_grid(raw,meta,t0,end)
    def test_relative_tray_inverse_rotation(self):
        q=math.sqrt(.5);tray=dict(x=1,y=2,z=3,qx=0,qy=0,qz=q,qw=q)
        dish=dict(x=1,y=3,z=3,qx=0,qy=0,qz=q,qw=q)
        p,rot=a.relative(tray,dish)
        self.assertAlmostEqual(p[0],1)
        self.assertAlmostEqual(p[1],0)
        self.assertAlmostEqual(rot[3],1)
    def test_trigger_invalid_steps(self):
        with patch.object(a,'PULSE_STEPS',3):
            body=('sim_ns\titeration\tlink_id\ttorque_y_nm\n'+''.join(f'{a.TRIGGER_NS+i*a.STEP_NS}\t{i}\t10\t0.12\n' for i in range(3))).encode()
            self.assertEqual(a.read_trigger(body)['steps'],3)
            with self.assertRaisesRegex(a.QAError,'TRIGGER_COUNT'):a.read_trigger(body.splitlines()[0]+b'\n')
    def test_contacts_valid_partial_not_full(self):
        e,ros,topics,start,end=contact_fixture()
        r=a.read_contact(e,ros,topics,start,end)
        self.assertEqual(r['component_refresh_rows'],16)
        self.assertFalse(r['full_ros_delivery_proven'])
        self.assertEqual(r['positive_same_stamp_subset_stats']['tray']['matched_positive_steps'],1)
    def test_missing_refresh_fails(self):
        e,ros,topics,start,end=contact_fixture('gap')
        with self.assertRaisesRegex(a.QAError,'ECM_WINDOW_LENGTH'):
            a.read_contact(e,ros,topics,start,end)
    def test_invalid_support_pair(self):
        # Exact t0 requires a real positive pair in ECM, not an A report flag.
        h='sim_ns\titeration\tdt_ns\ttopic\tmodel\tsensor\tcollision\tsensor_id\tcollision_id\tpresent\tcount\tpairs\tarmed\tpost_state\tlate_control\n'
        body=h+''.join(f'200000000\t200\t1000000\t{model}\t{model}\ts\tc\t{i}\t{i}\t1\t0\t\t1\tPERIODIC\t0\n' for i,model in enumerate(('tray_platform','dish_01','dish_02'),10))
        valid={'support':{'tray_platform__dish_01':dict(exact_t0_positive=True,last_positive_ns=200000000),
                          'dish_01__dish_02':dict(exact_t0_positive=True,last_positive_ns=200000000)}}
        with self.assertRaisesRegex(a.QAError,'INITIAL_SUPPORT_EXACT_T0'):
            a.initial_support(body.encode(),valid,t0=200000000)

class CLI(unittest.TestCase):
    def test_missing_owner_creates_honest_hold_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'private output'
            ret=main(['--owner',str(Path(d)/'missing.tar.gz'),'--out-dir',str(out)])
            self.assertEqual(ret,2)
            r=json.loads((out/'qa_report.json').read_text())
            self.assertFalse(r['actual_owner_raw_directly_recomputed'])
            self.assertEqual(r['gates']['B-Q01'],'HOLD')
            self.assertFalse((out/'approval_ledger.jsonl').exists())
            self.assertFalse((out/'train_manifest.csv').exists())
            tar=out/'b_a15_qa03_diagnostics.tar.gz';self.assertTrue(tar.is_file())
            self.assertIn(hashlib.sha256(tar.read_bytes()).hexdigest(),(out/(tar.name+'.sha256')).read_text())
            with tarfile.open(tar) as t:
                self.assertEqual(set(t.getnames()),{'qa_report.json','diagnostic_status.json','SHA256SUMS'})
            self.assertEqual(main(['--owner','missing.tar.gz','--out-dir',str(out)]),2)
    def test_wrong_hash_does_not_publish_actual(self):
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d);archive=parent/'a15_pilot_evidence.tar.gz';archive.write_bytes(b'not an Owner file')
            side=parent/(archive.name+'.sha256');side.write_text(a.sha(archive.read_bytes())+'  '+archive.name+'\n')
            out=parent/'out'
            self.assertEqual(main(['--owner',str(archive),'--out-dir',str(out)]),2)
            doc=json.loads((out/'qa_report.json').read_text());self.assertFalse(doc['actual_owner_raw_directly_recomputed'])
            self.assertIn('SHA',doc['first_error'])
    def test_review_rows_not_real_approval(self):
        self.assertEqual(a.review_rows(a.owner_missing_report()),[])
        doc={'actual_owner_raw_directly_recomputed':True,'scenes':[dict(scene_id='L15-01',geometry_family_id='f',physical_layout_id='l',image_sha256='x',capture_ns=2_000_000_000,metrics={'dish_02':dict(cumulative_relative_path_m=0,max_relative_displacement_m=0)})]}
        row=a.review_rows(doc)[0]
        self.assertEqual(row['human_decision'],'')
        self.assertEqual(row['ground_truth'],'NOT_OPERATOR_APPROVED')
    def test_full_diagnostics_do_not_embed_owner_raw(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out';out.mkdir()
            raw=a.owner_missing_report();(out/'qa_report.json').write_text(json.dumps(raw))
            from b_a15_qa_cli import make_diagnostics
            make_diagnostics(out,raw,2)
            with tarfile.open(out/'b_a15_qa03_diagnostics.tar.gz') as t:
                self.assertFalse(any('a15_pilot_evidence' in n or 'raw' in n for n in t.getnames()))

if __name__=='__main__':unittest.main()

class ExtraIdentityAndFOV(unittest.TestCase):
    def test_geometry_family_layout_hash_from_shapes(self):
        import json
        dims=[[.11,.035],[.085,.035]]
        fam=a.sha(json.dumps({'shape':'cylinder_stack_2','dimensions':dims,'mass':.2,'mu':.8},sort_keys=True,separators=(',',':')).encode())
        centers=[[-.05,0,.5675],[-.04,0,.6025]]
        lay=a.sha(json.dumps({'family':fam,'centers':centers},sort_keys=True,separators=(',',':')).encode())
        dishes=[dict(name=f'dish_{i+1:02}',radius_m=dims[i][0],thickness_m=dims[i][1],mass_kg=.2,friction_mu=.8,x=centers[i][0],y=centers[i][1],z=centers[i][2]) for i in range(2)]
        design=dict(initial_dishes=dishes,geometry_family_id=fam,physical_layout_id=lay)
        self.assertEqual(a.geometry_provenance(design)['geometry_family_id'],fam)
        design['physical_layout_id']='bad'
        with self.assertRaisesRegex(a.QAError,'GEOMETRY_FAMILY_LAYOUT_HASH_MISMATCH'):a.geometry_provenance(design)
    def test_fov_box_projection_recomputed_not_occlusion(self):
        t=2_000_000_000
        q=math.sqrt(.5)
        posefields=['sim_ns','entity','x','y','z','qx','qy','qz','qw']
        rows=[dict(sim_ns=t,entity='camera',x=0,y=0,z=1.5,qx=0,qy=q,qz=0,qw=q),
              dict(sim_ns=t,entity='dish_01',x=-.05,y=0,z=.7,qx=0,qy=0,qz=0,qw=1),
              dict(sim_ns=t,entity='dish_02',x=-.04,y=0,z=.75,qx=0,qy=0,qz=0,qw=1)]
        o=io.StringIO();w=csv.DictWriter(o,fieldnames=posefields,delimiter='\t');w.writeheader();w.writerows(rows)
        meta=dict(initial_dishes=[dict(name='dish_01',radius_m=.05,thickness_m=.02),dict(name='dish_02',radius_m=.05,thickness_m=.02)],dishes={})
        info=dict(k=[381.,0,320.,0,381.,240.,0,0,1])
        with self.assertRaisesRegex(a.QAError,'CAMERA_FOV_RECALC_MISMATCH'):a.visibility_geometry(o.getvalue().encode(),meta,{'dishes':{}},info,t0=t)

class ActualSchemaRegression(unittest.TestCase):
    """Synthetic fixtures with the production schema separation; no private raw."""
    def test_fov_separate_design_and_validity_success_and_tamper(self):
        t=2_000_000_000
        q=math.sqrt(.5)
        rows=[dict(sim_ns=t,entity='camera',x=0,y=0,z=1.5,qx=0,qy=q,qz=0,qw=q),
              dict(sim_ns=t,entity='dish_01',x=0,y=0,z=.7,qx=0,qy=0,qz=0,qw=1),
              dict(sim_ns=t,entity='dish_02',x=0,y=0,z=.75,qx=0,qy=0,qz=0,qw=1)]
        o=io.StringIO();w=csv.DictWriter(o,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
        design=dict(initial_dishes=[dict(name=n,radius_m=.05,thickness_m=.02) for n in ('dish_01','dish_02')])
        info=dict(k=[381.,0,320.,0,381.,240.,0,0,1])
        rad=math.hypot(.05,.01)
        validity={'dishes':{}}
        for name,z in [('dish_01',.7),('dish_02',.75)]:
            span=381.*rad/(1.5-z-rad)
            validity['dishes'][name]={'conservative_projected_bbox_px':[320-span,240-span,320+span,240+span]}
        result=a.visibility_geometry(o.getvalue().encode(),design,validity,info,t0=t)
        for name,bounds in result.items():
            for actual,expected in zip(bounds,validity['dishes'][name]['conservative_projected_bbox_px']):
                self.assertAlmostEqual(actual,expected,places=7)
        validity['dishes']['dish_01']['conservative_projected_bbox_px'][0]+=.01
        with self.assertRaisesRegex(a.QAError,'CAMERA_FOV_RECALC_MISMATCH'):
            a.visibility_geometry(o.getvalue().encode(),design,validity,info,t0=t)
    def test_wrong_hash_source_class_distinct_from_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);archive=p/'a15_pilot_evidence.tar.gz';archive.write_bytes(b'not an Owner file')
            (p/(archive.name+'.sha256')).write_text(a.sha(archive.read_bytes())+'  '+archive.name+'\n')
            self.assertEqual(main(['--owner',str(archive),'--out-dir',str(p/'bad')]),2)
            bad=json.loads((p/'bad'/'qa_report.json').read_text())
            self.assertEqual(bad['source_class'],'OWNER_INPUT_PRESENT_VALIDATION_FAILED')
            self.assertEqual(bad['scope'],'B_QA03_OWNER_RAW_VALIDATION_FAILED')
            self.assertTrue(all(x=='HOLD' for x in bad['gates'].values()))
            self.assertEqual(main(['--owner',str(p/'missing.tar.gz'),'--out-dir',str(p/'missing')]),2)
            missing=json.loads((p/'missing'/'qa_report.json').read_text())
            self.assertEqual(missing['source_class'],'OWNER_RAW_NOT_AVAILABLE')
            self.assertFalse(bad['actual_owner_raw_directly_recomputed'])
