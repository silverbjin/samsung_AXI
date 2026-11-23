"""C read-only validation of B's real tray data contract.

No test image may influence learning, and synthetic B fixtures are never labels.
C does not modify or copy B's data/manifest into its branch.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ("sample_id", "scene_id", "stack_id", "label", "image_path",
          "source", "capture_config", "license_status", "ground_truth",
          "image_sha256", "split")
LABEL_MAP = {"STABLE": 0, "UNSTABLE": 1}
SPLITS = ("train", "val", "test")


def read_verified_split(manifest: Path, root: Path, *, demo_fixtures: bool = False) -> list[dict[str, str]]:
    """Validate a strict real-data or explicitly isolated B MOCK_ONLY fixture split.

    A caller must opt into demo_fixtures. No mixed real/mock provenance is allowed.
    """
    import json
    from PIL import Image

    if not manifest.is_file():
        raise ValueError("C_SPLIT_MANIFEST_MISSING")
    with manifest.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("C_SPLIT_SCHEMA_MISMATCH")
        rows = list(reader)
    if not rows:
        raise ValueError("C_TRAINING_NOT_RUN_NO_REAL_DATA")
    root = root.resolve()
    seen_samples, seen_sha = set(), set()
    stack_splits, scene_stacks = defaultdict(set), defaultdict(set)
    groups = defaultdict(set)
    for row in rows:
        if any(not row.get(k, "").strip() for k in FIELDS):
            raise ValueError("C_REQUIRED_FIELD_MISSING")
        if row["label"] not in LABEL_MAP:
            raise ValueError("C_INVALID_LABEL")
        if row["split"] not in SPLITS:
            raise ValueError("C_INVALID_SPLIT")
        if demo_fixtures:
            if row["ground_truth"] != "MOCK_ONLY" or row["source"] != "CONTRACT_FIXTURE":
                raise ValueError("C_DEMO_REQUIRES_B_MOCK_ONLY_FIXTURES")
        elif row["ground_truth"] != "PHYSICS_OBSERVED" or row["source"] not in ("GAZEBO_TRAY", "REAL_TRAY"):
            raise ValueError("C_FIXTURE_OR_UNVERIFIED_GROUND_TRUTH")
        if row["license_status"] not in ("OWNED", "AUTHORIZED"):
            raise ValueError("C_DATA_LICENSE_NOT_APPROVED")
        if row["sample_id"] in seen_samples or row["image_sha256"] in seen_sha:
            raise ValueError("C_DUPLICATE_IMAGE_OR_SAMPLE")
        seen_samples.add(row["sample_id"])
        seen_sha.add(row["image_sha256"])
        try:
            cfg = json.loads(row["capture_config"])
        except (ValueError, TypeError) as exc:
            raise ValueError("C_INVALID_CAPTURE_CONFIG") from exc
        if not isinstance(cfg, dict):
            raise ValueError("C_INVALID_CAPTURE_CONFIG")
        if demo_fixtures:
            if cfg.get("camera") != "synthetic_contract_only":
                raise ValueError("C_DEMO_CAMERA_NOT_B_FIXTURE")
        elif not cfg.get("physics_evidence"):
            raise ValueError("C_PHYSICS_EVIDENCE_REFERENCE_MISSING")
        rel = Path(row["image_path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("C_UNSAFE_IMAGE_PATH")
        image_path = (root / rel).resolve()
        if not image_path.is_relative_to(root) or not image_path.is_file():
            raise ValueError("C_IMAGE_MISSING")
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != row["image_sha256"]:
            raise ValueError("C_IMAGE_SHA_MISMATCH")
        try:
            with Image.open(image_path) as img:
                img.verify()
            with Image.open(image_path) as img:
                if img.format != "PNG" or img.mode != "RGB" or img.size != (224, 224):
                    raise ValueError("C_IMAGE_FORMAT_MISMATCH")
        except (OSError, SyntaxError) as exc:
            raise ValueError("C_CORRUPT_IMAGE") from exc
        stack_splits[row["stack_id"]].add(row["split"])
        scene_stacks[row["scene_id"]].add(row["stack_id"])
        groups[(row["split"], row["label"])].add(row["stack_id"])
    if any(len(x) != 1 for x in stack_splits.values()):
        raise ValueError("C_STACK_SPLIT_LEAK")
    if any(len(x) != 1 for x in scene_stacks.values()):
        raise ValueError("C_SCENE_SPANS_STACKS")
    if any(not groups[(split, label)] for split in SPLITS for label in LABEL_MAP):
        raise ValueError("C_INDEPENDENT_SPLIT_CLASS_MISSING")
    return rows


def summarize(rows: list[dict[str, str]]) -> dict:
    return {
        "rows": len(rows), "label_map": LABEL_MAP,
        "split_counts": {split: dict(Counter(r["label"] for r in rows if r["split"] == split))
                         for split in SPLITS},
        "independent_stack_count": len({r["stack_id"] for r in rows}),
    }
