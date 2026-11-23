"""Mock-only separation: B fixture data may exercise C, never certify physics."""
import csv
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from ai.evaluation.dataset_contract import FIELDS, read_verified_split
from ai.train.evaluate import classification_metrics
from ai.evaluation.stability_model import load_checkpoint
from ai.train.demo_fixture_pipeline import orchestrate


def b_fixture_rows(tmp_path):
    rows = []
    for class_no, label in enumerate(('STABLE', 'UNSTABLE')):
        for group, split in enumerate(('train', 'val', 'test')):
            filename = f'b_contract_{label.lower()}_{group}.png'
            path = tmp_path / filename
            Image.new('RGB',(224,224),(40+class_no*100,30+group*30,80)).save(path)
            rows.append({'sample_id': filename[:-4], 'scene_id': f'fixture-{label}-{group}',
                         'stack_id': f'fixture-{label}-{group}', 'label': label,
                         'image_path': filename, 'source': 'CONTRACT_FIXTURE',
                         'capture_config': '{"camera":"synthetic_contract_only"}',
                         'license_status': 'OWNED', 'ground_truth': 'MOCK_ONLY',
                         'image_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'split': split})
    manifest=tmp_path / 'split_manifest.csv'
    with manifest.open('w',newline='') as output:
        writer=csv.DictWriter(output,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    return manifest,rows


def test_demo_fixture_requires_explicit_opt_in(tmp_path):
    manifest,rows=b_fixture_rows(tmp_path)
    with pytest.raises(ValueError, match='C_FIXTURE_OR_UNVERIFIED_GROUND_TRUTH'):
        read_verified_split(manifest,tmp_path)
    assert len(read_verified_split(manifest,tmp_path,demo_fixtures=True)) == 6


def test_demo_rejects_falsely_claimed_physics(tmp_path):
    manifest,rows=b_fixture_rows(tmp_path)
    rows[0]['source']='GAZEBO_TRAY';rows[0]['ground_truth']='PHYSICS_OBSERVED'
    with manifest.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError,match='C_DEMO_REQUIRES_B_MOCK_ONLY_FIXTURES'):
        read_verified_split(manifest,tmp_path,demo_fixtures=True)


def test_demo_rejects_relabelled_camera(tmp_path):
    manifest,rows=b_fixture_rows(tmp_path)
    rows[0]['capture_config']='{"camera":"unknown"}'
    with manifest.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError,match='C_DEMO_CAMERA_NOT_B_FIXTURE'):
        read_verified_split(manifest,tmp_path,demo_fixtures=True)


def test_demo_requires_class_and_split_independence(tmp_path):
    manifest,rows=b_fixture_rows(tmp_path)
    rows[0]['stack_id']=rows[1]['stack_id']
    with manifest.open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    with pytest.raises(ValueError,match='C_STACK_SPLIT_LEAK'):
        read_verified_split(manifest,tmp_path,demo_fixtures=True)


def test_demo_metrics_are_math_only():
    result=classification_metrics(['STABLE','UNSTABLE'],['UNSTABLE','UNSTABLE'])
    assert result['confusion_matrix']==[[0,1],[0,1]]
    assert result['accuracy']==0.5


def test_demo_output_must_be_outside_repo(tmp_path):
    args=type('Args',(), {'output':Path(__file__).parents[1], 'b_script':tmp_path/'fake.py'})()
    with pytest.raises(ValueError,match='C_DEMO_ARTIFACTS_MUST_BE_OUTSIDE_REPO'):
        orchestrate(args)


def test_loader_mock_is_opt_in(tmp_path):
    # No real PyTorch dependency needed for contract in CI: API must remain fail-closed.
    import inspect
    sig = inspect.signature(load_checkpoint)
    assert sig.parameters['allow_mock'].default is False
