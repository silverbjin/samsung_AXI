"""A-12 reproducibility, actual dynamic SDF and no simulated label inference."""
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_tray_world import (
    SCENARIOS, build_world, placements, validate_world, write_trial,
    TRAY_TOP, TRAY_WIDTH, MU, MASS_KG,
)


@pytest.mark.parametrize("scenario",SCENARIOS)
def test_four_scenarios_are_dynamic_and_reproducible(scenario):
    a, spec=build_world(scenario,117)
    b, other=build_world(scenario,117)
    assert ET.tostring(a)==ET.tostring(b)
    assert spec==other
    assert validate_world(a,spec)
    assert all(d["mass_kg"]==MASS_KG and d["friction_mu"]==MU for d in spec)
    assert "restaurant" not in ET.tostring(a).decode()


def test_stable_and_unstable_candidates_have_distinct_initial_conditions():
    st=placements("ST-01",7)
    un=placements("UN-01",7)
    assert all(abs(d["x"]) < TRAY_WIDTH/2 for d in st)
    assert any(abs(d["x"])>TRAY_WIDTH/2 for d in un)
    assert all(d["z"]>TRAY_TOP for d in un)


def test_reject_wrong_seed_and_scenario():
    with pytest.raises(ValueError, match="UNKNOWN_SCENARIO"):
        build_world("STABLE",10)
    with pytest.raises(ValueError,match="INVALID_SEED"):
        build_world("ST-01",-10)


def test_no_overwrite_and_capture_metadata_has_no_ground_truth(tmp_path):
    dest=tmp_path/"trial.sdf"
    row=write_trial("UN-02",13,dest,"trial_0001")
    assert row["ground_truth"]=="NOT_YET_OBSERVED"
    assert row["label"]=="REVIEW_REQUIRED"
    assert row["input_capture_phase"]=="PRE_OBSERVATION"
    assert dest.with_suffix(".scenario.json").exists()
    with pytest.raises(ValueError, match="NO_OVERWRITE"):
        write_trial("UN-02",13,dest,"trial_0001")


def test_world_has_sensor_ogre2_physics_and_pose_broadcaster():
    xml=ET.tostring(build_world("ST-02",3)[0]).decode()
    for name in ("gz-sim-sensors-system","gz-sim-physics-system",
                 "gz-sim-scene-broadcaster-system","ogre2"):
        assert name in xml
    root=ET.fromstring(xml)
    models=root.findall("./world/model")
    disks=[m for m in models if m.get("name","").startswith("dish_")]
    assert len(disks)==3
    for d in disks:
        assert d.findtext("static")=="false"
        assert d.find("./link/collision/geometry/cylinder") is not None
        assert float(d.findtext("./link/inertial/mass"))>0
        assert d.find("./joint") is None
