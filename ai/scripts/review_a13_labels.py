#!/usr/bin/env python3
"""B-12 explicit human decision ledger. No AI or batch automatic approvals."""
from __future__ import annotations
import argparse
import csv
import fcntl
import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from import_a13_evidence import EvidenceError, sha256

DECISIONS=('APPROVED','DEFERRED','REJECTED')
LABELS=('STABLE','UNSTABLE')


def canonical_hash(record:dict)->str:
    return hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False,
                     separators=(',',':')).encode('utf-8')).hexdigest()


def load_candidates(review:Path):
    path=review/'candidate_manifest.csv'
    with path.open(newline='',encoding='utf-8') as fp:
        rows=list(csv.DictReader(fp))
    if not rows or len({x['candidate_id'] for x in rows})!=len(rows):
        raise EvidenceError('B12_CANDIDATE_MANIFEST_INVALID')
    return {r['candidate_id']:r for r in rows}


def load_ledger(path:Path):
    if not path.is_file():return []
    rows=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        try:r=json.loads(line)
        except (TypeError,ValueError) as exc:
            raise EvidenceError('B12_APPROVAL_LEDGER_CORRUPT') from exc
        sig=r.pop('record_sha256',None)
        if sig!=canonical_hash(r):
            raise EvidenceError('B12_APPROVAL_LEDGER_SHA_MISMATCH')
        r['record_sha256']=sig;rows.append(r)
    if len(set(r['candidate_id'] for r in rows))!=len(rows):
        raise EvidenceError('B12_DUPLICATE_REVIEW_RECORD')
    return rows


def check_raw_candidate(row:dict, raw:Path):
    # Never use path traversal strings from the candidate CSV.
    for key,sha_key in [('source_image_path','source_image_sha256'),
                        ('physics_path','physics_sha256')]:
        rel=Path(row[key])
        if rel.is_absolute() or '..' in rel.parts or not (raw/rel).resolve().is_relative_to(raw.resolve()):
            raise EvidenceError('B12_UNSAFE_CANDIDATE_PATH')
        p=raw/rel
        if not p.is_file() or sha256(p)!=row[sha_key]:
            raise EvidenceError('B12_CANDIDATE_SHA_DRIFT')
    if (raw/row['physics_path']).stat().st_size!=int(row['physics_size_bytes']):
        raise EvidenceError('B12_PHYSICS_SIZE_DRIFT')


def record_review(review:Path,raw:Path,candidate_id:str,reviewer_id:str,decision:str,
                  reason:str,license_status:str,approved_label:str|None=None):
    if not reviewer_id.strip() or not reason.strip():
        raise EvidenceError('B12_EXPLICIT_REVIEWER_AND_REASON_REQUIRED')
    if decision not in DECISIONS:
        raise EvidenceError('B12_INVALID_DECISION')
    if decision=='APPROVED':
        if approved_label not in LABELS or license_status not in ('OWNED','AUTHORIZED'):
            raise EvidenceError('B12_APPROVAL_LABEL_LICENSE_REQUIRED')
    elif approved_label is not None:
        raise EvidenceError('B12_NONAPPROVED_LABEL_FORBIDDEN')
    candidates=load_candidates(review)
    if candidate_id not in candidates:
        raise EvidenceError('B12_CANDIDATE_UNKNOWN')
    candidate=candidates[candidate_id]
    if candidate['temporal_review']!='PASS' or candidate['observation']=='INDETERMINATE':
        if decision=='APPROVED':raise EvidenceError('B12_TEMPORAL_OR_PHYSICS_REVIEW_REQUIRED')
    check_raw_candidate(candidate,raw)
    path=review/'approval_ledger.jsonl'
    # Cooperative Unix advisory lock; two reviewers must not erase one another.
    with (review/'.b-review.lock').open('a+b') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        try:
            if any(x['candidate_id']==candidate_id for x in load_ledger(path)):
                raise EvidenceError('B12_REVIEW_ALREADY_RECORDED_NO_OVERWRITE')
            payload={'approval_schema_version':1,'candidate_id':candidate_id,
                     'source_archive_sha256':candidate['source_archive_sha256'],
                     'source_image_sha256':candidate['source_image_sha256'],
                     'physics_evidence_sha256':candidate['physics_sha256'],
                     'reviewer_id':reviewer_id,'reviewed_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                     'decision':decision,'approved_label':approved_label,'reason':reason,
                     'temporal_review':candidate['temporal_review'],
                     'license_status':license_status}
            payload['record_sha256']=canonical_hash(payload)
            fd,tmp=tempfile.mkstemp(prefix='.approval-',suffix='.jsonl',dir=review)
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as stream:
                    previous=path.read_text(encoding='utf-8') if path.is_file() else ''
                    stream.write(previous+json.dumps(payload,sort_keys=True,ensure_ascii=False)+'\n')
                os.replace(tmp,path)
            finally:
                Path(tmp).unlink(missing_ok=True)
            return payload
        finally:
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review-dir',type=Path,required=True)
    p.add_argument('--raw-dir',type=Path,required=True)
    p.add_argument('--candidate-id',required=True)
    p.add_argument('--reviewer-id',required=True)
    p.add_argument('--decision',choices=DECISIONS,required=True)
    p.add_argument('--approved-label',choices=LABELS)
    p.add_argument('--reason',required=True)
    p.add_argument('--license-status',choices=('OWNED','AUTHORIZED','UNVERIFIED'),required=True)
    a=p.parse_args()
    try:
        result=record_review(a.review_dir,a.raw_dir,a.candidate_id,a.reviewer_id,
                             a.decision,a.reason,a.license_status,a.approved_label)
        print('SMARTDISH_B_HUMAN_REVIEW_RECORDED '+result['record_sha256'])
    except EvidenceError as exc:
        print('B_LABEL_APPROVAL_PENDING '+str(exc));raise SystemExit(2)

if __name__=='__main__':main()
