"""B A13: success/failure always packages a private bounded review TAR (fixture only)."""
from __future__ import annotations
import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / 'scripts/smartdish_b_real_data_one_shot.sh'
PACKAGER = ROOT / 'ai/scripts/package_a13_diagnostics.py'


def checkout(tmp_path, *, success=False):
    root=tmp_path/'checkout'
    (root/'scripts').mkdir(parents=True)
    (root/'ai/scripts').mkdir(parents=True)
    shutil.copyfile(SHELL,root/'scripts'/SHELL.name)
    shutil.copyfile(PACKAGER,root/'ai/scripts'/PACKAGER.name)
    data=None
    if success:
        # Synthetic, not actual A13. A local copy changes only the expected test SHA.
        data=b'contract-only-test-archive-not-real-A13'
        fake_tar=tmp_path/'test-only-A13.tar.gz'
        fake_tar.write_bytes(data)
        path=root/'scripts'/SHELL.name
        path.write_text(path.read_text().replace(
          'bfc3465448dd34f0cb113fc73b7d07e9ae5c0028c844fd1d3c75f94c6a2f8e6e',
          hashlib.sha256(data).hexdigest()))
        (root/'ai/scripts/import_a13_evidence.py').write_text('''
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--archive');p.add_argument('--output');a=p.parse_args()
r=Path(a.output);(r/'trial_0001').mkdir(parents=True)
(r/'trial_0001/tray_rgb.png').write_bytes(b'FAKE_PNG_TEST_ONLY')
(r/'trial_0001/physics_observations.jsonl').write_text('FAKE_TRACE_TEST_ONLY')
(r/'summary.json').write_text('{"fake_fixture":true}')
print('SMARTDISH_B_A13_INTERNAL_HASH_PASS verified=FIXTURE_ONLY')
''')
        (root/'ai/scripts/extract_a13_candidates.py').write_text('''
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--raw');p.add_argument('--out');p.add_argument('--archive-sha256');a=p.parse_args()
r=Path(a.out);(r/'plots').mkdir(parents=True)
(r/'review.html').write_text('<html>TEST_ONLY<img src="../raw/trial_0001/tray_rgb.png"></html>')
(r/'candidate_manifest.csv').write_text('candidate_id,label_status\\nFIXTURE_ONLY,REVIEW_REQUIRED\\n')
(r/'plots/B13-0123456789abcdefabcd_z.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
print('SMARTDISH_B_REAL_CANDIDATE_EXTRACTION_PASS 1 (FIXTURE_ONLY)')
print('SMARTDISH_B_LABEL_REVIEW_PACKAGE_READY '+str(r/'review.html'))
''')
    subprocess.run(['git','init','-q',str(root)],check=True)
    subprocess.run(['git','-C',str(root),'config','user.email','test@example.invalid'],check=True)
    subprocess.run(['git','-C',str(root),'config','user.name','Test-Only'],check=True)
    subprocess.run(['git','-C',str(root),'add','.'],check=True)
    subprocess.run(['git','-C',str(root),'commit','-qm','fixture'],check=True)
    sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    return root,sha, (tmp_path/'test-only-A13.tar.gz' if success else None)


def run(root,sha,*args):
    env={**os.environ,'HOME':str(root/'fake-home')}
    return subprocess.run(['bash',str(root/'scripts'/SHELL.name),'--sha',sha,*args],
                          cwd=root,env=env,text=True,capture_output=True)


def diagnostics(root):
    folder=root/'ai/data/private/b_a13_diagnostics'
    archives=list(folder.glob('smartdish_b_a13_*_diagnostics.tar.gz'))
    assert len(archives)==1,archives
    a=archives[0]
    assert a.with_name(a.name+'.sha256').is_file()
    assert a.with_name(a.name+'.sha256').read_text().split()[0]==hashlib.sha256(a.read_bytes()).hexdigest()
    with tarfile.open(a,'r:gz') as stream:
        names=stream.getnames()
        assert names[-1]=='SHA256SUMS'
        assert 'diagnostic_status.json' in names and 'execution.log' in names
        sums=stream.extractfile('SHA256SUMS').read().decode()
        for line in sums.splitlines():
            hexdigest,name=line.split('  ',1)
            assert hashlib.sha256(stream.extractfile(name).read()).hexdigest()==hexdigest
        report=json.load(stream.extractfile('diagnostic_status.json'))
        return names,report,stream.extractfile('execution.log').read().decode()


