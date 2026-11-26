"""B-12R synthetic archives only; owner A13 archive is never a Git fixture."""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
import sys
import tarfile
from pathlib import Path
from PIL import Image
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ai/scripts'))
from receive_b15_diagnostics import (publish_workspace,verify_bundle,ReceiptError,
                                    EXPECTED_A13_SHA,EXPECTED_A13_GIT_SHA)


def pack(tmp_path, mutate=None, *, wrong_sidecar=False, extra=None):
    png=io.BytesIO()
    Image.new('RGB',(640,480),(65,45,88)).save(png,'PNG')
    p=png.getvalue()
    ph=b'{"sim_ns":650000000,"entity":"dish_01","pose":{"x":0}}\n'
    candidate={
      'candidate_id':'B13-0123456789abcdefabcd','source_scene_id':'ST-01',
      'source_image_path':'trial_0001/tray_rgb.png','source_image_sha256':hashlib.sha256(p).hexdigest(),
      'physics_path':'trial_0001/physics_observations.jsonl','physics_sha256':hashlib.sha256(ph).hexdigest(),
      'physics_size_bytes':str(len(ph)), 'source_archive_sha256':EXPECTED_A13_SHA,
      'source_git_sha':EXPECTED_A13_GIT_SHA, 'suggested_label':'STABLE',
      'label_status':'REVIEW_REQUIRED','temporal_review':'PASS',
      'capture_stamp_ns':'600000000','pose_at_capture_ns':'550000000','stack_id':'synth-only'}
    buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=list(candidate));w.writeheader();w.writerow(candidate)
    status={'exit_code':0,'status':'RUN_SUCCESS','candidate_review_only':True,
            'source_archive_sha256':EXPECTED_A13_SHA,'a13_source_git_sha':EXPECTED_A13_GIT_SHA,
            'git_sha':'eae0e8553762addafb66fcee4ae8dd39b75d971f'}
    files={'execution.log':b'SMARTDISH_B_A13_INTERNAL_HASH_PASS verified=88\nSMARTDISH_B_REAL_CANDIDATE_EXTRACTION_PASS 1\n',
           'diagnostic_status.json':json.dumps(status).encode(),
           'review/review.html':('''<html><img src="../raw/trial_0001/tray_rgb.png"/>'''
                + ''.join(f'<img src="plots/B13-0123456789abcdefabcd_{key}.svg"/>' for key in ('z','tilt_deg','xy'))
                + '</html>').encode(),
           'review/plots/B13-0123456789abcdefabcd_z.svg':b'<svg/>',
           'review/plots/B13-0123456789abcdefabcd_tilt_deg.svg':b'<svg/>',
           'review/plots/B13-0123456789abcdefabcd_xy.svg':b'<svg/>',
           'review/candidate_manifest.csv':buf.getvalue().encode(),
           'review/evidence_audit.json':b'{}',
           'raw/trial_0001/tray_rgb.png':p,
           'raw/trial_0001/physics_observations.jsonl':ph}
    if mutate:mutate(files)
    files['SHA256SUMS']=''.join(hashlib.sha256(v).hexdigest()+'  '+k+'\n' for k,v in sorted(files.items())).encode()
    if extra:files.update(extra)
    a=tmp_path/'diagnostics.tar.gz'
    with tarfile.open(a,'w:gz') as tf:
        for name,contents in files.items():
            t=tarfile.TarInfo(name);t.size=len(contents);tf.addfile(t,io.BytesIO(contents))
    digest=hashlib.sha256(a.read_bytes()).hexdigest()
    side=tmp_path/(a.name+'.sha256')
    side.write_text(('0'*64 if wrong_sidecar else digest)+'  '+a.name+'\n')
    return a,side


def test_good_review_workspace_without_approval(tmp_path):
    a,side=pack(tmp_path)
    receipt=publish_workspace(a,side,tmp_path/'review_workspace')
    out=tmp_path/'review_workspace'
    assert receipt['diagnostic_members_verified']==10
    assert receipt['verified_candidates']==1 and receipt['operator_approvals']==0
    assert receipt['source_a13_full_archive_reverified'] is False
    assert (out/'review/review.html').is_file()
    assert not (out/'review/approval_ledger.jsonl').exists()
    assert not (out/'ai/data/manifest.csv').exists()
    with (out/'B12_REVIEW_DECISIONS_TEMPLATE.csv').open() as fp:
        row=list(csv.DictReader(fp))[0]
    assert row['decision']=='' and row['reviewer_id']=='' and row['approved_label']==''
    assert (out/'raw/trial_0001/tray_rgb.png').stat().st_mode & 0o222==0


def test_invalid_sidecar_is_blocked_before_stage(tmp_path):
    a,side=pack(tmp_path,wrong_sidecar=True)
    with pytest.raises(ReceiptError,match='B12R_ARCHIVE_SHA_MISMATCH'):
        publish_workspace(a,side,tmp_path/'release')
    assert not (tmp_path/'release').exists()


def test_missing_sidecar_is_fail_closed(tmp_path):
    a,side=pack(tmp_path);side.unlink()
    with pytest.raises(ReceiptError,match='B12R_SIDECAR_MISSING'):
        publish_workspace(a,side,tmp_path/'release')


