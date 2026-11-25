"""B-DATA-QA-01: contracts only, generated synthetic samples are never real labels."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ai/scripts'))
from audit_b_dacon_qa01 import (stage_audit,QAError,hash_group_leakage,trace_metrics,
                                review_ledger,verified_archive,BASELINE_ID)
from smartdish_b_dacon_qa01_cli import sha_pin

A13='bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e'
SRC='6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def fixture(tmp):
    raw=tmp/'input/raw'; review=tmp/'input/review';review.mkdir(parents=True);raw.mkdir(parents=True)
    rows=[]
    for n,scene in enumerate(('ST-01','ST-02','UN-01','UN-02'),1):
        folder=raw/f'trial_{n:04d}';folder.mkdir()
        Image.new('RGB',(640,480),(20*n,30*n,40*n)).save(folder/'tray_rgb.png')
        with (folder/'physics_observations.jsonl').open('w') as fp:
            for ts,z in [(600_000_000,.59),(5_600_000_000,.59 if n<3 else .30),(10_600_000_000,.59 if n<3 else .05)]:
                fp.write(json.dumps({'sim_ns':ts,'entity':'dish_01','pose':{'x':.0,'y':.0,'z':z}})+'\n')
        (folder/'capture_metadata.json').write_text(json.dumps({'stamp_ns':600_000_000,'encoding':'rgb8','width':640,'height':480,'frame_id':'cam','topic':'/smartdish/tray/image_raw'}))
        (folder/'trial_summary.json').write_text(json.dumps({'source_sha':SRC,'scene_id':scene}))
        (folder/'scenario.scenario.json').write_text(json.dumps({'scene_id':scene,'seed':n}))
        (folder/'sensor_preflight.sdf').write_text('<sdf><world><model><link><sensor name="smartdish_tray_rgb"><pose>0 0 1.5 0 1.57 0</pose><topic>/smartdish/tray/image_raw</topic><gz_frame_id>cam</gz_frame_id><camera><image><width>640</width><height>480</height></image></camera></sensor></link></model></world></sdf>')
        rows.append({'candidate_id':f'B13-{n:020x}','source_scene_id':scene,'trial_id':f'trial_{n:04d}',
                     'seed':n,'stack_id':f'stack-{n}',
                     'suggested_label':'STABLE' if n<3 else 'UNSTABLE',
                     'label_status':'REVIEW_REQUIRED','source_image_path':f'trial_{n:04d}/tray_rgb.png',
                     'source_image_sha256':sha(folder/'tray_rgb.png'),'physics_path':f'trial_{n:04d}/physics_observations.jsonl',
                     'physics_sha256':sha(folder/'physics_observations.jsonl'),'source_archive_sha256':A13,
                     'source_git_sha':SRC,'capture_stamp_ns':'600000000','pose_at_capture_ns':'550000000',
                     'observation_start_ns':'600000000','observation_end_ns':'10600000000',
                     'width':'640','height':'480','encoding':'rgb8'})
    with (review/'candidate_manifest.csv').open('w',newline='') as fp:
        writer=csv.DictWriter(fp,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    return raw,review,rows


def test_qa01_real_contract_synthetic_hold_gates(tmp_path):
    raw,review,_=fixture(tmp_path)
    result=stage_audit(raw,review,tmp_path/'private/qa')
    assert result['overall']=='HOLD'
    assert result['candidate_count']==4 and result['human_approval']['approved']==0
    assert all(x['status']=='HOLD' for x in result['gates'].values())
    assert (tmp_path/'private/qa/representative_product_camera_4_scenes.png').is_file()
    assert not (tmp_path/'private/qa/approval_ledger.jsonl').exists()
    assert not (tmp_path/'private/qa/split_manifest.csv').exists()


def test_qa01_check_synthetic_1_5cm_is_not_gt(tmp_path):
    raw,review,_=fixture(tmp_path);r=stage_audit(raw,review,tmp_path/'qa')
    assert r['dacon_comparison']['candidate_threshold_product_approved'] is False
    assert r['observability']['world_pose_metrics_are_labels'] is False
    with (tmp_path/'qa/physics_trace_metrics.csv').open() as f:rows=list(csv.DictReader(f))
    assert any(float(row['cumulative_world_m'])>0.015 for row in rows)
    assert all(row['has_tray_relative_pose']=='False' for row in rows)


def test_qa01_source_absent_q01_hold(tmp_path):
    raw,review,_=fixture(tmp_path);r=stage_audit(raw,review,tmp_path/'qa')
    assert 'B_Q01_ORIGINAL_TAR_NOT_PROVIDED' in r['gates']['B-Q01']['reasons']


def test_qa01_wrong_archive_sha_never_passes_q01(tmp_path):
    raw,review,_=fixture(tmp_path);p=tmp_path/'not_genuine_A13.tar.gz';p.write_bytes(b'fixture only')
    r=stage_audit(raw,review,tmp_path/'qa',source_archive=p)
    assert r['gates']['B-Q01']['status']=='HOLD'
    assert 'B_Q01_ORIGINAL_ARCHIVE_SHA_MISMATCH' in r['gates']['B-Q01']['reasons']


def test_qa01_hash_tamper_fails_before_publication(tmp_path):
    raw,review,_=fixture(tmp_path)
    (raw/'trial_0001/tray_rgb.png').write_bytes(b'tampered')
    with pytest.raises(QAError,match='B_QA_CANDIDATE_SHA_DRIFT'):
        stage_audit(raw,review,tmp_path/'qa')
    assert not (tmp_path/'qa').exists()


def test_qa01_path_traversal_blocked(tmp_path):
    raw,review,rows=fixture(tmp_path)
    rows[0]['source_image_path']='../../passwd'
    with (review/'candidate_manifest.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    with pytest.raises(QAError,match='B_QA_UNSAFE_RELATIVE_PATH'):
        stage_audit(raw,review,tmp_path/'qa')


def test_qa01_corrupt_pose_fails(tmp_path):
    raw,review,rows=fixture(tmp_path)
    p=raw/'trial_0001/physics_observations.jsonl'
    text=p.read_text().replace('"z": 0.59','"z": "nan"')
    p.write_text(text)
    rows[0]['physics_sha256']=sha(p)
    with (review/'candidate_manifest.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    with pytest.raises(QAError,match='B_Q03_NONFINITE_POSITION'):
        stage_audit(raw,review,tmp_path/'qa')


def test_qa01_output_no_overwrite(tmp_path):
    raw,review,_=fixture(tmp_path);out=tmp_path/'qa';stage_audit(raw,review,out)
    with pytest.raises(QAError,match='OUTPUT_EXISTS'):
        stage_audit(raw,review,out)


def test_qa01_readonly_source(tmp_path):
    raw,review,_=fixture(tmp_path)
    first=sha(raw/'trial_0002/tray_rgb.png');stage_audit(raw,review,tmp_path/'qa')
    assert sha(raw/'trial_0002/tray_rgb.png')==first
    assert not (review/'approval_ledger.jsonl').exists()


def test_qa01_split_geometry_family_hash_overlap(tmp_path):
    rows=[{'candidate_id':'a','split':'train','source_scene_id':'ST-01','stack_id':'g1','source_image_sha256':'abc','pixel_sha256':'zz'},
          {'candidate_id':'b','split':'test','source_scene_id':'ST-01','stack_id':'g2','source_image_sha256':'def','pixel_sha256':'yy'}]
    report=hash_group_leakage(rows)
    assert report['scene_overlaps']==['ST-01']
    assert not report['file_sha_overlaps']


def test_qa01_split_exact_image_overlap(tmp_path):
    rows=[{'candidate_id':'a','split':'train','source_scene_id':'ST-01','stack_id':'g1','source_image_sha256':'same','pixel_sha256':'samepixels'},
          {'candidate_id':'b','split':'test','source_scene_id':'ST-02','stack_id':'g2','source_image_sha256':'same','pixel_sha256':'samepixels'}]
    report=hash_group_leakage(rows)
    assert report['file_sha_overlaps']==['same'] and report['pixel_sha_overlaps']==['samepixels']


def test_qa01_review_ledger_corrupt_fails(tmp_path):
    raw,review,_=fixture(tmp_path)
    (review/'approval_ledger.jsonl').write_text('{"candidate_id":"fake","record_sha256":"bad"}\n')
    with pytest.raises(QAError,match='B_Q04_APPROVAL_LEDGER_INVALID'):
        stage_audit(raw,review,tmp_path/'qa')


def test_qa01_split_manifest_no_auto_pass(tmp_path):
    raw,review,rows=fixture(tmp_path)
    p=tmp_path/'split.csv'
    data=[{k:r[k] for k in ('candidate_id','source_scene_id','stack_id','source_image_sha256')}|{'split':'train' if n<2 else 'test'} for n,r in enumerate(rows)]
    with p.open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=data[0]);w.writeheader();w.writerows(data)
    r=stage_audit(raw,review,tmp_path/'qa',split_manifest=p)
    assert r['gates']['B-Q06']['status']=='HOLD'
    assert r['split_audit']['status']=='PROVIDED'


def test_qa01_reference_document_sha_captured(tmp_path):
    raw,review,_=fixture(tmp_path);baseline=tmp_path/'baseline.md';baseline.write_text('baseline for test only')
    result=stage_audit(raw,review,tmp_path/'qa',baseline=baseline)
    assert result['baseline_sha256']==sha(baseline)


def test_qa01_trace_nonmonotonic_rejected(tmp_path):
    p=tmp_path/'trace.jsonl'
    p.write_text('\n'.join(json.dumps({'sim_ns':600_000_000,'entity':'dish_01','pose':{'x':0,'y':0,'z':0}}) for _ in range(2)))
    with pytest.raises(QAError,match='B_Q03_TIME_NONMONOTONIC'):
        trace_metrics(p,600_000_000,600_000_000)


def test_qa01_no_source_archive_approved_by_simulated_marker(tmp_path):
    raw,review,rows=fixture(tmp_path)
    (raw/'summary.json').write_text('{"source_archive_sha256":"'+A13+'","verified":88}')
    r=stage_audit(raw,review,tmp_path/'qa')
    assert r['gates']['B-Q01']['status']=='HOLD'


def test_qa01_no_mutation_on_ledger(tmp_path):
    raw,review,rows=fixture(tmp_path)
    before=(review/'candidate_manifest.csv').read_bytes()
    stage_audit(raw,review,tmp_path/'qa')
    assert (review/'candidate_manifest.csv').read_bytes()==before


def checkout(tmp):
    root=tmp/'checkout (B QA)'
    for name in ('ai/scripts/audit_b_dacon_qa01.py','ai/scripts/smartdish_b_dacon_qa01_cli.py',
                 'scripts/smartdish_b_dacon_qa01_one_shot.sh'):
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    (root/'docs/quality').mkdir(parents=True)
    (root/'docs/quality/SMARTDISH_B_DACON_DATA_QUALITY_BASELINE_20261125_KO.md').write_text('fixture baseline')
    subprocess.run(['git','init','-q',str(root)],check=True)
    subprocess.run(['git','-C',str(root),'config','user.email','test@invalid.example'],check=True)
    subprocess.run(['git','-C',str(root),'config','user.name','Test'],check=True)
    subprocess.run(['git','-C',str(root),'add','.'],check=True)
    subprocess.run(['git','-C',str(root),'commit','-qm','fixture'],check=True)
    sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    return root,sha


def cli(root,sha,cwd,*args):
    return subprocess.run(['bash',str(root/'scripts/smartdish_b_dacon_qa01_one_shot.sh'),'--sha',sha,*args],
                          cwd=cwd,text=True,capture_output=True)


def check_diag(root):
    base=root/'ai/data/private/b_dacon_qa01';folders=list(base.iterdir());assert len(folders)==1
    archive=folders[0]/'b_dacon_qa01_diagnostics.tar.gz';side=Path(str(archive)+'.sha256')
    assert sha(archive)==side.read_text().split('  ',1)[0]
    with tarfile.open(archive,'r:gz') as t:
        files={name:t.extractfile(name).read() for name in t.getnames()}
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256(files[name]).hexdigest()==digest
    return files,json.loads(files['diagnostic_status.json'])

@pytest.mark.parametrize('cwd_variant',('root','elsewhere','space'))
def test_qa01_cli_cwd_independent_with_diagnostic(tmp_path,cwd_variant):
    root,sha0=checkout(tmp_path);raw,review,_=fixture(tmp_path/'evidence')
    cwd={'root':root,'elsewhere':tmp_path,'space':(tmp_path/'cwd with (x)')}[cwd_variant]
    cwd.mkdir(exist_ok=True)
    r=cli(root,sha0,cwd,'--workspace',str(raw.parent))
    assert r.returncode==0,r.stdout+r.stderr
    assert 'B-Q01=HOLD' in r.stdout and 'B-Q04=HOLD' in r.stdout
    files,status=check_diag(root)
    assert status['run_status']=='AUDIT_COMPLETED' and status['quality_verdict']=='HOLD'
    assert 'qa/qa_report.json' in files
    assert 'qa/representative_product_camera_4_scenes.png' in files
    assert not any('approval_ledger' in x for x in files)


def test_qa01_cli_sha_mismatch_diagnostic(tmp_path):
    root,sha0=checkout(tmp_path);r=cli(root,'0'*40,tmp_path)
    assert r.returncode==2 and 'B_QA_CODE_SHA_PIN_MISMATCH' in r.stderr
    assert check_diag(root)[1]['run_status']=='RUN_FAILED'


def test_qa01_cli_missing_workspace_failure_archive(tmp_path):
    root,sha0=checkout(tmp_path);r=cli(root,sha0,tmp_path)
    assert r.returncode==2 and 'B_QA_WORKSPACE_NOT_FOUND' in r.stderr
    assert check_diag(root)[1]['exit_code']==2


def test_qa01_cli_help_and_shell_syntax():
    subprocess.run(['bash','-n',str(ROOT/'scripts/smartdish_b_dacon_qa01_one_shot.sh')],check=True)
    r=subprocess.run(['bash',str(ROOT/'scripts/smartdish_b_dacon_qa01_one_shot.sh'),'--help'],capture_output=True,text=True)
    assert r.returncode==0 and '--source-archive' in r.stdout


def test_qa01_cli_wrong_original_tar_q01_hold(tmp_path):
    root,sha0=checkout(tmp_path);raw,review,_=fixture(tmp_path/'evidence')
    p=tmp_path/'a13_fake.tar.gz';p.write_bytes(b'not real')
    r=cli(root,sha0,tmp_path,'--workspace',str(raw.parent),'--source-archive',str(p))
    assert r.returncode==0 and 'B-Q01=HOLD' in r.stdout
    files,status=check_diag(root)
    qa=json.loads(files['qa/qa_report.json'])
    assert 'B_Q01_ORIGINAL_ARCHIVE_SHA_MISMATCH' in qa['gates']['B-Q01']['reasons']


def test_qa01_cli_does_not_kill_caller_shell(tmp_path):
    root,sha0=checkout(tmp_path)
    command=f'bash "{root}/scripts/smartdish_b_dacon_qa01_one_shot.sh" --sha {sha0} --workspace /nonexistent; echo PARENT_SHELL_ALIVE'
    r=subprocess.run(['bash','-c',command],cwd=tmp_path,capture_output=True,text=True)
    assert 'PARENT_SHELL_ALIVE' in r.stdout


def test_qa01_camera_sdf_restored_from_sha_verified_full_a13_tar(tmp_path,monkeypatch):
    """Synthetic-only contract: absent B12R subset SDF must not hide A's original SDF."""
    import audit_b_dacon_qa01 as audit
    raw,review,rows=fixture(tmp_path)
    tar_path=tmp_path/'synthetic_full_a13.tar.gz'
    index={}
    with tarfile.open(tar_path,'w:gz') as archive:
        for n in range(1,5):
            name=f'trial_{n:04d}/sensor_preflight.sdf'
            bs=(raw/name).read_bytes()
            index[name]=hashlib.sha256(bs).hexdigest()
            meta=tarfile.TarInfo(name);meta.size=len(bs)
            archive.addfile(meta,io.BytesIO(bs))
            (raw/name).unlink()
    for row in rows:
        index[row['source_image_path']]=row['source_image_sha256']
        index[row['physics_path']]=row['physics_sha256']
    # The actual verified_archive() performs full A13 SHA and 88-member checks.
    # This monkeypatch injects a trusted synthetic member index only for camera fallback.
    monkeypatch.setattr(audit,'verified_archive',lambda path:{'status':'PASS','source_archive_sha256':'SYNTHETIC_ONLY','verified_members':len(index),'_member_sha256':index})
    result=stage_audit(raw,review,tmp_path/'qa',source_archive=tar_path)
    assert result['gates']['B-Q01']['status']=='PASS'
    assert 'B_Q02_CAMERA_POSE_MISSING' not in result['gates']['B-Q02']['reasons']
    assert result['gates']['B-Q02']['status']=='HOLD'
    with (tmp_path/'qa/camera_metadata.csv').open(newline='') as f: cameras=list(csv.DictReader(f))
    assert len(cameras)==4
    assert all(c['camera_pose_source']=='VERIFIED_A13_TAR_SENSOR_PREFLIGHT_SDF' for c in cameras)
    assert all(c['camera_pose_sdf']=='0 0 1.5 0 1.57 0' for c in cameras)
    assert all(c['camera_pose_scope']=='STATIC_SENSOR_SDF_LOCAL_POSE_NOT_OBSERVED_DYNAMIC_TF' for c in cameras)
    assert not any((raw/f'trial_{n:04d}/sensor_preflight.sdf').exists() for n in range(1,5))


