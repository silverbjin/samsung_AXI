"""R03 DBG01: fail-closed independent verdicts and read-only archive review."""
import argparse
import hashlib
import json
import re
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

OLD_SHA="194db1429899775174096e24cde2e785feecda6b"
OLD_RAW="4f4328e6d40ba2936467f4f462364869c2f5662a6d71565d05a9961d4ab4342f"
OLD_OWNER="39c64fc10bdd1d2bd28477925829f879373042bd1af41b42f855657e53f40aa5"
MAX_BYTES=128*1024*1024

def require(ok,reason):
    if not ok: raise ValueError(reason)

def digest(path):
    with Path(path).open("rb") as f: return hashlib.file_digest(f,"sha256").hexdigest()

def unpack_verified(archive,target):
    """Verify exact manifest coverage, no duplicate/traversal/symlink members."""
    target=Path(target)
    require(target.is_dir() and not any(target.iterdir()),"DBG_TARGET_NOT_EMPTY")
    names=set(); size=0
    with tarfile.open(archive,"r:gz") as t:
        for m in t:
            p=PurePosixPath(m.name)
            require(m.isfile() and not p.is_absolute() and ".." not in p.parts
                    and m.name==p.as_posix() and m.name not in names
                    and not any(x=="approval_ledger.jsonl" for x in p.parts),"DBG_UNSAFE_MEMBER")
            size+=m.size
            require(size<=MAX_BYTES and len(names)<500,"DBG_ARCHIVE_LIMIT")
            names.add(m.name)
            dest=target/m.name; dest.parent.mkdir(parents=True,exist_ok=True)
            with t.extractfile(m) as src, dest.open("xb") as out:
                while chunk:=src.read(1024*1024): out.write(chunk)
    require("SHA256SUMS" in names,"DBG_MANIFEST_MISSING")
    checked=set()
    for line in (target/"SHA256SUMS").read_text().splitlines():
        h,n=line.split("  ",1)
        require(re.fullmatch("[0-9a-f]{64}",h) and n in names-{"SHA256SUMS"}
                and n not in checked and digest(target/n)==h,"DBG_MANIFEST_MISMATCH")
        checked.add(n)
    require(checked==names-{"SHA256SUMS"},"DBG_MANIFEST_COVERAGE")
    return len(checked)

def read(root,name):
    return json.loads((Path(root)/name).read_text())

def classify(summary,trial,cleanup,diag=None,roles=None):
    """Called ONLY after actual physical evidence + manifest verification."""
    error=summary.get("first_error")
    gui=trial.get("gui_verdict")
    rows=cleanup.get("owned_processes",[])
    require(bool(rows) and all(type(x.get("pid")) is int for x in rows)
            and len({x["pid"] for x in rows})==len(rows),"DBG_CLEANUP_IDENTITY")
    stopped=cleanup.get("all_owned_processes_stopped") is True and all(
        x.get("stopped") is True and type(x.get("returncode_after_cleanup")) is int for x in rows)
    require(trial.get("sensor_physics_verdict")=="PASS","DBG_PHYSICS_NOT_PASS")
    require(gui in ("PASS","FAIL","NOT_REQUESTED"),"DBG_GUI_VERDICT_INVALID")
    gui_pid=None
    if error:
        m=re.fullmatch(r"A13_GAZEBO_GUI_EARLY_EXIT_RC=(-?[0-9]+)",error)
        require(m and gui=="FAIL" and trial.get("gui_failure_reason")==error and diag
                and diag.get("phase")=="evidence_verification"
                and diag.get("first_error")=="RuntimeError: "+error,"DBG_NOT_GUI_ONLY_FAILURE")
        rc=int(m.group(1))
        before=diag.get("owned_processes_before_cleanup",[])
        require(bool(before) and before[0].get("running_at_failure") is True
                and before[-1].get("returncode_at_failure")==rc
                and before[-1].get("running_at_failure") is False,"DBG_SERVER_OR_GUI_BOUNDARY")
        gui_pid=before[-1]["pid"]
        require(any(x["pid"]==gui_pid and x.get("returncode_after_cleanup")==rc for x in rows),
                "DBG_GUI_EXIT_MISMATCH")
    else:
        require(summary.get("verdict")=="GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS"
                and gui!="FAIL","DBG_UNEXPECTED_RUNNER_STATE")
    if roles is not None:
        require(set(roles)=={x["pid"] for x in rows} and list(roles.values()).count("server")==1,
                "DBG_ROLE_MAP_INVALID")
        guis=[pid for pid,role in roles.items() if role=="gui"]
        require(len(guis)==int(gui!="NOT_REQUESTED"),"DBG_GUI_ROLE")
        if gui_pid is not None: require(guis==[gui_pid],"DBG_GUI_ROLE_MISMATCH")
        gui_pid=guis[0] if guis else None
    else:
        require(gui=="FAIL" and gui_pid is not None,"DBG_LEGACY_ROLE_UNKNOWN")
    nongui=[x for x in rows if x["pid"]!=gui_pid]
    clean=stopped and bool(nongui) and all(x["returncode_after_cleanup"]==0 for x in nongui)
    if gui=="PASS":
        clean=clean and any(x["pid"]==gui_pid and x["returncode_after_cleanup"]==0 for x in rows)
    return {"sensor_physics":"PASS","production_integration":"PASS","gui":gui,
            "cleanup":"PASS" if clean else "FAIL","all_owned_stopped":stopped,
            "evidence_integrity":"PASS","ground_truth":"UNKNOWN_HOLD","human_approved":False,
            "data_verdict":"PASS","overall":"EVIDENCE_PASS_GT_HOLD" if clean else "HOLD_CLEANUP",
            "next_independent_scene_allowed":stopped,"gui_error":error,
            "processes":rows}

