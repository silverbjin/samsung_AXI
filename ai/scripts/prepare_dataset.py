#!/usr/bin/env python3
"""SmartDish B: validate tray stability data and split by physical stack identity.

Only real, human-reviewed tray stability labels may be used for training.
Fixture contract checks are deliberately separate from model evaluation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, UnidentifiedImageError

LABELS = ('STABLE', 'UNSTABLE')
LABEL_MAP = {'STABLE': 0, 'UNSTABLE': 1}
FIELDS = ('sample_id', 'scene_id', 'stack_id', 'label', 'image_path', 'source',
          'capture_config', 'license_status', 'ground_truth', 'image_sha256')
SPLIT_FIELDS = FIELDS + ('split',)
SPLITS = ('train', 'val', 'test')
IMAGE_SIZE = (224, 224)
ALLOWED_SOURCES = {'GAZEBO_TRAY', 'REAL_TRAY', 'CONTRACT_FIXTURE'}
ALLOWED_LICENSES = {'OWNED', 'AUTHORIZED'}


def load_manifest(path: Path) -> list[dict]:
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(FIELDS):
            raise ValueError('B_SCHEMA_MISMATCH: ' + str(reader.fieldnames))
        return list(reader)


def validate(rows: list[dict], root: Path, allow_fixtures: bool = False) -> dict:
    """Validate all rows; return a compact auditable EDA report or raise."""
    root = root.resolve()
    seen_id, seen_sha = set(), {}
    counts, scenes, stacks = Counter(), Counter(), defaultdict(set)
    verified_evidence = 0
    for i, row in enumerate(rows, start=2):
        prefix = f'row={i}'
        if any(not str(row.get(k, '')).strip() for k in FIELDS):
            raise ValueError(f'B_REQUIRED_FIELD_EMPTY {prefix}')
        if row['label'] not in LABELS:
            raise ValueError(f'B_INVALID_LABEL {prefix} label={row["label"]}')
        if row['source'] not in ALLOWED_SOURCES:
            raise ValueError(f'B_INVALID_SOURCE {prefix}')
        if row['license_status'] not in ALLOWED_LICENSES:
            raise ValueError(f'B_LICENSE_NOT_APPROVED {prefix}')
        if row['ground_truth'] != 'PHYSICS_OBSERVED':
            if not (allow_fixtures and row['ground_truth'] == 'MOCK_ONLY'
                    and row['source'] == 'CONTRACT_FIXTURE'):
                raise ValueError(f'B_GROUND_TRUTH_NOT_OBSERVED {prefix}')
        elif row['source'] == 'CONTRACT_FIXTURE':
            raise ValueError(f'B_FIXTURE_CANNOT_BE_PHYSICS_OBSERVED {prefix}')
        if row['sample_id'] in seen_id:
            raise ValueError(f'B_DUPLICATE_SAMPLE_ID {prefix}')
        seen_id.add(row['sample_id'])
        try:
            config = json.loads(row['capture_config'])
        except json.JSONDecodeError as exc:
            raise ValueError(f'B_INVALID_CAPTURE_CONFIG {prefix}') from exc
        if not isinstance(config, dict) or not config:
            raise ValueError(f'B_INVALID_CAPTURE_CONFIG {prefix}')
        rel = Path(row['image_path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError(f'B_IMAGE_PATH_UNSAFE {prefix}')
        full = (root / rel).resolve()
        if not full.is_relative_to(root) or not full.is_file():
            raise ValueError(f'B_IMAGE_MISSING {prefix} path={rel}')
        if row['ground_truth'] == 'PHYSICS_OBSERVED':
            # B-07: re-audit the actual evidence bytes at every dataset preparation.
            # A stored path or JSON field alone is not a verified physical observation.
            required = ('camera', 'physics_evidence', 'physics_evidence_sha256',
                        'physics_evidence_size_bytes')
            if (any(key not in config for key in required)
                    or not all(isinstance(config[key], str) and config[key].strip()
                               for key in required[:3])
                    or not isinstance(config['physics_evidence_size_bytes'], int)
                    or isinstance(config['physics_evidence_size_bytes'], bool)
                    or config['physics_evidence_size_bytes'] <= 0
                    or re.fullmatch(r'[0-9a-f]{64}', config['physics_evidence_sha256']) is None):
                raise ValueError(f'B_PHYSICS_EVIDENCE_METADATA_INVALID {prefix}')
            evidence = Path(config['physics_evidence']).expanduser()
            if not evidence.is_absolute():
                evidence = root / evidence
            evidence = evidence.resolve()
            if not evidence.is_file():
                raise ValueError(f'B_PHYSICS_EVIDENCE_MISSING {prefix}')
            if evidence == full:
                raise ValueError(f'B_PHYSICS_EVIDENCE_NOT_INDEPENDENT {prefix}')
            digest, size = hashlib.sha256(), 0
            with evidence.open('rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
            if size != config['physics_evidence_size_bytes']:
                raise ValueError(f'B_PHYSICS_EVIDENCE_SIZE_MISMATCH {prefix}')
            if digest.hexdigest() != config['physics_evidence_sha256']:
                raise ValueError(f'B_PHYSICS_EVIDENCE_SHA_MISMATCH {prefix}')
            verified_evidence += 1
        sha = hashlib.sha256(full.read_bytes()).hexdigest()
        if sha != row['image_sha256']:
            raise ValueError(f'B_IMAGE_SHA_MISMATCH {prefix}')
        if sha in seen_sha:
            raise ValueError(f'B_DUPLICATE_IMAGE {prefix} previous={seen_sha[sha]}')
        seen_sha[sha] = row['sample_id']
        try:
            with Image.open(full) as image:
                image.verify()
            with Image.open(full) as image:
                if image.format != 'PNG' or image.mode != 'RGB' or image.size != IMAGE_SIZE:
                    raise ValueError(f'B_IMAGE_FORMAT_MISMATCH {prefix}')
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError(f'B_IMAGE_CORRUPT {prefix}') from exc
        counts[row['label']] += 1
        scenes[row['scene_id']] += 1
        stacks[row['stack_id']].add(row['label'])
    conflicts = [key for key, value in stacks.items() if len(value) != 1]
    if conflicts:
        raise ValueError(f'B_STACK_LABEL_CONFLICT stack_id={conflicts[0]}')
    scene_to_stack = defaultdict(set)
    for row in rows:
        scene_to_stack[row['scene_id']].add(row['stack_id'])
    mixed_scenes = [key for key, value in scene_to_stack.items() if len(value) != 1]
    if mixed_scenes:
        raise ValueError(f'B_SCENE_SPANS_STACKS scene_id={mixed_scenes[0]}')
    return {'samples': len(rows), 'classes': dict(counts), 'scenes': dict(scenes),
            'stack_groups': len(stacks), 'evidence_hash_verified': verified_evidence, 'duplicate_images': 0,
            'corrupt_images': 0, 'class_imbalance': (
                max(counts.values()) / min(counts.values()) if len(counts) == 2
                else None), 'data_scope': 'MOCK_ONLY' if allow_fixtures else 'PHYSICS_OBSERVED'}


def make_splits(rows: list[dict], seed: str = 'smartdish-b-v1') -> list[dict]:
    """Deterministic stratified allocation of whole stack groups, never frames."""
    by_label = {label: defaultdict(list) for label in LABELS}
    for row in rows:
        by_label[row['label']][row['stack_id']].append(row)
    assigned = {}
    for label in LABELS:
        groups = by_label[label]
        if len(groups) < 3:
            raise ValueError(f'B_INSUFFICIENT_INDEPENDENT_GROUPS label={label} groups={len(groups)}')
        order = sorted(groups, key=lambda x: hashlib.sha256(
            (seed + '|' + label + '|' + x).encode()).hexdigest())
        n = len(order)
        n_test = max(1, round(n * .2))
        n_val = max(1, round(n * .2))
        if n - n_test - n_val < 1:
            raise ValueError(f'B_INSUFFICIENT_TRAIN_GROUPS label={label}')
        for j, group in enumerate(order):
            assigned[group] = ('test' if j < n_test else 'val' if j < n_test+n_val else 'train')
    result = [dict(row, split=assigned[row['stack_id']]) for row in rows]
    for left in SPLITS:
        left_groups = {r['stack_id'] for r in result if r['split'] == left}
        for right in SPLITS:
            if left != right and left_groups & {r['stack_id'] for r in result if r['split'] == right}:
                raise AssertionError('B_SPLIT_STACK_LEAK')
    return result


def write_csv(path: Path, rows: list[dict], fields: tuple) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        # Stage the complete CSV and replace the final manifest only on success.
        with tempfile.NamedTemporaryFile(mode='w', newline='', encoding='utf-8',
                                         dir=path.parent, prefix='.b-csv-',
                                         suffix='.tmp', delete=False) as out:
            temp = Path(out.name)
            writer = csv.DictWriter(out, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def make_contract_fixtures(root: Path) -> Path:
    """Create six deterministic local synthetic images, never training data."""
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for cls, label in enumerate(LABELS):
        for group in range(3):
            name = f'b_contract_{label.lower()}_{group}.png'
            path = root / name
            img = Image.new('RGB', IMAGE_SIZE, (40 + cls * 100, 30 + group * 30, 80))
            img.save(path)
            rows.append({'sample_id': name[:-4], 'scene_id': f'fixture-{label}-{group}',
                         'stack_id': f'fixture-{label}-{group}', 'label': label,
                         'image_path': name, 'source': 'CONTRACT_FIXTURE',
                         'capture_config': '{"camera":"synthetic_contract_only"}',
                         'license_status': 'OWNED', 'ground_truth': 'MOCK_ONLY',
                         'image_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    out = root / 'manifest.csv'
    write_csv(out, rows, FIELDS)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, default=Path('ai/data/manifest.csv'))
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--out', type=Path, default=Path('ai/data/split_manifest.csv'))
    p.add_argument('--report', type=Path, default=Path('ai/data/quality_report.json'))
    p.add_argument('--make-fixtures', type=Path, help='emit MOCK_ONLY samples under this directory')
    p.add_argument('--allow-fixtures', action='store_true', help='test contract only; not model training')
    args = p.parse_args()
    if args.make_fixtures:
        path = make_contract_fixtures(args.make_fixtures)
        print('B_MOCK_ONLY_FIXTURES_CREATED manifest=' + str(path))
        return 0
    rows = load_manifest(args.manifest)
    report = validate(rows, args.root, args.allow_fixtures)
    split = make_splits(rows)
    report['splits'] = {k: Counter(row['label'] for row in split if row['split'] == k)
                        for k in SPLITS}
    report['label_map'] = LABEL_MAP
    write_csv(args.out, split, SPLIT_FIELDS)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('B_DATASET_CONTRACT_PASS ' + json.dumps(report, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