def test_b15_missing_input_still_creates_failure_diagnostics(tmp_path):
    root,sha,_=checkout(tmp_path)
    res=run(root,sha,'--archive','/path/to/example.tar.gz','--mode','review')
    assert res.returncode==3
    assert 'B_A13_ARCHIVE_PLACEHOLDER_PATH' in res.stderr
    assert 'SMARTDISH_B_DIAGNOSTIC_ARCHIVE_CREATED' in res.stdout
    names,report,log=diagnostics(root)
    assert report['status']=='RUN_FAILED' and report['exit_code']==3
    assert 'B_A13_ARCHIVE_PLACEHOLDER_PATH' in log
    assert report['source_archive_sha256'] is None
    assert not (root/'ai/data/private/b_a13_review_').exists()
    assert not any(x.endswith('tray_rgb.png') for x in names)


def test_b15_sha_mismatch_packaged_with_first_failure(tmp_path):
    root,sha,_=checkout(tmp_path)
    wrong=tmp_path/'wrong.tar.gz';wrong.write_bytes(b'bad')
    res=run(root,sha,'--archive',str(wrong))
    assert res.returncode==2
    names,report,log=diagnostics(root)
    assert report['status']=='RUN_FAILED' and 'B10_ARCHIVE_SHA_MISMATCH' in log
    assert 'SMARTDISH_B_A13_INTERNAL_HASH_PASS' not in log
    assert report['source_archive_sha256'] is None
    assert not any(name.endswith('.tar.gz') for name in names)


def test_b15_synthetic_success_archives_review_assets_and_no_approval(tmp_path):
    root,sha,archive=checkout(tmp_path,success=True)
    res=run(root,sha,'--archive',str(archive),'--mode','review')
    assert res.returncode==0,res.stdout+res.stderr
    assert res.stdout.count('SMARTDISH_B_LABEL_REVIEW_PACKAGE_READY')==1
    names,report,log=diagnostics(root)
    assert report['status']=='RUN_SUCCESS' and report['exit_code']==0
    assert report['candidate_review_only'] is True
    assert report['source_archive_sha256']==hashlib.sha256(archive.read_bytes()).hexdigest()
    assert 'raw/trial_0001/tray_rgb.png' in names
    assert 'raw/trial_0001/physics_observations.jsonl' in names
    assert 'review/review.html' in names
    assert 'review/plots/B13-0123456789abcdefabcd_z.svg' in names
    assert not any(x.endswith('approval_ledger.jsonl') or x.endswith('test-only-A13.tar.gz') for x in names)
    assert report['human_approved_labels'] is None


def test_b15_package_no_overwrite_or_leak_of_extra_private_files(tmp_path):
    from sys import path as search
    search.insert(0,str(ROOT/'ai/scripts'))
    from package_a13_diagnostics import package
    log=tmp_path/'log.txt';log.write_text('REDACT_TEST_LOG')
    work=tmp_path/'work';(work/'review/plots').mkdir(parents=True)
    (work/'review/review.html').write_text('review')
    (work/'review/approval_ledger.jsonl').write_text('PRIVATE_NOT_PACKED')
    (work/'review/plots/private-dump.svg').write_text('PRIVATE_NOT_PACKED')
    (work/'review/plots/B13-0123456789abcdefabcd_z.svg').symlink_to(
        work/'review/approval_ledger.jsonl')
    out=tmp_path/'result.tar.gz'
    report=package(log,work,out,0,'test_git_sha')
    assert report['status']=='RUN_SUCCESS'
    with tarfile.open(out,'r:gz') as tf:
        assert 'review/review.html' in tf.getnames()
        assert not any('approval_ledger' in x or 'private-dump' in x or x.endswith('_z.svg') for x in tf.getnames())
    with pytest.raises(ValueError,match='NO_OVERWRITE'):
        package(log,work,out,0,'test_git_sha')


def test_b15_import_failure_keeps_first_error_and_partial_diagnostics(tmp_path):
    root,sha,archive=checkout(tmp_path,success=True)
    # Replace only the test importer's behavior and then commit for SHA pin.
    script=root/'ai/scripts/import_a13_evidence.py'
    script.write_text('''import sys\nprint("B10_TRIAL_FILE_MISSING TEST_ONLY_INJECTED",file=sys.stderr)\nraise SystemExit(9)\n''')
    subprocess.run(['git','-C',str(root),'add','.'],check=True)
    subprocess.run(['git','-C',str(root),'commit','-qm','fixture import failure'],check=True)
    sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    res=run(root,sha,'--archive',str(archive))
    assert res.returncode==9
    assert 'B10_TRIAL_FILE_MISSING TEST_ONLY_INJECTED' in res.stderr
    names,report,log=diagnostics(root)
    assert report['status']=='RUN_FAILED' and report['exit_code']==9
    assert 'B10_TRIAL_FILE_MISSING TEST_ONLY_INJECTED' in log
    assert 'review/review.html' not in names
    assert 'source_archive_sha256' in report and report['source_archive_sha256']==hashlib.sha256(archive.read_bytes()).hexdigest()
