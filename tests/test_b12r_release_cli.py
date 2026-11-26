"""B12R CLI ship gate: execute the exact bash command in a separate process.

All archives in CI are synthetic contracts, never genuine A-13/Gazebo evidence.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
from test_b12_receive_diagnostics import pack as original_pack

ROOT=Path(__file__).resolve().parents[1]
SH=ROOT/'scripts/smartdish_b12r_one_shot.sh'
RUN=ROOT/'ai/scripts/smartdish_b12r_cli.py'
RECEIVE=ROOT/'ai/scripts/receive_b15_diagnostics.py'
AUDIT=ROOT/'ai/scripts/audit_a13_independent_groups.py'


def pack(tmp,mutate=None,**kwargs):
    """Extend old B12 receiver fixture with B14-required seed field."""
    def enrich(files):
        stream=io.StringIO(files['review/candidate_manifest.csv'].decode())
        rows=list(csv.DictReader(stream)); fields=list(rows[0]);
        if 'seed' not in fields: fields.append('seed')
        for row in rows: row['seed']='101'
        out=io.StringIO();w=csv.DictWriter(out,fieldnames=fields);w.writeheader();w.writerows(rows)
        files['review/candidate_manifest.csv']=out.getvalue().encode()
        if mutate:mutate(files)
    return original_pack(tmp,mutate=enrich,**kwargs)


def checkout(tmp):
    root=tmp/'local checkout (spaces)'
    for source in (SH,RUN,RECEIVE,AUDIT,ROOT/'scripts/smartdish_platform/runtime.py'):
        p=root/source.relative_to(ROOT)
        p.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,p)
    subprocess.run(['git','init','-q',str(root)],check=True)
    subprocess.run(['git','-C',str(root),'config','user.email','fixture@invalid.test'],check=True)
    subprocess.run(['git','-C',str(root),'config','user.name','Contract Test Only'],check=True)
    subprocess.run(['git','-C',str(root),'add','.'],check=True)
    subprocess.run(['git','-C',str(root),'commit','-qm','fixture'],check=True)
    sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    return root,sha


def run_cli(root,sha,cwd,*arguments):
    return subprocess.run(['bash',str(root/'scripts'/SH.name),'--sha',sha,*arguments],
                          cwd=cwd,env={**os.environ,'HOME':str(cwd)},text=True,capture_output=True)


def outcome(root):
    archives=list((root/'ai/data/private/b12r_diagnostics').glob('*_diagnostics.tar.gz'))
    assert len(archives)==1,archives
    archive=archives[0];side=Path(str(archive)+'.sha256')
    assert side.is_file()
    assert side.read_text().split('  ',1)[0]==hashlib.sha256(archive.read_bytes()).hexdigest()
    with tarfile.open(archive,'r:gz') as tf:
        members=tf.getnames()
        assert members[-1]=='SHA256SUMS'
        sums=tf.extractfile('SHA256SUMS').read().decode().splitlines()
        assert len(sums)==len(members)-1
        for line in sums:
            sig,rel=line.split('  ',1)
            assert hashlib.sha256(tf.extractfile(rel).read()).hexdigest()==sig
        status=json.loads(tf.extractfile('diagnostic_status.json').read())
        return members,status,tf.extractfile('execution.log').read().decode()


def test_b12r_ship_shell_and_help():
    subprocess.run(['bash','-n',str(SH)],check=True)
    r=subprocess.run(['bash',str(SH),'--help'],text=True,capture_output=True)
    assert r.returncode==0
    assert '--sha' in r.stdout and '--archive' in r.stdout


@pytest.mark.parametrize('cwd_case',['root','source','other','space'])
def test_b12r_cwd_independent_real_execution_contract(tmp_path,cwd_case):
    root,sha=checkout(tmp_path)
    source=tmp_path/'source (special names)';source.mkdir()
    a,side=pack(source)
    cwd={'root':root,'source':source,'other':tmp_path,'space':(tmp_path/'another folder (x)')}[cwd_case]
    cwd.mkdir(exist_ok=True)
    res=run_cli(root,sha,cwd,'--archive',str(a),'--mode','review')
    assert res.returncode==0,res.stdout+res.stderr
    assert 'B12R_REVIEW_WORKSPACE_READY candidates=1' in res.stdout
    assert 'B_LABEL_APPROVAL_PENDING approved=0' in res.stdout
    names,status,log=outcome(root)
    assert status['status']=='RUN_SUCCESS' and status['exit_code']==0
    assert status['source_diagnostic_archive_sha256']==hashlib.sha256(a.read_bytes()).hexdigest()
    assert 'review/review.html' in names
    assert 'review/plots/B13-0123456789abcdefabcd_xy.svg' in names
    assert 'review/approval_ledger.jsonl' not in names
    assert 'ai/data/manifest.csv' not in names


def test_b12r_relative_archive_and_explicit_absolute_sidecar(tmp_path):
    root,sha=checkout(tmp_path);folder=tmp_path/'input (x)';folder.mkdir()
    a,side=pack(folder)
    res=run_cli(root,sha,folder,'--archive',a.name,'--sha256-file',str(side))
    assert res.returncode==0,res.stderr
    assert outcome(root)[1]['status']=='RUN_SUCCESS'


def test_b12r_autodiscovers_local_latest(tmp_path):
    root,sha=checkout(tmp_path);folder=root/'ai/data/private/b_a13_diagnostics';folder.mkdir(parents=True)
    a,side=pack(tmp_path)
    target=folder/'smartdish_b_a13_20261125T055624Z_6624_diagnostics.tar.gz'
    shutil.copyfile(a,target)
    Path(str(target)+'.sha256').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'  '+target.name+'\n')
    res=run_cli(root,sha,tmp_path,'--mode','review')
    assert res.returncode==0,res.stderr
    assert outcome(root)[1]['status']=='RUN_SUCCESS'


def test_b12r_old_sha256sum_command_red_in_unrelated_cwd(tmp_path):
    source=tmp_path/'input archive';source.mkdir()
    a,side=pack(source)
    unrelated=tmp_path/'cwd not source';unrelated.mkdir()
    old=subprocess.run(['sha256sum','-c',str(side)],cwd=unrelated,text=True,capture_output=True)
    assert old.returncode==1
    assert 'No such file or directory' in old.stderr
    # Original bytes were genuine within the synthetic contract, not corrupt.
    good=subprocess.run(['sha256sum','-c',side.name],cwd=source,text=True,capture_output=True)
    assert good.returncode==0


def test_b12r_missing_tar_reports_specific_code_and_failure_tar(tmp_path):
    root,sha=checkout(tmp_path)
    res=run_cli(root,sha,tmp_path,'--archive',str(tmp_path/'nonexistent.tar.gz'))
    assert res.returncode==2 and 'B12R_ARCHIVE_NOT_FOUND' in res.stderr
    names,status,log=outcome(root)
    assert status['status']=='RUN_FAILED' and status['exit_code']==2
    assert 'B12R_ARCHIVE_NOT_FOUND' in log and 'review/review.html' not in names


def test_b12r_missing_sha_file_reports_specific_code(tmp_path):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path);side.unlink()
    res=run_cli(root,sha,tmp_path,'--archive',str(a))
    assert res.returncode==2 and 'B12R_SIDECAR_MISSING' in res.stderr
    assert outcome(root)[1]['error_code']=='B12R_SIDECAR_MISSING'


def test_b12r_sidecar_wrong_filename_detected(tmp_path):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path)
    side.write_text(hashlib.sha256(a.read_bytes()).hexdigest()+'  unrelated-file.tar.gz\n')
    res=run_cli(root,sha,tmp_path,'--archive',str(a))
    assert res.returncode==2 and 'B12R_SIDECAR_INVALID' in res.stderr
    assert outcome(root)[1]['error_code']=='B12R_SIDECAR_INVALID'


def test_b12r_archive_tamper_fails_but_logs_are_saved(tmp_path):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path)
    a.write_bytes(a.read_bytes()+b'tampered')
    res=run_cli(root,sha,tmp_path,'--archive',str(a))
    assert res.returncode==2 and 'B12R_ARCHIVE_SHA_MISMATCH' in res.stderr
    assert outcome(root)[1]['error_code']=='B12R_ARCHIVE_SHA_MISMATCH'


@pytest.mark.parametrize('name,contents,code',[('../bad',b'exploit','B12R_UNSAFE_ARCHIVE_PATH'),('symlink',None,'B12R_LINK_OR_SPECIAL_FORBIDDEN')])
def test_b12r_tar_unsafe_items_keep_diagnostic(tmp_path,name,contents,code):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path)
    with tarfile.open(tmp_path/'mutated.tar.gz','w:gz') as tf:
        if contents is not None:
            t=tarfile.TarInfo(name);t.size=len(contents);tf.addfile(t,io.BytesIO(contents))
        else:
            t=tarfile.TarInfo('symlink');t.type=tarfile.SYMTYPE;t.linkname='/etc/passwd';tf.addfile(t)
    b=tmp_path/'mutated.tar.gz';s=Path(str(b)+'.sha256');s.write_text(hashlib.sha256(b.read_bytes()).hexdigest()+'  '+b.name+'\n')
    res=run_cli(root,sha,tmp_path,'--archive',str(b))
    assert res.returncode==2 and code in res.stderr
    assert outcome(root)[1]['status']=='RUN_FAILED'


def test_b12r_missing_svg_blocks_with_diag(tmp_path):
    root,sha=checkout(tmp_path)
    def mutate(files):
        files['review/review.html']=files['review/review.html'].replace(b'plots/B13-0123456789abcdefabcd_z.svg',b'plots/missing_z.svg')
    a,side=pack(tmp_path,mutate=mutate)
    res=run_cli(root,sha,tmp_path,'--archive',str(a))
    assert res.returncode==2 and 'B12R_REVIEW_ASSET_MISSING_OR_UNEXPECTED' in res.stderr
    assert outcome(root)[1]['status']=='RUN_FAILED'


def test_b12r_wrong_git_sha_does_not_consume_user_data(tmp_path):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path)
    oldsha='f'*40
    res=run_cli(root,oldsha,tmp_path,'--archive',str(a))
    assert res.returncode==2 and 'B12R_CODE_SHA_PIN_MISMATCH' in res.stderr
    assert outcome(root)[1]['error_code']=='B12R_CODE_SHA_PIN_MISMATCH'
    assert hashlib.sha256(a.read_bytes()).hexdigest()==side.read_text().split()[0]


def test_b12r_human_label_stays_blank(tmp_path):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path)
    res=run_cli(root,sha,tmp_path,'--archive',str(a))
    assert res.returncode==0
    folders=list((root/'ai/data/private').glob('b12_operator_review_*'))
    assert len(folders)==1
    manifest=folders[0]/'B12_REVIEW_DECISIONS_TEMPLATE.csv'
    with manifest.open(newline='') as f: rows=list(csv.DictReader(f))
    assert len(rows)==1 and all(row['decision']=='' and row['approved_label']=='' for row in rows)
    assert not (folders[0]/'review/approval_ledger.jsonl').exists()


def test_b12r_existing_output_never_overwritten(tmp_path):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path)
    out=root/'ai/data/private/preexisting';out.mkdir(parents=True)
    sentinel=out/'keep.txt';sentinel.write_text('original')
    res=run_cli(root,sha,tmp_path,'--archive',str(a),'--output',str(out))
    assert res.returncode==2 and 'B12R_WORKDIR_INVALID_OR_EXISTS' in res.stderr
    assert sentinel.read_text()=='original'
    assert outcome(root)[1]['status']=='RUN_FAILED'


def test_b12r_reject_external_output_path(tmp_path):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path)
    output=tmp_path/'outside';res=run_cli(root,sha,tmp_path,'--archive',str(a),'--output',str(output))
    assert res.returncode==2 and 'B12R_WORKDIR_INVALID_OR_EXISTS' in res.stderr
    assert not output.exists()


def test_b12r_help_does_not_create_artifact(tmp_path):
    root,sha=checkout(tmp_path)
    r=subprocess.run(['bash',str(root/'scripts'/SH.name),'--help'],cwd=tmp_path,capture_output=True,text=True)
    assert r.returncode==0 and '--sha' in r.stdout
    assert not (root/'ai/data/private').exists()


def test_b12r_user_shell_remains_alive_after_failure(tmp_path):
    root,sha=checkout(tmp_path)
    cmd=f'bash "{root}/scripts/{SH.name}" --sha {sha} --archive /nonexistent >/dev/null 2>&1; echo SHELL_STILL_ALIVE'
    r=subprocess.run(['bash','-c',cmd],cwd=tmp_path,capture_output=True,text=True)
    assert r.returncode==0 and 'SHELL_STILL_ALIVE' in r.stdout
    assert outcome(root)[1]['status']=='RUN_FAILED'


def test_b12r_missing_required_cli_option_archived(tmp_path):
    root,sha=checkout(tmp_path)
    res=subprocess.run(['bash',str(root/'scripts'/SH.name),'--mode','review'],
                       cwd=tmp_path,capture_output=True,text=True)
    assert res.returncode==2 and 'B12R_ARGUMENT_INVALID' in res.stderr
    assert outcome(root)[1]['error_code']=='B12R_ARGUMENT_INVALID'


def test_b12r_approval_mode_forbidden_and_archived(tmp_path):
    root,sha=checkout(tmp_path);a,side=pack(tmp_path)
    res=run_cli(root,sha,tmp_path,'--archive',str(a),'--mode','approve')
    assert res.returncode==2 and 'B12R_AUTO_APPROVAL_FORBIDDEN' in res.stderr
    assert outcome(root)[1]['error_code']=='B12R_AUTO_APPROVAL_FORBIDDEN'


def test_b12r_disallows_source_diagnostic_ledger_even_when_resigned(tmp_path):
    root,sha=checkout(tmp_path)
    a,side=pack(tmp_path,mutate=lambda f:f.update({'review/approval_ledger.jsonl':b'not-authorized'}))
    res=run_cli(root,sha,tmp_path,'--archive',str(a))
    assert res.returncode==2 and 'B12R_APPROVAL_IN_DIAGNOSTIC_FORBIDDEN' in res.stderr
    names,state,log=outcome(root)
    assert state['approved_labels']==0 and not any('approval_ledger' in name for name in names)

