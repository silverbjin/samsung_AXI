"""Public fixture-only negative guards; no B private data or models committed."""
import copy
import json
from pathlib import Path

import pytest
from ai.train.dataset_v1_gate import (IntakeHold, EXPECTED_COUNTS, SCOPE, B_EXEC_SHA,
    VERSION, checked_path, safe_name, verify_rows, verify_release_root)


def fixture_rows():
    rows = []
    i = 0
    registry = {"manifest.csv": "0" * 64, "split_manifest.csv": "0" * 64}
    for (split, label), count in EXPECTED_COUNTS.items():
        for _ in range(count):
            i += 1
            name = f"synthetic-{i:02d}"
            im = f"images/{name}.png"
            ev = f"evidence/{name}.tar.gz"
            image_sha, evidence_sha = f"{i:064x}", f"{(i + 100):064x}"
            registry[im], registry[ev] = image_sha, evidence_sha
            rows.append({"sample_id": name, "scene_id": name, "stack_id": "stack-" + name,
                         "label": label, "image_path": im, "source": "GAZEBO_TRAY",
                         "capture_config": json.dumps({"camera": "RGB_T0_ONLY",
                                                     "physics_evidence": ev,
                                                     "physics_evidence_sha256": evidence_sha,
                                                     "physics_evidence_size_bytes": 123}),
                         "license_status": "AUTHORIZED", "ground_truth": "PHYSICS_OBSERVED",
                         "image_sha256": image_sha, "split": split})
    release = {"files": registry, "family_assignment": {f"{j:064x}": split
                                 for j, split in enumerate(["train", "train", "val", "test", "test"], 1)},
               "approved_count": 18, "excluded_count": 2,
               "label_map": {"STABLE": 0, "UNSTABLE": 1},
               "contact_health": "HOLD", "scope": SCOPE, "source_sha": B_EXEC_SHA,
               "version": VERSION, "state": "DATASET_V1_RELEASED"}
    excluded = [{"scene_id": "L18-06", "reason": "human decision"},
                {"scene_id": "L18-08", "reason": "human decision"}]
    return rows, [dict(row) for row in rows], excluded, release


def validate(rows, excluded, release):
    base = [{k: v for k, v in row.items() if k != "split"} for row in rows]
    return verify_rows(base, rows, excluded, release)


def test_fixture_only_valid_shape_is_not_a_training_approval():
    rows, _, excluded, release = fixture_rows()
    result = validate(rows, excluded, release)
    assert result["approved"] == 18 and result["family_count"] == 5
    assert result["contact_health"] == "HOLD"


@pytest.mark.parametrize("name", ["../secret", "a/../../b", "/tmp/x", "a//b",
                                  "a/./b", "a\\b", "C:/x", ""])
def test_unsafe_paths_denied(name):
    assert not safe_name(name)


def test_path_symlink_denied(tmp_path):
    outside = tmp_path / "outside"
    outside.write_text("private")
    (tmp_path / "link").symlink_to(outside)
    with pytest.raises(IntakeHold, match="C_V1_SYMLINK_FORBIDDEN"):
        checked_path(tmp_path, "link")


def test_real_root_absent_is_hold(tmp_path):
    with pytest.raises(IntakeHold, match="C_V1_PRIVATE_ROOT_INACCESSIBLE"):
        verify_release_root(tmp_path / "absent")


def test_test_split_changed_rejected():
    rows, _, excluded, release = fixture_rows()
    next(r for r in rows if r["split"] == "test")["split"] = "train"
    with pytest.raises(IntakeHold, match="C_V1_FROZEN_SPLIT_COUNTS_CHANGED"):
        validate(rows, excluded, release)


def test_label_flip_denied():
    rows, _, excluded, release = fixture_rows()
    rows[0]["label"] = "UNSTABLE"
    with pytest.raises(IntakeHold, match="C_V1_FROZEN_SPLIT_COUNTS_CHANGED"):
        validate(rows, excluded, release)


def test_duplicate_stack_denied():
    rows, _, excluded, release = fixture_rows()
    rows[0]["stack_id"] = rows[1]["stack_id"]
    with pytest.raises(IntakeHold, match="C_V1_LAYOUT_OR_IMAGE_DUPLICATE"):
        validate(rows, excluded, release)


def test_mock_and_wrong_rights_denied():
    for key, value in [("source", "CONTRACT_FIXTURE"),
                       ("ground_truth", "MOCK_ONLY"),
                       ("license_status", "UNKNOWN")]:
        rows, _, excluded, release = fixture_rows()
        rows[0][key] = value
        with pytest.raises(IntakeHold, match="C_V1_UNVERIFIED_OR_MOCK_ROW"):
            validate(rows, excluded, release)


def test_family_split_policy_cannot_be_changed():
    rows, _, excluded, release = fixture_rows()
    release["family_assignment"][f"{1:064x}"] = "test"
    with pytest.raises(IntakeHold, match="C_V1_FAMILY_ASSIGNMENT_CHANGED"):
        validate(rows, excluded, release)


def test_evidence_digest_cross_check_denied():
    rows, _, excluded, release = fixture_rows()
    row = rows[0]
    name = json.loads(row["capture_config"])["physics_evidence"]
    release["files"][name] = "0" * 64
    with pytest.raises(IntakeHold, match="C_V1_REGISTRY_ROW_HASH_MISMATCH"):
        validate(rows, excluded, release)


def test_excluded_layout_cannot_enter_training():
    rows, _, excluded, release = fixture_rows()
    rows[0]["scene_id"] = "L18-06"
    with pytest.raises(IntakeHold, match="C_V1_EXCLUDED_SAMPLE_IN_TRAINING"):
        validate(rows, excluded, release)


def test_contact_hold_cannot_be_lifted_by_c():
    rows, _, excluded, release = fixture_rows()
    release["contact_health"] = "PASS"
    with pytest.raises(IntakeHold, match="C_V1_RELEASE_POLICY_MISMATCH"):
        validate(rows, excluded, release)
