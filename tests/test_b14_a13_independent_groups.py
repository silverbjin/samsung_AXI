"""B14: source SHA+fixed A13 geometry, not seed count, defines pilot independence."""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ai/scripts'))
import pytest
from audit_a13_independent_groups import (A13_GIT_SHA,preview_candidates,
                                           approved_row_template_guard)


def row(scene,seed,stack,label):
    return dict(source_scene_id=scene,source_git_sha=A13_GIT_SHA,
                seed=str(seed),stack_id=stack,suggested_label=label)


def real_pilot_count_is_2_per_provisional_class():
    rows=[row('ST-01',102,'stack-a','STABLE'),row('ST-02',103,'stack-b','STABLE'),
          row('UN-01',104,'stack-c','UNSTABLE'),row('UN-02',105,'stack-d','UNSTABLE')]
    return preview_candidates(rows)


def test_b14_real_pilot_insufficient_groups():
    out=real_pilot_count_is_2_per_provisional_class()
    assert out['independent_templates_by_suggested_label']=={'STABLE':2,'UNSTABLE':2}
    assert out['status']=='B_DATASET_SPLIT_BLOCKED'
    assert out['operator_approved_labels']==0


def test_b14_seed_only_duplicate_is_not_new_template():
    rows=[row('ST-01',102,'stack-a','STABLE'),row('ST-01',103,'stack-b','STABLE')]
    result=preview_candidates(rows)
    assert result['independent_templates_by_suggested_label']['STABLE']==1
    assert result['scene_details']['ST-01']['distinct_legacy_stack_ids']==2
    assert result['warning']=='B14_SEED_JITTER_MAY_CROSS_LEGACY_STACK_HASH_GROUPS'


def test_b14_approved_rows_legacy_stack_hash_leak_blocked():
    rows=[]
    for i in range(2):
        cfg={'source_git_sha':A13_GIT_SHA,'source_scene_id':'UN-01','seed':101+i}
        rows.append({'capture_config':json.dumps(cfg),'stack_id':f'old-{i}', 'label':'UNSTABLE'})
    assert approved_row_template_guard(rows)=='B14_A13_SEED_JITTER_SPLIT_LEAKAGE UN-01'


def test_b14_conflicting_same_template_labels_blocked():
    rows=[{'capture_config':json.dumps({'source_git_sha':A13_GIT_SHA,'source_scene_id':'ST-01'}),
           'stack_id':'same','label':lab} for lab in ('STABLE','UNSTABLE')]
    assert approved_row_template_guard(rows)=='B14_A13_SOURCE_TEMPLATE_LABEL_CONFLICT ST-01'


def test_b14_non_a13_source_not_modified():
    row={'capture_config':json.dumps({'camera':'non_a13'}), 'stack_id':'other','label':'STABLE'}
    assert approved_row_template_guard([row]) is None


def test_b14_invalid_capture_config_rejected():
    with pytest.raises(ValueError,match='B14_CAPTURE_CONFIG_INVALID'):
        approved_row_template_guard([{'capture_config':'{bad','stack_id':'x','label':'STABLE'}])


def test_b14_unsupported_real_source_not_silently_counted():
    with pytest.raises(ValueError,match='B14_UNSUPPORTED_SOURCE_LAYOUT'):
        preview_candidates([row('ST-99',102,'stack','STABLE')])
