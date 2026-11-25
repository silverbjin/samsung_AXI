#!/usr/bin/env python3
"""B-14R: read-only conservative audit of A13 physical-layout independence.

Seed-only jitter is NOT an independent physical stacking layout.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

A13_GIT_SHA = '6cb5b6bfc69687ded0b565b1a3ed6b0cf34b36df'
A13_FIXED_TEMPLATES = frozenset({'ST-01','ST-02','UN-01','UN-02'})


def preview_candidates(rows):
    """Only approximate collection diversity; suggested labels are NOT approved."""
    groups = defaultdict(set)
    distinct_stack = defaultdict(set)
    by_scene = defaultdict(set)
    for row in rows:
        scene = row['source_scene_id']
        if row['source_git_sha'] != A13_GIT_SHA or scene not in A13_FIXED_TEMPLATES:
            raise ValueError('B14_UNSUPPORTED_SOURCE_LAYOUT')
        label = row['suggested_label']
        if label not in ('STABLE','UNSTABLE','REVIEW_REQUIRED'):
            raise ValueError('B14_UNEXPECTED_SUGGESTED_LABEL')
        if label != 'REVIEW_REQUIRED':
            groups[label].add(scene)
        distinct_stack[scene].add(row['stack_id'])
        by_scene[scene].add(row['seed'])
    report={
      'schema':1,
      'status':'B_DATASET_SPLIT_BLOCKED',
      'reason':'B14_INSUFFICIENT_PHYSICAL_LAYOUT_TEMPLATES',
      'operator_approved_labels':0,
      'source_git_sha':A13_GIT_SHA,
      'independent_templates_by_suggested_label':{k:len(groups[k]) for k in ('STABLE','UNSTABLE')},
      'scene_details':{scene:{'seed_values':sorted(by_scene[scene]),
                               'distinct_legacy_stack_ids':len(distinct_stack[scene]),
                               'physical_independent_layout_templates':1}
                       for scene in sorted(by_scene)},
      'seed_only_repeats_are_new_independent_groups':False,
      'no_data_leakage_verified_for_C':False,
      'note':'Current A13 uses four fixed layouts; seed changes only +/-0.001 m x/y jitter. New physical configurations require A owner review.'}
    if any(len(x)>1 for x in distinct_stack.values()):
        report['warning']='B14_SEED_JITTER_MAY_CROSS_LEGACY_STACK_HASH_GROUPS'
    return report


def approved_row_template_guard(rows):
    """Return first C-split block for A13 only; leave other B source contracts untouched."""
    by_template = defaultdict(lambda: {'stacks':set(),'labels':set()})
    for row in rows:
        try:
            cfg = json.loads(row['capture_config'])
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError('B14_CAPTURE_CONFIG_INVALID') from exc
        scene=cfg.get('source_scene_id')
        if cfg.get('source_git_sha')==A13_GIT_SHA and scene in A13_FIXED_TEMPLATES:
            by_template[scene]['stacks'].add(row['stack_id'])
            by_template[scene]['labels'].add(row['label'])
    for template,group in sorted(by_template.items()):
        if len(group['labels'])>1:
            return 'B14_A13_SOURCE_TEMPLATE_LABEL_CONFLICT '+template
        if len(group['stacks'])>1:
            return 'B14_A13_SEED_JITTER_SPLIT_LEAKAGE '+template
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-manifest',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    a=parser.parse_args()
    with a.candidate_manifest.open(newline='',encoding='utf-8') as fp:
        rows=list(csv.DictReader(fp))
    if not rows:
        raise SystemExit('B14_EMPTY_CANDIDATE_MANIFEST')
    result=preview_candidates(rows)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('B14_SEED_ONLY_GROUPS_NOT_INDEPENDENT')
    print('B_DATASET_SPLIT_BLOCKED '+json.dumps(result['independent_templates_by_suggested_label'],sort_keys=True))


if __name__=='__main__': main()
