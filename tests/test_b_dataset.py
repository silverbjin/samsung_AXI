"""B data contract checks: generated images are NOT physics-labelled examples."""
import csv
import hashlib
import json
import sys
from pathlib import Path
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parents[1] / 'ai/scripts'))
from prepare_dataset import FIELDS, IMAGE_SIZE, LABEL_MAP, load_manifest, make_splits, validate, write_csv, make_contract_fixtures
from collect_tableware import collect


def rows_at(tmp_path):
    rows = []
    for label_idx, label in enumerate(('STABLE', 'UNSTABLE')):
        for group in range(5):
            for frame in range(2):
                n = label_idx * 100 + group * 10 + frame
                path = tmp_path / f'{n}.png'
                Image.new('RGB', IMAGE_SIZE, (n, 90, 120)).save(path)
                rows.append(dict(sample_id=f'id-{n}', scene_id=f'scene-{label}-{group}',
                                 stack_id=f'{label}-{group}', label=label,
                                 image_path=path.name, source='CONTRACT_FIXTURE',
                                 capture_config='{"view":"unit-test"}',
                                 license_status='OWNED', ground_truth='MOCK_ONLY',
                                 image_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return rows


def test_label_map_and_real_manifest_strict(tmp_path):
    assert LABEL_MAP == {'STABLE': 0, 'UNSTABLE': 1}
    rows = rows_at(tmp_path)
    with pytest.raises(ValueError, match='B_GROUND_TRUTH_NOT_OBSERVED'):
        validate(rows, tmp_path)
    quality = validate(rows, tmp_path, allow_fixtures=True)
    assert quality['samples'] == 20
    assert quality['data_scope'] == 'MOCK_ONLY'


def test_group_split_deterministic_no_leak(tmp_path):
    rows = rows_at(tmp_path)
    a, b = make_splits(rows), make_splits(list(reversed(rows)))
    assert {(r['sample_id'],r['split']) for r in a} == {(r['sample_id'],r['split']) for r in b}
    for label in ('STABLE', 'UNSTABLE'):
        for split in ('train', 'val', 'test'):
            assert any(r['split'] == split and r['label'] == label for r in a)
    for group in {r['stack_id'] for r in a}:
        assert len({r['split'] for r in a if r['stack_id'] == group}) == 1


def test_legacy_s7_label_rejected(tmp_path):
    rows = rows_at(tmp_path)
    rows[0]['label'] = 'STACKED'
    with pytest.raises(ValueError, match='B_INVALID_LABEL'):
        validate(rows, tmp_path, allow_fixtures=True)


def test_image_duplicate_and_tamper_rejected(tmp_path):
    rows = rows_at(tmp_path)
    rows[1]['image_sha256'] = rows[0]['image_sha256']
    with pytest.raises(ValueError, match='B_IMAGE_SHA_MISMATCH'):
        validate(rows, tmp_path, allow_fixtures=True)
    rows = rows_at(tmp_path)
    rows[1]['image_path'] = rows[0]['image_path']
    rows[1]['image_sha256'] = rows[0]['image_sha256']
    with pytest.raises(ValueError, match='B_DUPLICATE_IMAGE'):
        validate(rows, tmp_path, allow_fixtures=True)


def test_group_conflict_rejected(tmp_path):
    rows = rows_at(tmp_path)
    rows[0]['stack_id'] = rows[-1]['stack_id']
    with pytest.raises(ValueError, match='B_STACK_LABEL_CONFLICT'):
        validate(rows, tmp_path, allow_fixtures=True)


def test_split_requires_independent_groups(tmp_path):
    rows = [r for r in rows_at(tmp_path) if r['stack_id'] in {'STABLE-0', 'UNSTABLE-0'}]
    with pytest.raises(ValueError, match='B_INSUFFICIENT_INDEPENDENT_GROUPS'):
        make_splits(rows)


def test_manifest_schema_and_missing(tmp_path):
    rows = rows_at(tmp_path)
    path = tmp_path / 'manifest.csv'
    write_csv(path, rows, FIELDS)
    assert load_manifest(path) == rows
    (tmp_path / rows[0]['image_path']).unlink()
    with pytest.raises(ValueError, match='B_IMAGE_MISSING'):
        validate(load_manifest(path), tmp_path, allow_fixtures=True)


def test_collector_requires_physics_and_de_dupes(tmp_path):
    img = tmp_path / 'input.png'
    Image.new('RGB',(320,240),(22,44,66)).save(img)
    root = tmp_path / 'repo'
    root.mkdir()
    manifest = root / 'manifest.csv'
    write_csv(manifest, [], FIELDS)
    with pytest.raises(ValueError, match='B_OBSERVATION_METADATA_REQUIRED'):
        collect(img, root, manifest, 'STABLE','scene-1','stack-1','GAZEBO_TRAY','OWNED','','tray_rgb')
    evidence = tmp_path / 'settle.log'
    evidence.write_text('human-reviewed observation: tray remained level after simulation')
    row = collect(img,root,manifest,'STABLE','scene-1','stack-1','GAZEBO_TRAY','OWNED',str(evidence),'tray_rgb')
    assert row['ground_truth'] == 'PHYSICS_OBSERVED'
    cfg = json.loads(row['capture_config'])
    assert cfg['physics_evidence_sha256'] == hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert validate(load_manifest(manifest),root)['samples'] == 1
    with pytest.raises(ValueError, match='B_DUPLICATE_IMAGE'):
        collect(img,root,manifest,'STABLE','scene-1','stack-1','GAZEBO_TRAY','OWNED',str(evidence),'tray_rgb')


def test_mock_fixture_end_to_end(tmp_path):
    manifest = make_contract_fixtures(tmp_path)
    rows = load_manifest(manifest)
    with pytest.raises(ValueError, match='B_GROUND_TRUTH_NOT_OBSERVED'):
        validate(rows, tmp_path)
    assert validate(rows, tmp_path, allow_fixtures=True)['samples'] == 6
    split = make_splits(rows)
    assert {row['split'] for row in split} == {'train', 'val', 'test'}


def test_scene_group_leak_guard(tmp_path):
    rows = rows_at(tmp_path)
    rows[0]['scene_id'] = rows[2]['scene_id']
    with pytest.raises(ValueError, match='B_SCENE_SPANS_STACKS'):
        validate(rows,tmp_path,allow_fixtures=True)


def test_physics_reference_must_be_real_nonempty_independent(tmp_path):
    image = tmp_path / 'capture.png'
    Image.new('RGB', (32, 32), (20, 30, 40)).save(image)
    manifest = tmp_path / 'm.csv'
    write_csv(manifest, [], FIELDS)
    with pytest.raises(ValueError, match='B_PHYSICS_EVIDENCE_FILE_MISSING'):
        collect(image,tmp_path,manifest,'STABLE','s','g','GAZEBO_TRAY','OWNED','missing.log','tray')
    with pytest.raises(ValueError, match='B_PHYSICS_EVIDENCE_NOT_INDEPENDENT'):
        collect(image,tmp_path,manifest,'STABLE','s','g','GAZEBO_TRAY','OWNED',str(image),'tray')
    blank = tmp_path / 'blank.log'
    blank.touch()
    with pytest.raises(ValueError, match='B_PHYSICS_EVIDENCE_EMPTY'):
        collect(image,tmp_path,manifest,'STABLE','s','g','GAZEBO_TRAY','OWNED',str(blank),'tray')
    assert load_manifest(manifest) == []


def _physical_manifest(tmp_path):
    image = tmp_path / 'camera.png'
    Image.new('RGB', (320, 240), (22, 44, 77)).save(image)
    evidence = tmp_path / 'settle_pose.log'
    evidence.write_text('POSE_BEFORE_AND_AFTER=RECORDED', encoding='utf-8')
    manifest = tmp_path / 'manifest.csv'
    write_csv(manifest, [], FIELDS)
    collect(image, tmp_path, manifest, 'STABLE', 'scene_1', 'stack_1',
            'GAZEBO_TRAY', 'OWNED', str(evidence), '/smartdish/tray/image_raw')
    return manifest, evidence


def test_physics_evidence_reaudit_pass(tmp_path):
    manifest, evidence = _physical_manifest(tmp_path)
    report = validate(load_manifest(manifest), tmp_path)
    assert report['evidence_hash_verified'] == 1


def test_physics_evidence_changed_same_size_rejected(tmp_path):
    manifest, evidence = _physical_manifest(tmp_path)
    evidence.write_bytes(b'X' * evidence.stat().st_size)
    with pytest.raises(ValueError, match='B_PHYSICS_EVIDENCE_SHA_MISMATCH'):
        validate(load_manifest(manifest), tmp_path)


def test_physics_evidence_missing_rejected(tmp_path):
    manifest, evidence = _physical_manifest(tmp_path)
    evidence.unlink()
    with pytest.raises(ValueError, match='B_PHYSICS_EVIDENCE_MISSING'):
        validate(load_manifest(manifest), tmp_path)


def test_physics_evidence_metadata_corrupted_rejected(tmp_path):
    manifest, _ = _physical_manifest(tmp_path)
    rows = load_manifest(manifest)
    config = json.loads(rows[0]['capture_config'])
    del config['physics_evidence_sha256']
    rows[0]['capture_config'] = json.dumps(config)
    with pytest.raises(ValueError, match='B_PHYSICS_EVIDENCE_METADATA_INVALID'):
        validate(rows, tmp_path)
