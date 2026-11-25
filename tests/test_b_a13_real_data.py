"""Synthetic A13-shaped CONTRACT_ONLY archive. NEVER label as owner evidence or train on it."""
import csv
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path
from PIL import Image
import pytest

SCRIPTS=Path(__file__).parents[1]/'ai/scripts'
sys.path.insert(0,str(SCRIPTS))
from import_a13_evidence import import_archive,sha256,EvidenceError,SOURCE_SHA
from extract_a13_candidates import create_review,audit_trial,trace_audit
from review_a13_labels import record_review,load_ledger,load_candidates
from register_a13_approved import stage_approved


def write(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(content,sort_keys=True)+'\n' if isinstance(content,(dict,list)) else content)


def make_fixture(tmp_path):
    src=tmp_path/'fake_a13_input';src.mkdir()
    scene_names=('ST-01','ST-02','UN-01','UN-02')
    rows=[]
    for i,scene in enumerate(scene_names,1):
        t=src/f'trial_{i:04d}';t.mkdir()
        Image.new('RGB',(640,480),(i*30,90,100)).save(t/'tray_rgb.png')
        dishes={f'dish_{j:02d}':{'x':round((j-1)*(.03*i),5),'y':0.,
                 'z':.60,'qx':0.,'qy':0.,'qz':0.,'qw':1.,'tilt_deg':0.} for j in range(1,3)}
        fallen=scene.startswith('UN')
        after={n:dict(p,z=.15 if fallen else .60) for n,p in dishes.items()}
        trial=f'TRIAL_{i}'
        initial_dishes=[dict(name=n,x=p['x'],y=p['y'],z=p['z'],roll=0.,pitch=0.,
                             radius_m=.1,thickness_m=.035) for n,p in dishes.items()]
        write(t/'scenario.scenario.json',{'scene_id':scene,'trial_id':trial,
                 'seed':100+i,'platform':{'top_z_m':.57},'initial_dishes':initial_dishes})
        write(t/'scenario.sdf','<sdf version="1.9"/>\n')
        write(t/'capture_metadata.json',{'ground_truth':'NOT_OBSERVED',
              'image_sha256':sha256(t/'tray_rgb.png')})
        write(t/'initial_state.json',{'stamp_ns':600000000,'pose_stamp_ns':550000000,'dishes':dishes})
        write(t/'final_state.json',{'observation_end_ns':10650000000,'dishes':after})
        physical=[]
        for n in sorted(dishes):
            for ns,pose in ((550000000,dishes[n]),(650000000,dishes[n]),(10650000000,after[n])):
                physical.append({'sim_ns':ns,'entity':n,'pose':pose,'source':'CONTRACT_ONLY_TEST'})
        (t/'physics_observations.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in physical))
        write(t/'process_cleanup.json',{'all_owned_processes_stopped':True})
        motion={'observation':'FALL_OBSERVED' if fallen else 'HELD_OBSERVED',
                'per_dish':[{'name':n,'drop_m':.45 if fallen else 0} for n in dishes]}
        row={'trial_id':trial,'scene_id':scene,'seed':100+i,'source_sha':SOURCE_SHA,
            'sensor_physics_verdict':'PASS','gui_verdict':'PASS',
            'gui_active_during_physics':True,'label':'REVIEW_REQUIRED',
            'ground_truth':'NOT_OPERATOR_APPROVED',
            'image_sha256':sha256(t/'tray_rgb.png'),
            'physics_sha256':sha256(t/'physics_observations.jsonl'),
            'physics_size_bytes':(t/'physics_observations.jsonl').stat().st_size,
            'capture_stamp_ns':600000000,'pose_at_capture_ns':550000000,
            'observation_start_ns':650000000,'observation_end_ns':10650000000,
            'image_stamp_samples':[200000000,400000000,600000000,800000000],
            'width':640,'height':480,'encoding':'rgb8','image_received_count':4,'motion':motion}
        write(t/'trial_summary.json',row);rows.append(row)
    write(src/'source_manifest.json',{'source_sha':SOURCE_SHA})
    write(src/'deployment_gate_manifest.json',{'source_sha':SOURCE_SHA,
                      'status':'REAL_WSLG_SMOKE_PASS',
                      'gui_preflight':{'verdict':'GAZEBO_GUI_PROCESS_STABLE_NO_GLX_ERROR'},
                      'smoke':{'verdict':'REAL_WSLG_SMOKE_PASS','archive_sha256':'a'*64}})
    write(src/'summary.json',{'source_sha':SOURCE_SHA,'mode':'batch','gui':True,
                'verdict':'GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS','first_error':None,
                'trials':rows})
    entries=[]
    for f in sorted(x for x in src.rglob('*') if x.is_file()):
        entries.append(sha256(f)+'  '+f.relative_to(src).as_posix())
    (src/'SHA256SUMS').write_text('\n'.join(entries)+'\n')
    archive=tmp_path/'test-only-no-real-data.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(x for x in src.rglob('*') if x.is_file()):
            tar.add(p,arcname=p.relative_to(src).as_posix())
    return src,archive


def imported(tmp_path):
    src,archive=make_fixture(tmp_path)
    root=tmp_path/'raw'
    result=import_archive(archive,root,expected_archive=sha256(archive),expected_count=None)
    # This helper returns TEST-ONLY mutable copies for negative tampering tests.
    # Production import_archive() keeps all verified raw files mode 0444.
    for path in root.rglob('*'):
        if path.is_file():
            path.chmod(0o600)
    return root,archive,result


def test_b10_import_verified_contract_only(tmp_path):
    root,archive,result=imported(tmp_path)
    assert result['trial_count']==4 and result['ground_truth_approved'] is False
    assert [r['scene_id'] for r in result['trials']]==['ST-01','ST-02','UN-01','UN-02']
    assert (root/'SHA256SUMS').is_file()


def test_b10_expected_tar_sha_fails_closed(tmp_path):
    _,archive=make_fixture(tmp_path)
    with pytest.raises(EvidenceError,match='B10_ARCHIVE_SHA_MISMATCH'):
        import_archive(archive,tmp_path/'out',expected_archive='0'*64,expected_count=None)
    assert not (tmp_path/'out').exists()


def rearchive(src,archive):
    lines=[]
    for f in sorted(x for x in src.rglob('*') if x.is_file() and x.name!='SHA256SUMS'):
        lines.append(sha256(f)+'  '+f.relative_to(src).as_posix())
    (src/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(x for x in src.rglob('*') if x.is_file()):
            tar.add(p,arcname=p.relative_to(src).as_posix())


def test_b10_file_sha_mismatch_blocks(tmp_path):
    src,archive=make_fixture(tmp_path)
    (src/'trial_0001/tray_rgb.png').write_bytes(b'changed')
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(x for x in src.rglob('*') if x.is_file()):
            tar.add(p,arcname=p.relative_to(src).as_posix())
    with pytest.raises(EvidenceError,match='B10_INTERNAL_SHA_MISMATCH'):
        import_archive(archive,tmp_path/'out',expected_archive=sha256(archive),expected_count=None)


def test_b10_member_set_unlisted_file_rejected(tmp_path):
    src,archive=make_fixture(tmp_path)
    write(src/'not_listed.txt','oops')
    with tarfile.open(archive,'w:gz') as tar:
        for p in sorted(x for x in src.rglob('*') if x.is_file()):
            tar.add(p,arcname=p.relative_to(src).as_posix())
    with pytest.raises(EvidenceError,match='B10_INTERNAL_FILE_SET_MISMATCH'):
        import_archive(archive,tmp_path/'out',expected_archive=sha256(archive),expected_count=None)

@pytest.mark.parametrize('unsafe', ['../escape','/absolute','trial/../../bad'])
def test_b10_unsafe_tar_member_rejected(tmp_path,unsafe):
    _,archive=make_fixture(tmp_path)
    with tarfile.open(tmp_path/'unsafe.tar','w:gz') as unused:
        info=tarfile.TarInfo(unsafe);data=b'test';info.size=len(data);unused.addfile(info,io.BytesIO(data))
    tarpath=tmp_path/'unsafe.tar'
    with pytest.raises(EvidenceError,match='B10_ARCHIVE_UNSAFE_PATH'):
        import_archive(tarpath,tmp_path/'out',expected_archive=sha256(tarpath),expected_count=None)


def test_b10_symlink_tar_forbidden(tmp_path):
    t=tmp_path/'unsafe.tar'
    with tarfile.open(t,'w:gz') as tar:
        info=tarfile.TarInfo('link');info.type=tarfile.SYMTYPE;info.linkname='../../x';tar.addfile(info)
    with pytest.raises(EvidenceError,match='B10_ARCHIVE_LINK_OR_SPECIAL_FORBIDDEN'):
        import_archive(t,tmp_path/'out',expected_archive=sha256(t),expected_count=None)


def test_b10_mixed_source_sha_rejected(tmp_path):
    src,archive=make_fixture(tmp_path)
    f=src/'trial_0004/trial_summary.json';row=json.loads(f.read_text());row['source_sha']='0'*40
    write(f,row);rearchive(src,archive)
    with pytest.raises(EvidenceError,match='B10_TRIAL_PROVENANCE_MISMATCH'):
        import_archive(archive,tmp_path/'out',expected_archive=sha256(archive),expected_count=None)


def test_b10_failed_trial_rejected(tmp_path):
    src,archive=make_fixture(tmp_path)
    f=src/'trial_0004/trial_summary.json';row=json.loads(f.read_text());row['gui_verdict']='FAIL'
    write(f,row);rearchive(src,archive)
    with pytest.raises(EvidenceError,match='B10_TRIAL_NOT_ACCEPTED'):
        import_archive(archive,tmp_path/'out',expected_archive=sha256(archive),expected_count=None)


def test_b11_candidates_trace_and_review_material(tmp_path):
    root,archive,_=imported(tmp_path);out=tmp_path/'review'
    details=create_review(root,out,sha256(archive),expected_members=None)
    assert len(details)==4
    assert [x['candidate']['suggested_label'] for x in details]==['STABLE','STABLE','UNSTABLE','UNSTABLE']
    assert all(x['candidate']['label_status']=='REVIEW_REQUIRED' for x in details)
    assert (out/'review.html').is_file() and len(list((out/'plots').glob('*.svg')))==12


def test_b11_jsonl_corrupt_and_temporal_invalid(tmp_path):
    root,archive,_=imported(tmp_path)
    f=root/'trial_0001/physics_observations.jsonl';f.write_text('{\n')
    with pytest.raises(EvidenceError,match='B11_JSONL_CORRUPT'):
        audit_trial(root,'trial_0001',sha256(archive))


def test_b11_nonfinite_and_rewind_rejected(tmp_path):
    root,archive,_=imported(tmp_path);f=root/'trial_0001/physics_observations.jsonl'
    data=[json.loads(x) for x in f.read_text().splitlines()]
    data[0]['pose']['z']=float('nan')
    f.write_text('\n'.join(json.dumps(x) for x in data)+'\n')
    with pytest.raises(EvidenceError,match='B11_NONFINITE_POSE'):
        audit_trial(root,'trial_0001',sha256(archive))
    data[0]['pose']['z']=.6
    data[1]['sim_ns']=data[0]['sim_ns']
    f.write_text('\n'.join(json.dumps(x) for x in data)+'\n')
    with pytest.raises(EvidenceError,match='B11_ENTITY_TIME_REWIND'):
        audit_trial(root,'trial_0001',sha256(archive))


def test_b12_unapproved_candidate_not_in_release(tmp_path):
    raw,archive,_=imported(tmp_path);rv=tmp_path/'review'
    create_review(raw,rv,sha256(archive),expected_members=None)
    report=stage_approved(raw,rv,tmp_path/'release')
    assert report['approved_samples']==0 and report['verdict']=='B_LABEL_APPROVAL_PENDING'


def test_b12_explicit_human_approval_and_sha_binding(tmp_path):
    raw,archive,_=imported(tmp_path);rv=tmp_path/'review'
    create_review(raw,rv,sha256(archive),expected_members=None)
    candidate=next(iter(load_candidates(rv).values()))
    with pytest.raises(EvidenceError,match='B12_EXPLICIT_REVIEWER_AND_REASON_REQUIRED'):
        record_review(rv,raw,candidate['candidate_id'],'','APPROVED','why','OWNED','STABLE')
    with pytest.raises(EvidenceError,match='B12_APPROVAL_LABEL_LICENSE_REQUIRED'):
        record_review(rv,raw,candidate['candidate_id'],'tester','APPROVED','why','UNVERIFIED','STABLE')
    row=record_review(rv,raw,candidate['candidate_id'],'human-test-only','DEFERRED','needs inspection','UNVERIFIED')
    assert row['decision']=='DEFERRED' and len(load_ledger(rv/'approval_ledger.jsonl'))==1
    report=stage_approved(raw,rv,tmp_path/'release')
    assert report['approved_samples']==0 and report['deferred']==1


def test_b12_approval_hash_drift_rejected(tmp_path):
    raw,archive,_=imported(tmp_path);rv=tmp_path/'review'
    create_review(raw,rv,sha256(archive),expected_members=None)
    cand=next(iter(load_candidates(rv).values()))
    record_review(rv,raw,cand['candidate_id'],'human-test-only','APPROVED','reviewed','OWNED','STABLE')
    ledger=rv/'approval_ledger.jsonl'
    ledger.write_text(ledger.read_text().replace('STABLE','UNSTABLE'))
    with pytest.raises(EvidenceError,match='B12_APPROVAL_LEDGER_SHA_MISMATCH'):
        load_ledger(ledger)


def test_b12_approval_source_image_changed_rejected(tmp_path):
    raw,archive,_=imported(tmp_path);rv=tmp_path/'review'
    create_review(raw,rv,sha256(archive),expected_members=None)
    cand=next(iter(load_candidates(rv).values()))
    (raw/cand['source_image_path']).write_bytes(b'tampered')
    with pytest.raises(EvidenceError,match='B12_CANDIDATE_SHA_DRIFT'):
        record_review(rv,raw,cand['candidate_id'],'human-test-only','APPROVED','review','OWNED','STABLE')

@pytest.mark.skipif(not (SCRIPTS/'collect_tableware.py').is_file(),reason='Existing B collector only in GitHub checkout')
def test_b13_approved_contract_integrates_real_existing_collector(tmp_path):
    # Test-only operator input against synthetic evidence; NOT an actual human approval.
    raw,archive,_=imported(tmp_path);rv=tmp_path/'review';create_review(raw,rv,sha256(archive),expected_members=None)
    candidates=load_candidates(rv)
    c=next(iter(candidates.values()))
    record_review(rv,raw,c['candidate_id'],'TEST_ACTOR_CONTRACT_ONLY','APPROVED',
                  'SYNTHETIC TEST LABEL NOT REAL','OWNED','STABLE')
    out=tmp_path/'release'
    report=stage_approved(raw,rv,out,b_ref=SOURCE_SHA)
    assert report['approved_samples']==1
    assert report['verdict']=='B_DATASET_SPLIT_BLOCKED'
    from prepare_dataset import load_manifest
    rows=load_manifest(out/'ai/data/manifest.csv')
    cfg=json.loads(rows[0]['capture_config'])
    assert cfg['approval_record_sha256']==load_ledger(rv/'approval_ledger.jsonl')[0]['record_sha256']
    assert not Path(cfg['physics_evidence']).is_absolute()
    assert (out/cfg['physics_evidence']).is_file()
    assert (out/'source_evidence/approval_ledger.jsonl').is_file()
    assert not (out/'ai/data/split_manifest.csv').exists()


@pytest.mark.skipif(not (SCRIPTS/'collect_tableware.py').is_file(),reason='Existing B collector only in GitHub checkout')
def test_b13_mismatched_approval_candidate_sha_fails(tmp_path):
    raw,archive,_=imported(tmp_path);rv=tmp_path/'review';create_review(raw,rv,sha256(archive),expected_members=None)
    c=next(iter(load_candidates(rv).values()))
    record_review(rv,raw,c['candidate_id'],'TEST_ACTOR_CONTRACT_ONLY','APPROVED','SYNTHETIC_TEST','OWNED','STABLE')
    with (rv/'candidate_manifest.csv').open(newline='') as fp:
        rows=list(csv.DictReader(fp));fields=rows[0].keys()
    rows[0]['physics_sha256']='0'*64
    with (rv/'candidate_manifest.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=fields);w.writeheader();w.writerows(rows)
    with pytest.raises(EvidenceError,match='B13_APPROVAL_HASH_BINDING_BROKEN'):
        stage_approved(raw,rv,tmp_path/'release',b_ref=SOURCE_SHA)

@pytest.mark.skipif(not (SCRIPTS/'collect_tableware.py').is_file(),reason='Existing B collector only in GitHub checkout')
def test_b14_release_portable_sha_verifier_and_tamper(tmp_path):
    from verify_b_real_release import verify_release
    raw,archive,_=imported(tmp_path);rv=tmp_path/'review';create_review(raw,rv,sha256(archive),expected_members=None)
    c=next(iter(load_candidates(rv).values()))
    record_review(rv,raw,c['candidate_id'],'TEST_ACTOR_CONTRACT_ONLY','APPROVED','SYNTHETIC_TEST','OWNED','STABLE')
    release=tmp_path/'release'
    stage_approved(raw,rv,release,b_ref=SOURCE_SHA)
    report=verify_release(release)
    assert report['approved_count']==1
    (release/'source_evidence/physics'/f"{c['candidate_id']}.jsonl").write_text('tampered')
    with pytest.raises(EvidenceError,match='B14_RELEASE_SHA_MISMATCH'):
        verify_release(release)

def test_b11_first_image_after_material_drop_is_review_required(tmp_path):
    raw,archive,_=imported(tmp_path)
    f=raw/'trial_0001/scenario.scenario.json';row=json.loads(f.read_text())
    row['initial_dishes'][0]['z']=1.2
    write(f,row)
    audit=audit_trial(raw,'trial_0001',sha256(archive))
    assert audit['candidate']['temporal_review']=='TEMPORAL_REVIEW_REQUIRED'
    assert audit['candidate']['suggested_label']=='REVIEW_REQUIRED'


def test_b11_missing_entity_refused(tmp_path):
    raw,archive,_=imported(tmp_path)
    file=raw/'trial_0001/physics_observations.jsonl'
    trace=[json.loads(line) for line in file.read_text().splitlines()]
    file.write_text(''.join(json.dumps(x)+'\n' for x in trace if x['entity']=='dish_01'))
    with pytest.raises(EvidenceError,match='B11_MISSING_DISH_ENTITY'):
        audit_trial(raw,'trial_0001',sha256(archive))


def test_b12_temporal_candidate_never_auto_approved(tmp_path):
    raw,archive,_=imported(tmp_path);rv=tmp_path/'review'
    create_review(raw,rv,sha256(archive),expected_members=None)
    manifest=rv/'candidate_manifest.csv'
    with manifest.open(newline='') as fp:rows=list(csv.DictReader(fp));fields=list(rows[0])
    rows[0]['temporal_review']='TEMPORAL_REVIEW_REQUIRED'
    with manifest.open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=fields);w.writeheader();w.writerows(rows)
    with pytest.raises(EvidenceError,match='B12_TEMPORAL_OR_PHYSICS_REVIEW_REQUIRED'):
        record_review(rv,raw,rows[0]['candidate_id'],'TEST_ONLY', 'APPROVED','reviewed','OWNED','STABLE')


def test_b10_duplicate_tar_path_rejected(tmp_path):
    t=tmp_path/'duplicate.tar.gz'
    with tarfile.open(t,'w:gz') as tar:
        for i in range(2):
            data=b'same';info=tarfile.TarInfo('summary.json');info.size=len(data)
            tar.addfile(info,io.BytesIO(data))
    with pytest.raises(EvidenceError,match='B10_ARCHIVE_DUPLICATE_MEMBER'):
        import_archive(t,tmp_path/'out',expected_archive=sha256(t),expected_count=None)


def test_b10_9s_min_limit_underflow_rejected(tmp_path):
    src,archive=make_fixture(tmp_path)
    rowfile=src/'trial_0001/trial_summary.json';row=json.loads(rowfile.read_text())
    row['observation_end_ns']=8_000_000_000
    write(rowfile,row);rearchive(src,archive)
    with pytest.raises(EvidenceError,match='B10_TEMPORAL_CONTRACT_FAIL'):
        import_archive(archive,tmp_path/'out',expected_archive=sha256(archive),expected_count=None)

def test_b10_real_import_preserves_readonly_verified_bytes(tmp_path):
    _,archive=make_fixture(tmp_path)
    dest=tmp_path/'immutable_raw'
    import_archive(archive,dest,expected_archive=sha256(archive),expected_count=None)
    assert (dest/'trial_0001/tray_rgb.png').stat().st_mode & 0o222 == 0
