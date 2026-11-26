"""R02-3 production archive review; no human approval."""
import argparse
import hashlib
import json
from pathlib import Path
from smartdish_a14_verify import verify_trial

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(trial,pin):
    trial=Path(trial)
    qa=json.loads((trial/"a14_gt_candidate.json").read_text())
    r=json.loads((trial/"r02_3_health_result.json").read_text())
    summary=json.loads((trial/"trial_summary.json").read_text())
    core=verify_trial(trial,pin)
    assert all(v for k,v in core["checks"].items() if k!="A14_CONTACT_EVIDENCE_PASS")
    assert r["source_sha"]==pin and r["scope"]=="PRODUCTION_RGB_T0_OBSERVATION_SAME_RUN"
    assert r["integration_evidence_pass"] and r["refresh"]["refresh_contract_pass"]
    assert qa["evidence_sha256"]["r02_3_health_result"]==sha(trial/"r02_3_health_result.json")
    for key,name in (("ecm_sha256","ecm_contact_steps.tsv"),("raw_ros_sha256","r02_3_ros_contacts.jsonl"),
                     ("clock_samples_sha256","r02_3_clock_samples.json"),("runtime_world_sha256","sensor_preflight.sdf"),
                     ("scenario_sha256","scenario.sdf")):
        assert r[key]==sha(trial/name),(key,name)
    assert r["capture_ns"]==qa["rgb_t0_sim_time_ns"]<=r["start_ns"]
    assert (r["start_ns"],r["end_ns"])==(qa["observation_start_ns"],qa["observation_end_ns"])
    assert r["end_ns"]-r["start_ns"]>=10_000_000_000
    assert r["production_contact_health"]=="HOLD" and qa["rule_candidate"]=="UNKNOWN"
    assert r["human_approved"] is False and qa["human_approved"] is False
    assert qa["quality_verdict"]=="HOLD" and not (trial/"approval_ledger.jsonl").exists()
    assert summary["actual_runtime_world_sha256"]==r["runtime_world_sha256"]
    return r
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--trial",required=True,type=Path);p.add_argument("--sha",required=True)
    a=p.parse_args();r=verify(a.trial,a.sha)
    print("R02_3_REAL_PRODUCTION_EVIDENCE_PASS_GT_HOLD="+r["scene_id"],flush=True)
