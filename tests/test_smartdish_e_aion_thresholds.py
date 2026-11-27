"""Owner approved integration: per-class decision confidence threshold tests.

Synthetic-only: the numerical confidence is provided by stub predictor; this
suite never reads private images/weights, changes B ground-truth or sends Goals.
"""
import math
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_ai"))
from smartdish_ai.inference_core import InferenceCore

def frame():
    return bytes([30,80,120])*256

def classify(label, conf, stable=.80, unstable=.80, capture="CAP1"):
    m=InferenceCore(lambda *_:(label,conf),"fixture-stub",
        stable_confidence_min=stable,unstable_confidence_min=unstable)
    assert m.cache_rgb(frame(),16,16,received_at=9)
    return m.handle_request('{"request_id":"REQ","capture_id":"'+capture+'"}',now=10)

@pytest.mark.parametrize("label,conf,st,un,expected",[
    ("STABLE",.70,.65,.90,"STABLE"),
    ("STABLE",.70,.75,.50,"UNKNOWN"),
    ("UNSTABLE",.70,.90,.65,"UNSTABLE"),
    ("UNSTABLE",.70,.50,.75,"UNKNOWN"),
    ("STABLE",.80,.80,.80,"STABLE"),
    ("UNSTABLE",.80,.80,.80,"UNSTABLE"),
])
def test_dynamic_label_thresholds_are_independent(label,conf,st,un,expected):
    resp=classify(label,conf,st,un)
    assert resp["status"]==expected
    assert resp["confidence"]==(conf if expected!="UNKNOWN" else None)
    assert resp["model_version"]=="fixture-stub"

def test_change_during_runtime_uses_latest_value_for_next_capture():
    m=InferenceCore(lambda *_:("STABLE",.70),"fixture-stub")
    assert m.cache_rgb(frame(),16,16,received_at=5)
    assert m.handle_request('{"request_id":"R","capture_id":"C1"}',now=6)["status"]=="UNKNOWN"
    assert m.set_decision_thresholds(.65,.95)==(.65,.95)
    assert m.cache_rgb(frame(),16,16,received_at=6,stamp_ns=234)
    assert m.handle_request('{"request_id":"R","capture_id":"C2"}',now=7)["status"]=="STABLE"

@pytest.mark.parametrize("value",[None,False,True,float("nan"),float("inf"),float("-inf"),.49,1.01,"0.7"])
def test_invalid_update_fails_closed_and_is_atomic(value):
    m=InferenceCore()
    assert m.decision_thresholds()==(.80,.80)
    with pytest.raises(ValueError,match="C_INVALID_CLASS_DECISION_THRESHOLD"):
        m.set_decision_thresholds(.70,value)
    assert m.decision_thresholds()==(.80,.80)
    with pytest.raises(ValueError,match="C_INVALID_CLASS_DECISION_THRESHOLD"):
        m.set_decision_thresholds(value,.70)
    assert m.decision_thresholds()==(.80,.80)

def test_unknown_when_no_predictor_even_with_low_threshold():
    m=InferenceCore(stable_confidence_min=.50,unstable_confidence_min=.50)
    m.cache_rgb(frame(),16,16,received_at=5)
    r=m.handle_request('{"request_id":"R","capture_id":"C"}',now=6)
    assert (r["status"],r["confidence"],r["model_version"])==("UNKNOWN",None,"none")
