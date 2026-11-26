#!/usr/bin/env python3
"""B-13/14 bridge human-approved A13 candidates into existing B collector and C readiness."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter,defaultdict
from pathlib import Path
from import_a13_evidence import EvidenceError,sha256
from review_a13_labels import load_candidates,load_ledger,check_raw_candidate


def stage_approved(raw:Path,review:Path,release:Path, *, b_ref: str|None=None):
    """Only approved, hash-bound, operator-reviewed candidates may enter a real manifest."""
    candidates=load_candidates(review)
    approvals=load_ledger(review/'approval_ledger.jsonl')
    if not any(a['decision']=='APPROVED' for a in approvals):
        # Do not even create a training manifest before a human approval exists.
        release.mkdir(parents=True,exist_ok=True)
        (release/'reports').mkdir(exist_ok=True)
        result={'approved_samples':0,'new_registered':0,'candidate_count':len(candidates),
                'decision_count':len(approvals),'review_pending':len(candidates)-len(approvals),
                'approved_by_operator':0,'deferred':sum(a['decision']=='DEFERRED' for a in approvals),
                'rejected':sum(a['decision']=='REJECTED' for a in approvals),
                'verdict':'B_LABEL_APPROVAL_PENDING','training_executed':False}
        (release/'reports/quality_report.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from collect_tableware import collect
    from prepare_dataset import FIELDS,load_manifest,write_csv,validate,make_splits,SPLIT_FIELDS
    if not release.exists():
        release.mkdir(parents=True)
    manifest=release/'ai/data/manifest.csv'
    if not manifest.exists():write_csv(manifest,[],FIELDS)
    current=load_manifest(manifest)
    registered={json.loads(row['capture_config']).get('a13_candidate_id')
                for row in current}
    count=0
    for approval in approvals:
        if approval['decision']!='APPROVED':continue
        cid=approval['candidate_id']
        if cid not in candidates:
            raise EvidenceError('B13_APPROVAL_CANDIDATE_NOT_FOUND')
        c=candidates[cid]
        if (approval['source_archive_sha256']!=c['source_archive_sha256']
                or approval['source_image_sha256']!=c['source_image_sha256']
                or approval['physics_evidence_sha256']!=c['physics_sha256']):
            raise EvidenceError('B13_APPROVAL_HASH_BINDING_BROKEN')
        if (approval['approved_label'] not in ('STABLE','UNSTABLE')
                or approval['license_status'] not in ('OWNED','AUTHORIZED')
                or c['temporal_review']!='PASS' or c['observation']=='INDETERMINATE'):
            raise EvidenceError('B13_APPROVAL_INCOMPLETE_OR_UNSAFE')
        check_raw_candidate(c,raw)
        if cid in registered:continue
        image_out=release/'source_evidence/original_images'/f'{cid}.png'
        physics_out=release/'source_evidence/physics'/f'{cid}.jsonl'
        image_out.parent.mkdir(parents=True,exist_ok=True)
        physics_out.parent.mkdir(parents=True,exist_ok=True)
        if image_out.exists() or physics_out.exists():
            raise EvidenceError('B13_RELEASE_SOURCE_OVERWRITE_FORBIDDEN')
        shutil.copyfile(raw/c['source_image_path'],image_out)
        shutil.copyfile(raw/c['physics_path'],physics_out)
        try:
            record=collect(image_out,release,manifest,approval['approved_label'],
                           c['scene_id'],c['stack_id'],'GAZEBO_TRAY',approval['license_status'],
                           str(physics_out),'/smartdish/tray/image_raw',
                           a13_provenance={'a13_candidate_id':cid,
                            'source_archive_sha256':c['source_archive_sha256'],
                            'source_image_sha256':c['source_image_sha256'],
                            'source_git_sha':c['source_git_sha'],
                            'source_trial_id':c['trial_id'],'source_scene_id':c['source_scene_id'],
                            'seed':int(c['seed']),
                            'capture_stamp_ns':int(c['capture_stamp_ns']),
                            'approval_record_sha256':approval['record_sha256']})
        except Exception:
            image_out.unlink(missing_ok=True);physics_out.unlink(missing_ok=True)
            raise
        registered.add(cid);count+=1
    rows=load_manifest(manifest)
    quality={'approved_samples':len(rows),'new_registered':count,
             'candidate_count':len(candidates),'decision_count':len(approvals),
             'review_pending':len(candidates)-len(approvals),
             'approved_by_operator':sum(a['decision']=='APPROVED' for a in approvals),
             'rejected':sum(a['decision']=='REJECTED' for a in approvals),
             'deferred':sum(a['decision']=='DEFERRED' for a in approvals),
             'label_counts':dict(Counter(r['label'] for r in rows)),
             'groups_per_label':{lab:len({r['stack_id'] for r in rows if r['label']==lab})
                                 for lab in ('STABLE','UNSTABLE')},
             'verdict':'B_LABEL_APPROVAL_PENDING'}
    # No partial training split when fewer than three independent groups per label.
    if rows:
        quality['pilot_status']='B_APPROVED_PILOT_DATA_READY'
        report=validate(rows,release,allow_fixtures=False)
        quality['evidence_hash_verified']=report['evidence_hash_verified']
        from audit_a13_independent_groups import approved_row_template_guard
        try:
            template_block=approved_row_template_guard(rows)
            if template_block:
                raise ValueError(template_block)
            split=make_splits(rows)
        except ValueError as exc:
            quality['verdict']='B_DATASET_SPLIT_BLOCKED'
            quality['reason']=str(exc)
        else:
            write_csv(release/'ai/data/split_manifest.csv',split,SPLIT_FIELDS)
            # C is read-only; its strict split/physics contract remains the gate.
            try:
                repo_root=Path(__file__).resolve().parents[2]
                if str(repo_root) not in sys.path: sys.path.insert(0,str(repo_root))
                from ai.train.check_real_data_readiness import check
                c=check(release/'ai/data/split_manifest.csv',release,b_ref=b_ref or 'missing-sha')
                if c['verdict']=='CONTRACT_READY_HUMAN_REVIEW_REQUIRED':
                    quality['verdict']='B_DATASET_READY_FOR_C_REVIEW'
                    quality['c_readiness']=c
                else:
                    quality['verdict']='B_C_CROSS_CONTRACT_BLOCKED'
                    quality['reason']=c.get('reason','C_UNKNOWN')
            except ImportError:
                quality['verdict']='B_C_CROSS_CONTRACT_NOT_RUN'
                quality['reason']='C_SOURCE_UNAVAILABLE' 
    (release/'reports').mkdir(exist_ok=True)
    (release/'source_evidence').mkdir(exist_ok=True)
    # Signed-by-hash decision log and candidate index travel with a portable release.
    # These are immutable copies; re-running must not silently rewrite a release.
    for filename in ('candidate_manifest.csv','approval_ledger.jsonl','evidence_audit.json'):
        source_file=review/filename
        if source_file.is_file():
            target=release/'source_evidence'/filename
            if target.exists():
                if sha256(target)!=sha256(source_file):
                    raise EvidenceError('B13_RELEASE_LEDGER_DRIFT')
            else:
                shutil.copyfile(source_file,target)
    (release/'reports/quality_report.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2)+'\n')
    # Reference all files with content hashes for a private, portable release root.
    file_list=[]
    for p in sorted(release.rglob('*')):
        if p.is_file() and p.name not in ('SHA256SUMS','release_manifest.json'):
            file_list.append({'path':p.relative_to(release).as_posix(),'sha256':sha256(p),
                              'size_bytes':p.stat().st_size})
    release_info={'schema':1,'verdict':quality['verdict'],'candidate_count':len(candidates),
                  'approved_count':len(rows),'files':file_list,'training_executed':False}
    (release/'release_manifest.json').write_text(json.dumps(release_info,ensure_ascii=False,indent=2)+'\n')
    (release/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['path']+'\n' for x in file_list) + sha256(release/'release_manifest.json')+'  release_manifest.json\n')
    return quality


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-dir',type=Path,required=True)
    p.add_argument('--review-dir',type=Path,required=True)
    p.add_argument('--release-root',type=Path,required=True)
    p.add_argument('--b-ref',required=True,help='exact 40-character B code SHA')
    a=p.parse_args()
    try:
        result=stage_approved(a.raw_dir,a.review_dir,a.release_root,b_ref=a.b_ref)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
        if result['approved_samples']>0:
            print('SMARTDISH_B_APPROVED_DATA_IMPORT_PASS')
        print(result['verdict'])
    except (EvidenceError,ValueError) as exc:
        print('B13_IMPORT_BLOCKED '+str(exc));raise SystemExit(2)

if __name__=='__main__':main()
