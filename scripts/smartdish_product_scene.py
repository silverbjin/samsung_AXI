#!/usr/bin/env python3
"""A-PROD-01 opt-in S7 startup scene. Manifest describes expectations only."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from s7_scene import build_world, NAME, SCENARIOS
from s6_scene import TABLE3_WORLD_XY, FIXTURE_WORLD_XY

def generate(source, out, scenario, run_id):
    source, out = Path(source), Path(out)
    manifest_path = out.with_suffix(".manifest.json")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,124}", run_id):
        raise ValueError("A_PRODUCT_INVALID_RUN_ID")
    if scenario not in SCENARIOS:
        raise ValueError("A_PRODUCT_INVALID_SCENARIO")
    if out.resolve() == source.resolve() or out.exists() or manifest_path.exists():
        raise ValueError("A_PRODUCT_NO_OVERWRITE")
    original = source.read_bytes()
    rendered = build_world(original.decode("utf-8"), scenario).encode("utf-8")
    model = ET.fromstring(rendered).find(f".//world/model[@name='{NAME}']")
    # S6 has one logical plate per plate_i visual; rims are not extra dishes.
    plates = [] if model is None else sorted(
        v.attrib["name"] for v in model.findall("./link/visual")
        if re.fullmatch(r"plate_[0-9]+", v.attrib.get("name", "")))
    if scenario == "stacked" and len(plates) != 3:
        raise ValueError("A_PRODUCT_EXPECTED_THREE_PLATES")
    manifest = {
        "schema_version": 2, "profile": "OWNER_PRODUCT_RECOVERY",
        "run_id": run_id, "world_id": "restaurant", "table_id": "T03",
        "stack_id": run_id + ":T03", "scenario": scenario,
        "fixture_count": int(model is not None), "dish_count": len(plates),
        "expected_model_names": [NAME] if model is not None else [],
        "logical_plate_names": plates, "entity_ids": [],
        "table_world_xy": list(TABLE3_WORLD_XY),
        "fixture_world_xy": list(FIXTURE_WORLD_XY),
        "initial_location": "TABLE" if plates else "EMPTY",
        "source_sha256": hashlib.sha256(original).hexdigest(),
        "world_sha256": hashlib.sha256(rendered).hexdigest(),
        "runtime_verified": False, "receipt_kind": "GENERATED_EXPECTATION_ONLY",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("xb") as f:
        f.write(rendered)
    try:
        with manifest_path.open("x", encoding="utf-8") as f:
            json.dump(manifest, f, sort_keys=True, indent=2)
            f.write("\n")
    except Exception:
        out.unlink()
        raise
    return manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--scenario", choices=SCENARIOS, required=True)
    parser.add_argument("--run-id", required=True)
    a = parser.parse_args()
    print(json.dumps(generate(a.source, a.out, a.scenario, a.run_id), sort_keys=True))

if __name__ == "__main__":
    main()
