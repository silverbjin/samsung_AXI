#!/usr/bin/env python3
"""Read-only preflight of B handoff before real training.

Produces a machine-readable BLOCKED or CONTRACT_READY_HUMAN_REVIEW_REQUIRED
result; it NEVER certifies physical truth, model quality or permission to ship.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ai.evaluation.dataset_contract import read_verified_split, summarize


def check(split_manifest: Path, root: Path, *, b_ref: str) -> dict:
    report = {
        "schema": 1,
        "mode": "PHYSICS_OBSERVED_ONLY",
        "b_branch_sha": b_ref,
        "split_manifest": str(split_manifest),
        "split_sha256": (hashlib.sha256(split_manifest.read_bytes()).hexdigest()
                         if split_manifest.is_file() else None),
        "verdict": "BLOCKED",
        "training_executed": False,
        "physical_truth_certified": False,
    }
    if len(b_ref) != 40 or any(x not in "0123456789abcdef" for x in b_ref.lower()):
        report["reason"] = "C_B_SOURCE_SHA_MISSING_OR_INVALID"
        return report
    try:
        rows = read_verified_split(split_manifest, root, demo_fixtures=False)
    except (ValueError, OSError) as exc:
        report["reason"] = str(exc).split(" ")[0]
        return report
    report["verdict"] = "CONTRACT_READY_HUMAN_REVIEW_REQUIRED"
    report["dataset_summary"] = summarize(rows)
    report["reason"] = "C_LABELS_PHYSICS_AND_LICENSE_REQUIRE_HUMAN_REVIEW"
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split-manifest", type=Path, required=True)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--b-ref", required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    result = check(a.split_manifest, a.root, b_ref=a.b_ref)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("C_REAL_DATA_READINESS " + json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "CONTRACT_READY_HUMAN_REVIEW_REQUIRED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
