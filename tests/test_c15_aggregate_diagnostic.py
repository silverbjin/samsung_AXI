"""C15 P2 aggregate-only tests; no Torch, private data, Test or model inference."""
import copy
import json
from pathlib import Path
import pytest
from ai.train.c15_aggregate_diagnostic import audit,AuditHold

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=ROOT/"ai/docs/C_V1_P2_AGGREGATE_EVIDENCE_LOCK.json"

def snapshot():
    return json.loads(SNAPSHOT.read_text(encoding="utf8"))

def test_original_public_owner_aggregate_passes_without_test():
    r=audit(snapshot())
    assert r["verdict"]=="C15_EVIDENCE_DIAGNOSIS_COMPLETE_PERFORMANCE_HOLD"
    assert r["train"]["correct"]==4 and r["validation"]["correct"]==1
    assert r["train"]["majority_correct"]==8 and r["validation"]["majority_correct"]==2
    assert r["best_epoch"]==3 and r["planned_optimizer_steps"]==9
    assert not r["P3_test_opened"] and not r["P3_test_authorized"]
    assert not r["retraining_authorized"] and not r["test_evaluated"]
    assert len(r["not_determinable"])>=5

@pytest.mark.parametrize(("field","bad"),[
  ("source_summary_sha256","0"*64),("checkpoint_sha256","0"*64),
  ("experiment_lock_sha256","0"*64),("pretest_verdict","PASS_MODEL"),
  ("selected_epoch",2),("test_opened",True),("test_evaluated",True),
  ("test_used_for_training",True),("test_sealed_count",0),
  ("model_accepted",True),("AI_OFF","DISABLED"),
  ("A19","AUTHORIZED"),("E_AI_ON","PASS"),
  ("production_contact","PASS")])
def test_unauthorized_edits_hold(field,bad):
    x=snapshot();x[field]=bad
    with pytest.raises(AuditHold):audit(x)

@pytest.mark.parametrize(("epoch_index","split","field","bad"),[
  (0,"train","accuracy",.3333333),
  (0,"val","accuracy",.5),
  (2,"train","samples",10),
  (2,"val","samples",2),
  (2,"val","loss",float("nan")),
  (2,"val","loss",-1)])
def test_corrupted_aggregates_hold(epoch_index,split,field,bad):
    x=snapshot();x["epochs"][epoch_index][split][field]=bad
    with pytest.raises(AuditHold):audit(x)

def test_no_test_per_sample_probability_or_raw_data_used():
    source=(ROOT/"ai/train/c15_aggregate_diagnostic.py").read_text()
    assert "torch.load(" not in source
    assert "read_verified_split(" not in source
    assert "predict_pil(" not in source
    assert "test_sealed_count" in source
    assert "CLASS_SPECIFIC_CONFUSION_OR_UNSTABLE_FALSE_NEGATIVES" in source