def review(archive,pin,scene,reviewer_sha,*,reuse=False,trace=None):
    require(not __debug__ is False,"DBG_PYTHON_OPTIMIZED")
    require(re.fullmatch("[0-9a-f]{40}",pin) and re.fullmatch("[0-9a-f]{40}",reviewer_sha),
            "DBG_SHA_FORMAT")
    archive=Path(archive)
    raw_sha=digest(archive)
    if reuse:
        require(pin==OLD_SHA and scene=="ST-02" and raw_sha==OLD_RAW and trace is None,
                "DBG_REUSE_PIN_OR_HASH")
    else:
        require(pin==reviewer_sha and trace is not None,"DBG_NEW_SOURCE_SHA")
    with tempfile.TemporaryDirectory(prefix="a14_r03_review_") as tmp:
        root=Path(tmp)
        count=unpack_verified(archive,root)
        t=root/"trial_0001"
        s=read(root,"summary.json"); trial=read(t,"trial_summary.json")
        cleanup=read(t,"process_cleanup.json")
        cfg=read(t,"scenario.scenario.json")
        require(s["source_sha"]==trial["source_sha"]==cleanup["source_sha"]==pin,
                "DBG_SOURCE_SHA_MISMATCH")
        require(trial["scene_id"]==cleanup["scenario_id"]==cfg["scene_id"]==scene
                and trial["trial_id"]==cfg["trial_id"] and trial["seed"]==cfg["seed"],
                "DBG_SCENE_IDENTITY")
        require(trial["motion"]["observation"]=={"ST-02":"HELD_OBSERVED","UN-01":"FALL_OBSERVED"}[scene],
                "DBG_MOTION_MISMATCH")
        from smartdish_tray_evidence import verify_trial as verify_a13
        from a14_r02_production_verify import verify
        from a14_r02_production_collect import expected_sensors,cross_check
        from a14_physics_freshness_contract import evaluate,read_rows
        from a14_production_health_probe import read_ecm
        require(verify_a13(t),"DBG_A13_VERIFY")
        report=verify(t,pin)
        expected=expected_sensors(t/"scenario.sdf")
        rows,overflow=read_ecm(t/"ecm_contact_steps.tsv")
        require(not overflow,"DBG_ECM_OVERFLOW")
        start,end=report["start_ns"],report["end_ns"]
        raw=[json.loads(x) for x in (t/"r02_3_ros_contacts.jsonl").read_text().splitlines()]
        refresh=evaluate(read_rows(t/"ecm_contact_steps.tsv"),list(expected),start,end)
        ok,stats=cross_check(expected,rows,raw,start,end)
        require(ok and refresh["refresh_contract_pass"] and refresh==report["refresh"]
                and stats==report["transport"],"DBG_RAW_RECOMPUTATION_MISMATCH")
        roles=None
        if trace is not None:
            require(trace["source_sha"]==pin and trace["scene_id"]==scene,"DBG_TRACE_IDENTITY")
            roles={x["pid"]:x["role"] for x in trace["events"] if x["event"]=="launch"}
            ends={x["pid"]:x for x in trace["events"] if x["event"]=="cleanup_end"}
            require(set(ends)==set(roles) and all(ends[x["pid"]]["rc"]==x["returncode_after_cleanup"]
                   for x in cleanup["owned_processes"]),"DBG_TRACE_CLEANUP")
        diag=read(t,"failure_diagnostics.json") if (t/"failure_diagnostics.json").exists() else None
        verdict=classify(s,trial,cleanup,diag,roles)
        verdict.update(source_sha=pin,reviewer_sha=reviewer_sha,scene_id=scene,
                       trial_id=cfg["trial_id"],stack_id=cfg["stack_id"],seed=cfg["seed"],
                       archive_sha256=raw_sha,manifest_count=count,reused=reuse,
                       capture_ns=report["capture_ns"],start_ns=start,end_ns=end,
                       raw_ros_count=len(raw),refresh=refresh,transport=stats)
        return verdict

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--sha",required=True)
    p.add_argument("--reviewer-sha",required=True)
    p.add_argument("--scene",required=True,choices=["ST-02","UN-01"])
    p.add_argument("--reuse",action="store_true")
    p.add_argument("--trace",type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    try:
        result=review(a.archive,a.sha,a.scene,a.reviewer_sha,reuse=a.reuse,
                      trace=read(a.trace.parent,a.trace.name) if a.trace else None)
        rc=0 if result["next_independent_scene_allowed"] else 2
    except Exception as exc:
        result={"overall":"HOLD","data_verdict":"HOLD","first_error":str(exc) or type(exc).__name__,
                "ground_truth":"UNKNOWN_HOLD","human_approved":False};rc=2
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("R03_DBG_VERDICT="+json.dumps(result,sort_keys=True),flush=True)
    return rc
if __name__=="__main__":
    raise SystemExit(main())
