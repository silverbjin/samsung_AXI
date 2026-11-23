#!/usr/bin/env python3
"""Offline intake of an operator-labelled tray image; no ROS or fake physics labels.

The operator must separately observe settled tray geometry before assigning a
PHYSICS_OBSERVED label. This program validates metadata, not physical truth.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps
from prepare_dataset import FIELDS, IMAGE_SIZE, LABELS, load_manifest, write_csv


def collect(image: Path, root: Path, manifest: Path, label: str, scene_id: str,
            stack_id: str, source: str, license_status: str, evidence: str,
            camera: str) -> dict:
    if label not in LABELS:
        raise ValueError('B_LABEL_MUST_BE_STABLE_OR_UNSTABLE')
    if source not in {'GAZEBO_TRAY', 'REAL_TRAY'}:
        raise ValueError('B_NO_S7_OR_DACON_PROXY_LABELS')
    if license_status not in {'OWNED', 'AUTHORIZED'}:
        raise ValueError('B_LICENSE_NOT_APPROVED')
    if not all(x.strip() for x in (scene_id, stack_id, evidence, camera)):
        raise ValueError('B_OBSERVATION_METADATA_REQUIRED')
    if not image.is_file():
        raise ValueError('B_IMAGE_MISSING')
    evidence_file = Path(evidence).expanduser().resolve()
    if not evidence_file.is_file():
        raise ValueError('B_PHYSICS_EVIDENCE_FILE_MISSING')
    if evidence_file == image.resolve():
        raise ValueError('B_PHYSICS_EVIDENCE_NOT_INDEPENDENT')
    evidence_hash = hashlib.sha256()
    evidence_bytes = 0
    with evidence_file.open('rb') as source_file:
        while chunk := source_file.read(1024 * 1024):
            evidence_hash.update(chunk)
            evidence_bytes += len(chunk)
    if evidence_bytes == 0:
        raise ValueError('B_PHYSICS_EVIDENCE_EMPTY')
    with Image.open(image) as img:
        rgb = ImageOps.exif_transpose(img).convert('RGB')
        # Fixed network contract; RGB, 224x224, bilinear resize without ROI guarantee.
        rgb = ImageOps.fit(rgb, IMAGE_SIZE, method=Image.Resampling.BILINEAR)
        root = root.resolve()
        dest_dir = root / 'ai/data/images'
        dest_dir.mkdir(parents=True, exist_ok=True)
        tmp = dest_dir / '.incoming.png'
        rgb.save(tmp, format='PNG')
    raw = tmp.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    records = load_manifest(manifest)
    if any(r['image_sha256'] == sha for r in records):
        tmp.unlink()
        raise ValueError('B_DUPLICATE_IMAGE')
    sid = 'B-' + sha[:16]
    dest = dest_dir / f'{sid}.png'
    tmp.replace(dest)
    row = {'sample_id': sid, 'scene_id': scene_id, 'stack_id': stack_id,
           'label': label, 'image_path': dest.relative_to(root).as_posix(),
           'source': source, 'capture_config': json.dumps(
               {'camera': camera, 'physics_evidence': str(evidence_file),
                'physics_evidence_sha256': evidence_hash.hexdigest(),
                'physics_evidence_size_bytes': evidence_bytes,
                'preprocess': 'RGB_224_FIT_BILINEAR'},
               sort_keys=True, separators=(',', ':')),
           'license_status': license_status, 'ground_truth': 'PHYSICS_OBSERVED',
           'image_sha256': sha}
    write_csv(manifest, records+[row], FIELDS)
    return row


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', type=Path, required=True)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--manifest', type=Path, default=Path('ai/data/manifest.csv'))
    p.add_argument('--label', choices=LABELS, required=True)
    p.add_argument('--scene-id', required=True)
    p.add_argument('--stack-id', required=True)
    p.add_argument('--source', choices=('GAZEBO_TRAY', 'REAL_TRAY'), required=True)
    p.add_argument('--license-status', choices=('OWNED', 'AUTHORIZED'), required=True)
    p.add_argument('--physics-evidence', required=True,
                   help='existing nonempty operator/Gazebo settling evidence file; manual review still required')
    p.add_argument('--camera', required=True)
    a = p.parse_args()
    row = collect(a.image, a.root, a.manifest, a.label, a.scene_id, a.stack_id,
                  a.source, a.license_status, a.physics_evidence, a.camera)
    print('B_CAPTURE_INGESTED id=' + row['sample_id'] + ' sha256=' + row['image_sha256'])


if __name__ == '__main__':
    main()
