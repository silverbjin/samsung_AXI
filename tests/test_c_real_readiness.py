"""C06 B-06 evidence-file integrity tests: metadata fixtures are not real physics."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from ai.evaluation.dataset_contract import FIELDS, read_verified_split
from ai.train.check_real_data_readiness import check

B_PIN = "1bfc19eabe07f2a0ea8c5c8ba3509491c9dd217d"


def make_rows(tmp_path):
    rows = []
    for cls, label in enumerate(("STABLE", "UNSTABLE")):
        for i, split in enumerate(("train", "val", "test")):
            path = tmp_path / f"test_only_{label}_{i}.png"
            Image.new("RGB", (224,224), (cls * 100 + 10, i * 40 + 15, 90)).save(path)
            evidence = tmp_path / f"fake_only_{label}_{i}.log"
            evidence.write_text(f"SYNTHETIC TEST NOT REAL PHYSICS: {label} {i}")
            eb = evidence.read_bytes()
            rows.append(dict(sample_id=f"test-{label}-{i}",scene_id=f"scene-{label}-{i}",
                             stack_id=f"stack-{label}-{i}",label=label,
                             image_path=path.name,source="GAZEBO_TRAY",
                             capture_config=json.dumps({
                                 "camera": "/smartdish/tray/image_raw",
                                 "physics_evidence": str(evidence),
                                 "physics_evidence_sha256": hashlib.sha256(eb).hexdigest(),
                                 "physics_evidence_size_bytes": len(eb)}),
                             license_status="OWNED",ground_truth="PHYSICS_OBSERVED",
                             image_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             split=split))
    csv_path = tmp_path / "split_manifest.csv"
    with csv_path.open("w",newline="",encoding="utf-8") as out:
        w=csv.DictWriter(out,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    return csv_path, rows


def test_empty_actual_b_manifest_stays_blocked(tmp_path):
    manifest=tmp_path/'empty.csv'
    with manifest.open('w') as out:
        csv.DictWriter(out, fieldnames=FIELDS).writeheader()
    result=check(manifest,tmp_path,b_ref=B_PIN)
    assert result['verdict']=='BLOCKED'
    assert result['reason']=='C_TRAINING_NOT_RUN_NO_REAL_DATA'
    assert result['training_executed'] is False


def test_valid_metadata_requires_human_review_and_not_physics_proof(tmp_path):
    path, _ = make_rows(tmp_path)
    result = check(path,tmp_path,b_ref=B_PIN)
    assert result['verdict']=='CONTRACT_READY_HUMAN_REVIEW_REQUIRED'
    assert result['physical_truth_certified'] is False
    assert result['dataset_summary']['rows'] == 6


def test_missing_evidence_metadata_rejected(tmp_path):
    path,rows=make_rows(tmp_path)
    cfg=json.loads(rows[0]['capture_config']);del cfg['physics_evidence_sha256']
    rows[0]['capture_config']=json.dumps(cfg)
    rewrite(path, rows)
    with pytest.raises(ValueError,match='C_PHYSICS_EVIDENCE_INTEGRITY_METADATA_MISSING'):
        read_verified_split(path,tmp_path)


def rewrite(path,rows):
    with path.open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=FIELDS);w.writeheader();w.writerows(rows)


def test_missing_evidence_file_rejected(tmp_path):
    path,rows=make_rows(tmp_path)
    Path(json.loads(rows[0]['capture_config'])['physics_evidence']).unlink()
    with pytest.raises(ValueError,match='C_PHYSICS_EVIDENCE_FILE_MISSING'):
        read_verified_split(path,tmp_path)


def test_evidence_corruption_and_size_rejected(tmp_path):
    path,rows=make_rows(tmp_path)
    evidence=Path(json.loads(rows[0]['capture_config'])['physics_evidence'])
    evidence.write_bytes(b'A' * evidence.stat().st_size)
    with pytest.raises(ValueError,match='C_PHYSICS_EVIDENCE_SHA_MISMATCH'):
        read_verified_split(path,tmp_path)
    evidence.write_bytes(b'longer than before')
    with pytest.raises(ValueError,match='C_PHYSICS_EVIDENCE_SIZE_MISMATCH'):
        read_verified_split(path,tmp_path)


def test_no_mock_fixtures_as_real_even_with_metadata(tmp_path):
    path,rows=make_rows(tmp_path)
    rows[0]['ground_truth']='MOCK_ONLY';rows[0]['source']='CONTRACT_FIXTURE'
    rewrite(path,rows)
    assert check(path,tmp_path,b_ref=B_PIN)['verdict']=='BLOCKED'


def test_b_sha_required_to_trace_source(tmp_path):
    path,_=make_rows(tmp_path)
    assert check(path,tmp_path,b_ref='branch-name')['reason']=='C_B_SOURCE_SHA_MISSING_OR_INVALID'
