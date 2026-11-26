#!/usr/bin/env python3
"""C independent, read-only Dataset v1 intake (not B audit/release, no training).

No private assets or sample-level metadata are written to the report.
Exit 0 means sealed-file contract ready for *human* research approval, not model GO.
Exit 2 means P0 HOLD. Exactly one final machine-readable report is always written.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath

VERSION = "c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606"
B_DELIVERY_SHA = "f05e663ac0aaf843c544c905ddcc2a0791f741ac"
B_EXEC_SHA = "f9ddc56979626d4a78decb04e7b4ca28c3824b09"
OWNER_EVIDENCE_SHA = "411d092f4ab9e65ad044c9b1ae73b2f84456cef1730fef35dcff04c6b393b949"
RELEASE_SHA = "2e9bddf2359cca7f0ccbd2f4ca2c2dc8a5704cf3b9a712864243167b31abd756"
MANIFEST_SHA = "616996e1c7cdd69b6d656ae682ea9536839e15f18a90f86a2b339548fe907769"
SPLIT_SHA = "8a530b6a34788300bb507ea10aafd10a7ab5616a0c0ffc0f87b7ccf79d0db6d5"
RECEIPT_SHA = "14a3e0382f3f8572c6158766eb86cf788b25c6796c6a979da140087a333bb228"
LEDGER_SHA = "1d0a94aeb7de484654958f1e53e47bd8865b04ffa006316ca607baca50b3d8e3"
POLICY_SHA = "b593af4d741439c4871ee946bb157e4d472d5934902ec65f566731cae8ad6cbb"
SCOPE = "FIXED_WORLD_Y_TORQUE_CONDITIONAL_STATIC_CYLINDER_RGB_T0_ONLY"
BASE_FIELDS = ["sample_id", "scene_id", "stack_id", "label", "image_path", "source",
               "capture_config", "license_status", "ground_truth", "image_sha256"]
EXPECTED_COUNTS = {("train", "STABLE"): 8, ("train", "UNSTABLE"): 3,
                   ("val", "STABLE"): 2, ("val", "UNSTABLE"): 1,
                   ("test", "STABLE"): 3, ("test", "UNSTABLE"): 1}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class IntakeHold(ValueError):
    """A blocker with a stable machine-readable reason, never a silent waiver."""


def require(condition: bool, reason: str):
    if not condition:
        raise IntakeHold(reason)


def sha_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(name: str) -> bool:
    p = PurePosixPath(name)
    return (bool(name) and p.as_posix() == name and not p.is_absolute()
            and "\\" not in name and ":" not in name
            and all(k not in ("", ".", "..") for k in name.split("/")))


def checked_path(root: Path, name: str) -> Path:
    require(safe_name(name), "C_V1_UNSAFE_RELEASE_PATH")
    root = root.resolve()
    candidate = root / name
    cur = root
    for component in PurePosixPath(name).parts:
        cur = cur / component
        require(not cur.is_symlink(), "C_V1_SYMLINK_FORBIDDEN")
    require(candidate.resolve().is_relative_to(root), "C_V1_PATH_ESCAPES_ROOT")
    return candidate


def read_csv_bytes(blob: bytes, columns: list[str]) -> list[dict]:
    reader = csv.DictReader(io.StringIO(blob.decode("utf-8-sig")))
    require(reader.fieldnames == columns, "C_V1_SCHEMA_MISMATCH")
    data = list(reader)
    require(all(None not in row and all(isinstance(row.get(c), str) for c in columns)
                for row in data), "C_V1_ROW_INVALID")
    return data


def verify_rows(base: list[dict], split: list[dict], excluded: list[dict], release: dict) -> dict:
    """Verify exact *published* split; do not re-split, relabel, augment or train."""
    require(len(base) == len(split) == 18, "C_V1_APPROVED_18_REQUIRED")
    require(len(excluded) == 2 and {r["scene_id"] for r in excluded} ==
            {"L18-06", "L18-08"}, "C_V1_EXCLUSIONS_CHANGED")
    require(all({k: x[k] for k in BASE_FIELDS} == y for x, y in zip(split, base)),
            "C_V1_MANIFEST_SPLIT_DIFFER")
    counts = Counter((x["split"], x["label"]) for x in split)
    require(dict(counts) == EXPECTED_COUNTS, "C_V1_FROZEN_SPLIT_COUNTS_CHANGED")
    require(len({x["sample_id"] for x in split}) == 18 and
            len({x["scene_id"] for x in split}) == 18 and
            len({x["stack_id"] for x in split}) == 18 and
            len({x["image_sha256"] for x in split}) == 18,
            "C_V1_LAYOUT_OR_IMAGE_DUPLICATE")
    require(not ({x["scene_id"] for x in split} & {r["scene_id"] for r in excluded}),
            "C_V1_EXCLUDED_SAMPLE_IN_TRAINING")
    fam = release.get("family_assignment")
    require(isinstance(fam, dict) and len(fam) == 5 and
            Counter(fam.values()) == {"train": 2, "val": 1, "test": 2} and
            all(HEX64.fullmatch(str(k)) for k in fam), "C_V1_FAMILY_ASSIGNMENT_CHANGED")
    require(release.get("approved_count") == 18 and release.get("excluded_count") == 2 and
            release.get("label_map") == {"STABLE": 0, "UNSTABLE": 1} and
            release.get("contact_health") == "HOLD" and
            release.get("scope") == SCOPE and release.get("source_sha") == B_EXEC_SHA and
            release.get("version") == VERSION and release.get("state") == "DATASET_V1_RELEASED",
            "C_V1_RELEASE_POLICY_MISMATCH")
    for row in split:
        require(row["source"] == "GAZEBO_TRAY" and
                row["ground_truth"] == "PHYSICS_OBSERVED" and
                row["license_status"] == "AUTHORIZED" and
                HEX64.fullmatch(row["image_sha256"]) is not None,
                "C_V1_UNVERIFIED_OR_MOCK_ROW")
        require(safe_name(row["image_path"]), "C_V1_UNSAFE_IMAGE_PATH")
        try:
            cfg = json.loads(row["capture_config"])
        except (TypeError, ValueError) as exc:
            raise IntakeHold("C_V1_CAPTURE_CONFIG_INVALID") from exc
        require(isinstance(cfg, dict) and cfg.get("camera") == "RGB_T0_ONLY" and
                isinstance(cfg.get("physics_evidence"), str) and
                safe_name(cfg["physics_evidence"]) and
                HEX64.fullmatch(str(cfg.get("physics_evidence_sha256", ""))) is not None and
                type(cfg.get("physics_evidence_size_bytes")) is int and
                cfg["physics_evidence_size_bytes"] > 0,
                "C_V1_PHYSICS_EVIDENCE_METADATA_INVALID")
        reg = release.get("files", {})
        require(reg.get(row["image_path"]) == row["image_sha256"] and
                reg.get(cfg["physics_evidence"]) == cfg["physics_evidence_sha256"],
                "C_V1_REGISTRY_ROW_HASH_MISMATCH")
    return {"approved": 18, "excluded": 2, "family_count": 5,
            "label_counts": {"STABLE": 13, "UNSTABLE": 5},
            "split_counts": {s: {label: EXPECTED_COUNTS[(s, label)] for label in ("STABLE", "UNSTABLE")}
                             for s in ("train", "val", "test")},
            "preapproved_split_unchanged": True, "contact_health": "HOLD"}


def audit_metadata(release_blob: bytes, base_blob: bytes, split_blob: bytes,
                   excluded_blob: bytes) -> tuple[dict, dict]:
    require(sha_bytes(release_blob) == RELEASE_SHA, "C_V1_RELEASE_SHA_MISMATCH")
    require(sha_bytes(base_blob) == MANIFEST_SHA, "C_V1_MANIFEST_SHA_MISMATCH")
    require(sha_bytes(split_blob) == SPLIT_SHA, "C_V1_SPLIT_SHA_MISMATCH")
    release = json.loads(release_blob)
    registry = release.get("files")
    require(isinstance(registry, dict) and len(registry) == 42 and
            all(safe_name(name) and isinstance(h, str) and HEX64.fullmatch(h)
                for name, h in registry.items()), "C_V1_REGISTRY_42_INVALID")
    require(registry.get("manifest.csv") == MANIFEST_SHA and
            registry.get("split_manifest.csv") == SPLIT_SHA and
            registry.get("human_approval_ledger.jsonl") == LEDGER_SHA and
            registry.get("approved_policy.json") == POLICY_SHA,
            "C_V1_RELEASE_PINS_DIFFER")
    base = read_csv_bytes(base_blob, BASE_FIELDS)
    split = read_csv_bytes(split_blob, BASE_FIELDS + ["split"])
    excluded = read_csv_bytes(excluded_blob, ["scene_id", "reason"])
    return release, verify_rows(base, split, excluded, release)


def verify_release_root(root: Path) -> dict:
    require(root.is_dir(), "C_V1_PRIVATE_ROOT_INACCESSIBLE")
    root = root.resolve()
    release_blob = checked_path(root, "dataset_release.json").read_bytes()
    base_blob = checked_path(root, "manifest.csv").read_bytes()
    split_blob = checked_path(root, "split_manifest.csv").read_bytes()
    excluded_blob = checked_path(root, "excluded_samples.csv").read_bytes()
    release, summary = audit_metadata(release_blob, base_blob, split_blob, excluded_blob)
    sidecar = checked_path(root, "dataset_release.json.sha256").read_text(encoding="utf-8").split()
    require(len(sidecar) == 2 and sidecar[0] == RELEASE_SHA and
            sidecar[1] == "dataset_release.json", "C_V1_RELEASE_SIDECAR_MISMATCH")
    count = 0
    for name, expected_sha in sorted(release["files"].items()):
        path = checked_path(root, name)
        require(path.is_file(), "C_V1_PRIVATE_FILE_MISSING")
        require(sha_file(path) == expected_sha, "C_V1_PRIVATE_FILE_HASH_MISMATCH")
        count += 1
    # Verify the source rows' image/evidence all physically exist. No image
    # pixels are opened for training here; this is an independent hash audit.
    require(count == 42, "C_V1_INCOMPLETE_FILE_REGISTRY")
    # Reuse existing C producer-independent dataset contract: PNG RGB224, image
    # SHA, independent physics evidence SHA/size, scene/stack split leakage.
    from ai.evaluation.dataset_contract import read_verified_split
    verified_rows = read_verified_split(root / "split_manifest.csv", root, demo_fixtures=False)
    require(len(verified_rows) == 18, "C_V1_C_DATASET_CONTRACT_MISMATCH")
    return {**summary, "files_independently_hashed": count,
            "dataset_version": VERSION,
            "source_execution_pin": B_EXEC_SHA,
            "delivery_pin": B_DELIVERY_SHA,
            "P0_verdict": "CONTRACT_READY_HUMAN_REVIEW_REQUIRED",
            "training_permitted": False,
            "model_pilot_accepted": False,
            "physical_generalization_certified": False}


def verify_owner_archive(path: Path, sidecar: Path) -> dict:
    require(path.is_file() and sidecar.is_file(), "C_V1_OWNER_ARCHIVE_MISSING")
    actual = sha_file(path)
    require(actual == OWNER_EVIDENCE_SHA, "C_V1_OWNER_ARCHIVE_SHA_MISMATCH")
    tokens = sidecar.read_text(encoding="utf-8").split()
    require(len(tokens) == 2 and tokens[0] == OWNER_EVIDENCE_SHA,
            "C_V1_OWNER_SIDECAR_MISMATCH")
    with tarfile.open(path, "r:gz") as t:
        files = {}
        for m in t.getmembers():
            require(m.isfile() and safe_name(m.name) and m.name not in files and
                    m.size <= 10 * 1024 * 1024, "C_V1_OWNER_TAR_UNSAFE")
            files[m.name] = t.extractfile(m).read()
    sums = files.pop("SHA256SUMS")
    entries = {}
    for line in sums.decode().splitlines():
        parts = line.split("  ", 1)
        require(len(parts) == 2 and HEX64.fullmatch(parts[0]) is not None and
                safe_name(parts[1]) and parts[1] not in entries, "C_V1_OWNER_MANIFEST_INVALID")
        entries[parts[1]] = parts[0]
    require(len(entries) == 15 and entries == {k: sha_bytes(v) for k, v in files.items()},
            "C_V1_OWNER_INTERNAL_15_MISMATCH")
    release, summary = audit_metadata(files["dataset_v1/dataset_release.json"],
                                      files["dataset_v1/manifest.csv"],
                                      files["dataset_v1/split_manifest.csv"],
                                      files["dataset_v1/excluded_samples.csv"])
    # The mini evidence contains only four of the 42 registered release files.
    verified_four = sum(files.get("dataset_v1/" + k) is not None and
                        sha_bytes(files["dataset_v1/" + k]) == v
                        for k, v in release["files"].items()
                        if "dataset_v1/" + k in files)
    require(verified_four == 4, "C_V1_OWNER_INCLUDED_FOUR_MISMATCH")
    inner_bytes = files["b_qa06_diagnostics.tar.gz"]
    with tarfile.open(fileobj=io.BytesIO(inner_bytes), mode="r:gz") as t:
        nested = {m.name: t.extractfile(m).read() for m in t.getmembers()
                  if m.isfile() and safe_name(m.name)}
    nested_sums = nested.pop("SHA256SUMS")
    inner_expected = {}
    for line in nested_sums.decode().splitlines():
        h, n = line.split("  ", 1)
        inner_expected[n] = h
    require(len(inner_expected) == 6 and inner_expected ==
            {k: sha_bytes(v) for k, v in nested.items()},
            "C_V1_OWNER_NESTED_6_MISMATCH")
    diag = json.loads(files["diagnostic_status.json"])
    owner = json.loads(files["owner_release_verification.json"])
    require(diag.get("source_sha") == diag.get("checkout_head") == B_EXEC_SHA and
            diag.get("tracked_clean") is True and diag.get("exit_code") == 0 and
            owner.get("release_file_hashes_verified") == 42 and
            owner.get("dataset_version") == VERSION and
            owner.get("manifest_sha256") == MANIFEST_SHA and
            owner.get("split_manifest_sha256") == SPLIT_SHA,
            "C_V1_OWNER_RECEIPT_MISMATCH")
    return {**summary, "owner_archive_sha256": actual,
            "owner_internal_verified": 15, "owner_nested_verified": 6,
            "included_release_files_hashed": verified_four,
            "owner_reported_release_files": 42,
            "C_independent_private_files_verified": verified_four,
            "P0_verdict": "HOLD_PRIVATE_42_RECHECK",
            "training_permitted": False, "model_pilot_accepted": False}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset-root", type=Path, help="private WSL2 Dataset v1 directory")
    p.add_argument("--owner-archive", type=Path)
    p.add_argument("--owner-sidecar", type=Path)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    result = {"schema": 1, "role": "C_INDEPENDENT_V1_READ_ONLY",
              "training_executed": False, "test_opened_for_model_selection": False,
              "AI_OFF": "PROTECTED", "A19": "NOT_AUTHORIZED",
              "production_contact": "HOLD", "verdict": "HOLD"}
    try:
        if a.owner_archive or a.owner_sidecar:
            require(a.owner_archive is not None and a.owner_sidecar is not None,
                    "C_V1_OWNER_PAIR_REQUIRED")
            result.update(verify_owner_archive(a.owner_archive, a.owner_sidecar))
        if a.dataset_root is not None:
            result.update(verify_release_root(a.dataset_root))
        else:
            result["reason"] = "C_V1_PRIVATE_ROOT_NOT_VERIFIED"
        if a.dataset_root is None and a.owner_archive is None:
            result["reason"] = "C_V1_NO_INPUTS"
        result["verdict"] = result.get("P0_verdict", "HOLD")
    except (IntakeHold, OSError, ValueError, KeyError, tarfile.TarError, json.JSONDecodeError) as exc:
        result.update(verdict="HOLD", reason=str(exc).split(" ")[0])
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("C_V1_P0 " + json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["verdict"] == "CONTRACT_READY_HUMAN_REVIEW_REQUIRED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
