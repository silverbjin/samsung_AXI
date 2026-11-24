"""A-13 evidence immutability, timing and no false ground truth (unit only)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace as N

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_tray_evidence import (
    classify_motion,verify_timing,pose_from_transform,verify_trial,digest,manifest)


def test_physics_classification_is_observation_not_label():
    a={"dish_01":{"x":0.,"y":0.,"z":.59,"tilt_deg":0}}
    same={"dish_01":{"x":0.,"y":0.,"z":.58,"tilt_deg":0}}
    drop={"dish_01":{"x":.54,"y":0.,"z":.03,"tilt_deg":45}}
    st=classify_motion(a,same,["dish_01"],.57)
    un=classify_motion(a,drop,["dish_01"],.57)
    assert st["observation"]=="HELD_OBSERVED"
    assert un["observation"]=="FALL_OBSERVED"
    assert st["label"]==un["label"]=="REVIEW_REQUIRED"
    assert st["ground_truth"]=="NOT_OPERATOR_APPROVED"


@pytest.mark.parametrize("timing,reason",[
  ((10,12,8_000_000_013,11,[10,20,30]),"PHYSICS_DURATION_TOO_SHORT"),
  ((20,12,10_000_000_013,20,[10,20,30]),"IMAGE_AFTER_PHYSICS"),
  ((10,12,10_000_000_013,400_000_000,[10,20,30]),"IMAGE_POSE_SYNC"),
  ((10,12,10_000_000_013,10,[10,10,10]),"STALE_OR_REORDERED"),
])
def test_bad_timing_fails_closed(timing,reason):
    with pytest.raises(ValueError,match=reason):
        verify_timing(*timing)


def test_pose_requires_true_entity_name_and_normalized_rotation():
    t=N(child_frame_id="smartdish_tray::dish_01::body",
        transform=N(translation=N(x=0.,y=0.,z=.55),
                    rotation=N(x=0.,y=0.,z=0.,w=1.)))
    name,p=pose_from_transform(t)
    assert name=="dish_01" and p["z"]==.55
    t.child_frame_id="not_a_dish"
    assert pose_from_transform(t) is None
    t.child_frame_id="dish_01"
    t.transform.rotation.w=0.
    with pytest.raises(ValueError,match="QUATERNION"):
        pose_from_transform(t)


def test_valid_time_alignment_contract():
    assert verify_timing(200_000_000, 210_000_000, 10_310_000_000,
                         202_000_000, [200_000_000,400_000_000,
                                       600_000_000]) is None


def test_reject_empty_evidence_and_hash_drift(tmp_path):
    with pytest.raises(ValueError,match="EMPTY_OR_MISSING"):
        verify_trial(tmp_path)
    (tmp_path/"sample.log").write_bytes(b"a")
    s,n=digest(tmp_path/"sample.log")
    assert n==1 and len(s)==64
    assert len(manifest(tmp_path))==1
