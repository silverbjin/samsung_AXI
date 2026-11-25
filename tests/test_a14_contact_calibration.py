"""A14-07 independent real-Contact positive calibration: L0 contract tests.

Fixtures validate math/schema. They NEVER count as Gazebo L2 or Owner WSL2.
"""
import hashlib
import json
import sys
import tarfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from a14_contact_calibration import (
    WALL_BUDGET_S, MIN_SIM_NS, PAIRS, TOPICS,
    assess_positive_controls, bridge_config, generate_world,
    archive, pair_matches,
)


def row(key, t=1_000_000_000, reverse=False):
    expected = PAIRS[key]
    first, second = expected if not reverse else tuple(reversed(expected))
    return {
        "topic": TOPICS[key], "sim_time_ns": t,
        "stamp_source": "ROS_CONTACT_HEADER_STAMP",
        "collision1": first + "::body::collision",
        "collision2": second + "::body::collision",
        "collision1_id": 101, "collision2_id": 202,
    }


def test_two_independent_real_positive_targets_have_valid_sdf():
    tree = ET.fromstring(generate_world())
    world = tree.find("world")
    assert world is not None
    assert world.attrib["name"] == "a14_contact_calibration"
    plugin = world.find("./plugin[@name='gz::sim::systems::Contact']")
    assert plugin is not None
    assert plugin.attrib["filename"] == "gz-sim-contact-system"
    assert len(world.findall("./model")) == 4
    for key, topic in TOPICS.items():
        name = "a14_cal_" + key + "_target"
        model = world.find("./model[@name='%s']" % name)
        assert model.findtext("static") == "true"
        sensor = model.find(".//sensor[@type='contact']")
        assert sensor is not None
        assert sensor.find("topic") is None
        assert sensor.findtext("contact/collision") == "collision"
        assert sensor.findtext("contact/topic") == topic
        falling = world.find("./model[@name='a14_cal_%s_projectile']" % key)
        assert falling is not None
        assert falling.findtext("static") == "false"
    assert "smartdish_tray" not in world.attrib["name"]
    assert "approval_ledger" not in generate_world()


def test_jazzy_bridge_matches_real_contact_topics_and_clock():
    bridges = bridge_config()
    assert len(bridges) == 3
    for key, topic in TOPICS.items():
        item = next(x for x in bridges if x["ros_topic_name"] == topic)
        assert item["gz_type_name"] == "gz.msgs.Contacts"
        assert item["ros_type_name"] == "ros_gz_interfaces/msg/Contacts"
        assert item["direction"] == "GZ_TO_ROS"
        assert pair_matches(key, row(key)["collision1"], row(key)["collision2"])
        assert pair_matches(key, row(key, reverse=True)["collision1"],
                            row(key, reverse=True)["collision2"])
    clock = next(x for x in bridges if x["ros_topic_name"] == "/clock")
    assert clock["ros_type_name"] == "rosgraph_msgs/msg/Clock"


def test_both_valid_positive_controls_pass_without_proving_no_contact():
    result = assess_positive_controls(
        [row("tray"), row("floor", 1_200_000_000)],
        clock_ns=MIN_SIM_NS + 100, source_sha="a" * 40)
    assert result["verdict"] == "POSITIVE_CONTROL_PASS"
    assert all(x["positive_collision_observed"]
               for x in result["sensors"].values())
    assert result["production_contact_silence_resolved"] is False
    assert result["production_sensor_health"] == "NOT_MEASURED_BY_THIS_CONTROL"
    assert result["no_contact_inferred_from_silence"] is False
    assert result["rule_candidate"] == "UNKNOWN"
    assert result["ground_truth"] == "NOT_OPERATOR_APPROVED"
    assert result["human_approved"] is False


@pytest.mark.parametrize("items", [
    [], [row("tray")], [row("floor")],
    [dict(row("tray"), sim_time_ns=0), row("floor")],
    [dict(row("tray"), stamp_source="ROS_CALLBACK_CLOCK_APPROX_NOT_GT"), row("floor")],
    [dict(row("tray"), collision2="wrong::body::collision"), row("floor")],
    [dict(row("tray"), topic="/smartdish/a14/production/contact/tray"), row("floor")],
])
def test_missing_wrong_or_unstamped_real_contact_is_hold(items):
    x = assess_positive_controls(items, MIN_SIM_NS + 100, "b" * 40)
    assert x["verdict"] == "POSITIVE_CONTROL_HOLD"
    assert x["human_approved"] is False


def test_missing_sim_clock_never_qualifies_positive_events():
    x = assess_positive_controls([row("tray"), row("floor")],
                                 MIN_SIM_NS - 1, "c" * 40)
    assert x["verdict"] == "POSITIVE_CONTROL_HOLD"
    assert x["sim_clock_coverage"] == "INCOMPLETE"


def test_archive_sha_manifest_and_no_approval_ledger(tmp_path):
    p = tmp_path / "trial"
    p.mkdir()
    (p / "calibration_world.sdf").write_text(generate_world())
    (p / "calibration_result.json").write_text(json.dumps(
        assess_positive_controls([row("tray"), row("floor")], MIN_SIM_NS, "d" * 40)))
    bundle = archive(p)
    sidecar = p / (bundle.name + ".sha256")
    assert sidecar.is_file()
    outer, expected_name = sidecar.read_text().strip().split("  ")
    assert expected_name == bundle.name
    assert outer == hashlib.sha256(bundle.read_bytes()).hexdigest()
    with tarfile.open(bundle, "r:gz") as t:
        paths = set(t.getnames())
        assert "calibration_world.sdf" in paths
        assert "calibration_result.json" in paths
        assert "approval_ledger.jsonl" not in paths
        assert "SHA256SUMS" in paths
        for line in t.extractfile("SHA256SUMS").read().decode().splitlines():
            h, name = line.split("  ", 1)
            assert hashlib.sha256(t.extractfile(name).read()).hexdigest() == h


def test_bounded_work_no_legacy_tray_batch_replay():
    assert 30 <= WALL_BUDGET_S <= 100
    src = (ROOT / "scripts/a14_contact_calibration.py").read_text()
    assert "deadline = started + budget_s" in src
    assert "time.monotonic() < observing_until" in src
    assert "A14_CAL_POSITIVE_SENSOR_OR_CLOCK_NOT_OBSERVED" in src
    assert "stop_owned(proc)" in src
    assert "pkill" not in src and "killall" not in src
    assert "smartdish_a_tray_live.py single" not in src
    assert "ST-02" not in src and "UN-01" not in src
    assert "approval_ledger.jsonl" not in src