def test_unlisted_or_mutated_member_fails(tmp_path):
    a,side=pack(tmp_path,extra={'unlisted.txt':b'oops'})
    with pytest.raises(ReceiptError,match='B12R_HASH_SET_MISMATCH'):
        publish_workspace(a,side,tmp_path/'release')


def test_unsafe_traversal_is_rejected(tmp_path):
    a,side=pack(tmp_path,extra={'../evil.txt':b'hack'})
    with pytest.raises(ReceiptError,match='B12R_UNSAFE_ARCHIVE_PATH'):
        publish_workspace(a,side,tmp_path/'release')
    assert not (tmp_path/'evil.txt').exists()


def test_symlink_is_rejected(tmp_path):
    a,side=pack(tmp_path)
    with tarfile.open(tmp_path/'symlink.tar.gz','w:gz') as tf:
        t=tarfile.TarInfo('other');t.type=tarfile.SYMTYPE;t.linkname='/etc/passwd';tf.addfile(t)
    b=tmp_path/'symlink.tar.gz';s=tmp_path/'symlink.tar.gz.sha256'
    s.write_text(hashlib.sha256(b.read_bytes()).hexdigest()+'  '+b.name+'\n')
    with pytest.raises(ReceiptError,match='B12R_LINK_OR_SPECIAL_FORBIDDEN'):
        publish_workspace(b,s,tmp_path/'release')


def test_reject_nonaccepted_run(tmp_path):
    def m(f):
        j=json.loads(f['diagnostic_status.json']);j['exit_code']=1; j['status']='RUN_FAILED'
        f['diagnostic_status.json']=json.dumps(j).encode()
    a,side=pack(tmp_path,mutate=m)
    with pytest.raises(ReceiptError,match='B12R_SOURCE_RUN_NOT_ACCEPTED'):
        publish_workspace(a,side,tmp_path/'release')


def test_reject_candidate_label_as_approved(tmp_path):
    def m(f):f['review/candidate_manifest.csv']=f['review/candidate_manifest.csv'].replace(b'REVIEW_REQUIRED',b'APPROVED')
    a,side=pack(tmp_path,mutate=m)
    with pytest.raises(ReceiptError,match='B12R_LABEL_STATUS_INVALID'):
        publish_workspace(a,side,tmp_path/'release')


def test_reject_candidate_image_hash_mismatch(tmp_path):
    def m(f):
        f['review/candidate_manifest.csv']=f['review/candidate_manifest.csv'].replace(hashlib.sha256(f['raw/trial_0001/tray_rgb.png']).hexdigest().encode(),b'0'*64)
    a,side=pack(tmp_path,mutate=m)
    with pytest.raises(ReceiptError,match='B12R_CANDIDATE_HASH_MISMATCH'):
        publish_workspace(a,side,tmp_path/'release')


def test_no_overwrite(tmp_path):
    a,side=pack(tmp_path);output=tmp_path/'review'
    publish_workspace(a,side,output)
    with pytest.raises(ReceiptError,match='B12R_OUTPUT_EXISTS_NO_OVERWRITE'):
        publish_workspace(a,side,output)


def test_approval_ledger_in_source_archive_forbidden(tmp_path):
    def m(f):f['review/approval_ledger.jsonl']=b'{"fake":true}\n'
    a,side=pack(tmp_path,mutate=m)
    with pytest.raises(ReceiptError,match='B12R_APPROVAL_IN_DIAGNOSTIC_FORBIDDEN'):
        publish_workspace(a,side,tmp_path/'release')


def test_corrupt_image_rejected_even_with_matching_sums(tmp_path):
    def m(f):
        f['raw/trial_0001/tray_rgb.png']=b'not PNG'
        old=f['review/candidate_manifest.csv'].decode()
        import re
        old=re.sub('[0-9a-f]{64}(?=,trial_0001/physics_observations)',hashlib.sha256(b'not PNG').hexdigest(),old)
        f['review/candidate_manifest.csv']=old.encode()
    a,side=pack(tmp_path,mutate=m)
    with pytest.raises(ReceiptError,match='B12R_IMAGE_CORRUPT|B12R_CANDIDATE_HASH_MISMATCH'):
        publish_workspace(a,side,tmp_path/'release')


def test_b12_review_html_missing_svg_rejected(tmp_path):
    def m(files):
        files['review/review.html']=files['review/review.html'].replace(b'plots/B13-0123456789abcdefabcd_z.svg',b'plots/missing.svg')
    a,side=pack(tmp_path,mutate=m)
    with pytest.raises(ReceiptError,match='B12R_REVIEW_ASSET_MISSING_OR_UNEXPECTED'):
        publish_workspace(a,side,tmp_path/'release')


def test_b12_external_script_in_html_rejected(tmp_path):
    def m(files):
        files['review/review.html']+=b'<script src="https://example.com/exfil"></script>'
    a,side=pack(tmp_path,mutate=m)
    with pytest.raises(ReceiptError,match='B12R_UNSAFE_HTML_CONTENT'):
        publish_workspace(a,side,tmp_path/'release')
