"""A-PROD-01: generated scene and immutable stack identity."""
import hashlib
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from smartdish_product_scene import generate

BASE = ROOT / "src/restaurant_world/worlds/restaurant.sdf"

def test_stacked_and_empty(tmp_path):
    original = BASE.read_bytes()
    for scenario, count in [("stacked", 3), ("empty", 0)]:
        out = tmp_path / scenario / "world.sdf"
        m = generate(BASE, out, scenario, "ci-01")
        assert m["schema_version"] == 2
        assert m["profile"] == "OWNER_PRODUCT_RECOVERY"
        assert m["world_id"] == "restaurant"
        assert m["stack_id"] == "ci-01:T03"
        assert m["dish_count"] == count
        assert m["fixture_count"] == int(count > 0)
        assert m["world_sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
        assert m["source_sha256"] == hashlib.sha256(original).hexdigest()
        assert m["runtime_verified"] is False
        model = ET.parse(out).find(".//world/model[@name='s6_stacked_dishes']")
        assert (model is not None) == bool(count)
        assert json.loads(out.with_suffix(".manifest.json").read_text()) == m
    assert BASE.read_bytes() == original

def test_no_overwrite_or_duplicate(tmp_path):
    out = tmp_path / "world.sdf"
    generate(BASE, out, "stacked", "ci-02")
    with pytest.raises(ValueError):
        generate(BASE, out, "empty", "ci-02")
    with pytest.raises(ValueError):
        generate(out, tmp_path / "duplicate.sdf", "stacked", "ci-03")

@pytest.mark.parametrize("run_id", ["", "../bad", "x"*125, "a b"])
def test_bad_run_id(tmp_path, run_id):
    with pytest.raises(ValueError):
        generate(BASE, tmp_path / "bad.sdf", "stacked", run_id)
