#!/usr/bin/env python3
"""Reuse the passed R02-1 diagnostic, with one opt-in metadata challenge."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import a14_production_health_probe as probe
from a14_physics_freshness_contract import evaluate, read_rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sha",required=True)
    p.add_argument("--plugin",required=True,type=Path)
    p.add_argument("--out-dir",required=True,type=Path)
    a=p.parse_args()
    folder=a.out_dir.resolve()
    original=probe.prepare
    def prepare(root,plugin):
        expected,world,bridge=original(root,plugin)
        tree=ET.parse(world)
        element=tree.find("./world/plugin[@name='smartdish::A14ProductionHealth']")
        ET.SubElement(element,"late_control").text="true"
        tree.write(world,encoding="utf-8",xml_declaration=True)
        return expected,world,bridge
    probe.prepare=prepare
    rc=probe.run(a.sha,a.plugin.resolve(),folder)
    report=json.loads((folder/"health_result.json").read_text())
    result={"refresh_contract_pass":False,"source_sha":a.sha,"production_contact_health":"HOLD",
            "rule_candidate":"UNKNOWN","human_approved":False,"first_error":report.get("first_error")}
    try:
        if rc: raise RuntimeError("R02_1_DIAGNOSTIC_FAILED")
        result.update(evaluate(read_rows(folder/"ecm_contact_steps.tsv"),list(report["sensors"]),
                              report["start_ns"],report["end_ns"],diagnostic=True))
        if not result["refresh_contract_pass"]: raise RuntimeError("R02_2_METADATA_CHALLENGE_FAILED")
    except Exception as exc: result["first_error"]=str(exc)
    (folder/"freshness_result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    import hashlib
    target=folder/"freshness_result.json"
    (folder/"freshness_result.json.sha256").write_text(hashlib.sha256(target.read_bytes()).hexdigest()+"  "+target.name+"\n")
    print("R02_2_REFRESH_CONTRACT_PASS="+str(result["refresh_contract_pass"]).lower(),flush=True)
    return 0 if result["refresh_contract_pass"] else 1
if __name__=="__main__":
    sys.exit(main())
