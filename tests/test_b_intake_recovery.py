"""B-08 residual boundary: one writer + fail-closed orphan detection.

All images and physics evidence here are test-only; not real training data.
"""
from __future__ import annotations

import fcntl
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parents[1] / 'ai/scripts'))
import collect_tableware
from prepare_dataset import FIELDS, load_manifest, write_csv


def setup_intake(tmp_path: Path):
    root = tmp_path / 'repo'
    root.mkdir()
    manifest = root / 'ai/data/manifest.csv'
    write_csv(manifest, [], FIELDS)
    evidence = root / 'ai/data/private/settle.txt'
    evidence.parent.mkdir(parents=True)
    evidence.write_text('TEST_ONLY: human review NOT performed', encoding='utf-8')
    image = root / 'ai/data/private/raw.png'
    Image.new('RGB', (320, 240), (22, 44, 66)).save(image)
    return root, manifest, evidence, image


def ingest(root, manifest, evidence, image, scene='scene-A', stack='stack-A'):
    return collect_tableware.collect(image, root, manifest, 'STABLE', scene, stack,
                                     'GAZEBO_TRAY', 'OWNED', str(evidence), '/smartdish/tray/image_raw')


def test_staged_orphan_is_blocked_until_operator_quarantines(tmp_path):
    root, manifest, evidence, image = setup_intake(tmp_path)
    directory = root / 'ai/data/images'
    directory.mkdir(parents=True)
    orphan = directory / '.incoming-crashed.png'
    orphan.write_bytes(b'crash happened during a previous intake')
    before = manifest.read_bytes()
    with pytest.raises(ValueError, match='B_ORPHAN_FILES_DETECTED'):
        ingest(root, manifest, evidence, image)
    assert manifest.read_bytes() == before and orphan.is_file()
    quarantine = root / 'ai/data/private' / orphan.name
    orphan.rename(quarantine)  # operator action: preserve evidence, not auto-delete
    row = ingest(root, manifest, evidence, image)
    assert len(load_manifest(manifest)) == 1 and row['ground_truth'] == 'PHYSICS_OBSERVED'


def test_published_orphan_and_csv_temp_are_blocked_without_overwrite(tmp_path):
    root, manifest, evidence, image = setup_intake(tmp_path)
    directory = root / 'ai/data/images'
    directory.mkdir(parents=True)
    orphan = directory / ('B-' + '0'*16 + '.png')
    orphan.write_bytes(b'unindexed-image-preserve')
    csv_tmp = manifest.parent / '.b-csv-abandoned.tmp'
    csv_tmp.write_text('unfinished CSV')
    with pytest.raises(ValueError, match='B_ORPHAN_FILES_DETECTED'):
        ingest(root, manifest, evidence, image)
    assert orphan.read_bytes() == b'unindexed-image-preserve'
    assert csv_tmp.read_text() == 'unfinished CSV'
    assert load_manifest(manifest) == []
    orphan.rename(root / 'ai/data/private' / orphan.name)
    csv_tmp.rename(root / 'ai/data/private' / csv_tmp.name)
    assert len(load_manifest(manifest)) == 0
    ingest(root, manifest, evidence, image)
    assert len(load_manifest(manifest)) == 1


def test_second_writer_fails_fast_on_manifest_lock(tmp_path):
    root, manifest, evidence, image = setup_intake(tmp_path)
    lock_path = manifest.parent / '.b-intake.lock'
    with lock_path.open('a+b') as locked:
        fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(ValueError, match='B_COLLECTOR_BUSY'):
                ingest(root, manifest, evidence, image)
        finally:
            fcntl.flock(locked, fcntl.LOCK_UN)
    assert load_manifest(manifest) == []
    assert not (root / 'ai/data/images').exists()
    ingest(root, manifest, evidence, image)
    different = image.parent / 'other.png'
    Image.new('RGB', (320, 240), (88, 22, 10)).save(different)
    ingest(root, manifest, evidence, different, 'scene-B', 'stack-B')
    assert len(load_manifest(manifest)) == 2


def test_keyboard_interrupt_after_image_move_is_detectable_on_next_run(tmp_path, monkeypatch):
    root, manifest, evidence, image = setup_intake(tmp_path)
    original = manifest.read_bytes()
    original_writer = collect_tableware.write_csv
    def abrupt_exit(*args, **kwargs):
        raise KeyboardInterrupt('SIMULATED_KILL_AFTER_PNG_MOVED')
    monkeypatch.setattr(collect_tableware, 'write_csv', abrupt_exit)
    with pytest.raises(KeyboardInterrupt, match='SIMULATED_KILL_AFTER_PNG_MOVED'):
        ingest(root, manifest, evidence, image)
    monkeypatch.setattr(collect_tableware, 'write_csv', original_writer)
    assert manifest.read_bytes() == original
    pngs = list((root / 'ai/data/images').glob('B-*.png'))
    assert len(pngs) == 1
    with pytest.raises(ValueError, match='B_IMAGE_DEST_EXISTS_NOT_IN_MANIFEST'):
        ingest(root, manifest, evidence, image)
    pngs[0].rename(root / 'ai/data/private' / pngs[0].name)
    ingest(root, manifest, evidence, image)
    assert len(load_manifest(manifest)) == 1


def test_separate_cli_process_cannot_write_under_existing_lock(tmp_path):
    """Real second process, not merely a mock lock API."""
    import subprocess
    root, manifest, evidence, image = setup_intake(tmp_path)
    lock_path = manifest.parent / '.b-intake.lock'
    command = [sys.executable, str(Path(__file__).parents[1] / 'ai/scripts/collect_tableware.py'),
               '--image', str(image), '--root', str(root), '--manifest', str(manifest),
               '--label', 'STABLE', '--scene-id', 's1', '--stack-id', 'k1',
               '--source', 'GAZEBO_TRAY', '--license-status', 'OWNED',
               '--physics-evidence', str(evidence), '--camera', '/smartdish/tray/image_raw']
    with lock_path.open('a+b') as locked:
        fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        finally:
            fcntl.flock(locked, fcntl.LOCK_UN)
    assert result.returncode != 0
    assert 'B_COLLECTOR_BUSY' in result.stderr
    assert load_manifest(manifest) == []
    assert not (root / 'ai/data/images').exists()
    result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert 'B_CAPTURE_INGESTED' in result.stdout
    assert len(load_manifest(manifest)) == 1
