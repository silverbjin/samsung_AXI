#!/usr/bin/env python3
"""B-14 portable, offline release re-verification for C (never trains a model)."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from import_a13_evidence import EvidenceError,sha256
from review_a13_labels import load_ledger


def verify_release(release:Path):
    release=release.resolve()
    checksum=release/'SHA256SUMS'; manifest=release/'release_manifest.json'
    if not checksum.is_file() or not manifest.is_file():
        raise EvidenceError('B14_RELEASE_MANIFEST_MISSING')
    expected={}
    for line in checksum.read_text().splitlines():
        if '  ' not in line:
            raise EvidenceError('B14_CHECKSUM_FORMAT')
        digest,name=line.split('  ',1)
        p=Path(name)
        if (not re.fullmatch('[0-9a-f]{64}',digest) or p.is_absolute()
                or '..' in p.parts or name in expected):
            raise EvidenceError('B14_CHECKSUM_ENTRY_INVALID')
        expected[name]=digest
    found={p.relative_to(release).as_posix() for p in release.rglob('*') if p.is_file()}
    if set(expected)!=(found-{'SHA256SUMS'}):
        raise EvidenceError('B14_RELEASE_FILE_SET_MISMATCH')
    for name,hash_value in expected.items():
        p=(release/name).resolve()
        if not p.is_relative_to(release) or sha256(p)!=hash_value:
            raise EvidenceError('B14_RELEASE_SHA_MISMATCH '+name)
    info=json.loads(manifest.read_text())
    ledger_file=release/'source_evidence/approval_ledger.jsonl'
    if info['approved_count']>0:
        if not ledger_file.is_file():raise EvidenceError('B14_APPROVAL_LEDGER_MISSING')
        approvals={a['record_sha256']:a for a in load_ledger(ledger_file) if a['decision']=='APPROVED'}
        import csv
        rows=list(csv.DictReader((release/'ai/data/manifest.csv').open(newline='')))
        if len(rows)!=info['approved_count']:
            raise EvidenceError('B14_RELEASE_SAMPLE_COUNT_MISMATCH')
        for row in rows:
            cfg=json.loads(row['capture_config'])
            app=approvals.get(cfg.get('approval_record_sha256'))
            if (app is None or app['candidate_id']!=cfg.get('a13_candidate_id')
                    or app['source_image_sha256']!=cfg.get('source_image_sha256')
                    or app['source_archive_sha256']!=cfg.get('source_archive_sha256')
                    or app['approved_label']!=row['label']):
                raise EvidenceError('B14_APPROVAL_BINDING_INVALID')
            ev=Path(cfg['physics_evidence'])
            if ev.is_absolute() or '..' in ev.parts:
                raise EvidenceError('B14_PHYSICS_PATH_NOT_PORTABLE')
        from prepare_dataset import validate
        validate(rows,release,allow_fixtures=False)
    return {'verdict':'B14_PORTABLE_RELEASE_SHA_PASS',
            'sha_files':len(expected),'approved_count':info['approved_count'],
            'training_executed':False,'dataset_verdict':info['verdict']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--release-root',type=Path,required=True)
    a=p.parse_args()
    try:
        print(json.dumps(verify_release(a.release_root),sort_keys=True))
    except (EvidenceError,ValueError,FileNotFoundError) as exc:
        print('B14_RELEASE_RECHECK_BLOCKED '+str(exc));raise SystemExit(2)

if __name__=='__main__': main()