def test_qa01_camera_sdf_tampering_does_not_publish(tmp_path,monkeypatch):
    import audit_b_dacon_qa01 as audit
    raw,review,rows=fixture(tmp_path)
    tar_path=tmp_path/'synthetic_camera_sdf.tar.gz'
    with tarfile.open(tar_path,'w:gz') as archive:
        name='trial_0001/sensor_preflight.sdf'
        bs=(raw/name).read_bytes();meta=tarfile.TarInfo(name);meta.size=len(bs)
        archive.addfile(meta,io.BytesIO(bs))
    fake_index={'trial_0001/sensor_preflight.sdf':'0'*64}
    for row in rows:
        fake_index[row['source_image_path']]=row['source_image_sha256']
        fake_index[row['physics_path']]=row['physics_sha256']
    monkeypatch.setattr(audit,'verified_archive',lambda path:{'status':'PASS','_member_sha256':fake_index})
    with pytest.raises(QAError,match='B_Q02_CAMERA_SDF_HASH_DRIFT'):
        stage_audit(raw,review,tmp_path/'qa',source_archive=tar_path)
    assert not (tmp_path/'qa').exists()


def test_qa01_recommended_60_is_not_an_approval_gate(tmp_path):
    raw,review,_=fixture(tmp_path)
    report=stage_audit(raw,review,tmp_path/'qa')
    assert 'B_Q05_PILOT_60_SCENES_NONBINDING_RECOMMENDATION_GAP' in report['nonbinding_advisories']
    assert not any('60_SCENES' in reason for reason in report['gates']['B-Q05']['reasons'])
    assert 'B_Q05_GEOMETRY_ENVIRONMENT_CROSS_COVERAGE_NOT_DEMONSTRATED' in report['gates']['B-Q05']['reasons']
