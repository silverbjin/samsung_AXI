#!/usr/bin/env python3
"""SmartDish A WSLg release qualification: CI SHA + renderer + real smoke.

This is a release gate, never a substitute for real Gazebo sensor evidence.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import urllib.request

REPO="silverbjin/samsung_AXI"
WORKFLOWS={
    "SmartDish A11-A13 Tray RGB physics evidence",
    "SmartDish A Navigation Adapter L0 and L1",
    "Restaurant Robot MVP CI",
}
STAGES=("ST-02","UN-01")
OUTCOMES=("HELD_OBSERVED","FALL_OBSERVED")
WALL_PER_SIM_LIMIT=15.0
HASH=re.compile(r"^[0-9a-f]{40}$")


def renderer_profile(info: str, allow_software: bool):
    lines=info.splitlines()
    renderer=next((line.split(":",1)[1].strip() for line in lines
                   if line.startswith("OpenGL renderer string:")),None)
    if not renderer:
        raise RuntimeError("A13_WSLG_RENDERER_UNKNOWN")
    software=bool(re.search(r"llvmpipe|softpipe|swrast|software raster",renderer,re.I))
    if software and not allow_software:
        raise RuntimeError("A13_WSLG_SOFTWARE_RENDERER_UNAPPROVED")
    return {"renderer":renderer,"software":software,"profile":
            "OPERATOR_APPROVED_SOFTWARE_REQUIRES_REAL_SMOKE"
            if software else "HARDWARE_REQUIRES_REAL_SMOKE",
            "accelerated":not software}


def completed_ci_runs(runs: list, source_sha: str):
    if not HASH.fullmatch(source_sha):
        raise RuntimeError("A13_RELEASE_SHA_FORMAT_INVALID")
    found={}
    for row in runs:
        if row.get("head_sha")!=source_sha or row.get("name") not in WORKFLOWS:
            continue
        if row.get("status")=="completed" and row.get("conclusion")=="success":
            found[row["name"]]={"run_id":row["id"],"url":row["html_url"],
                                  "head_sha":source_sha}
    missing=sorted(WORKFLOWS-set(found))
    if missing:
        raise RuntimeError("A13_CI_SAME_SHA_GREEN_MISSING "+", ".join(missing))
    return found


def request_ci_runs():
    url=("https://api.github.com/repos/"+REPO+
         "/actions/runs?branch=feat%2Fsmartdish-a-tray-camera&per_page=60")
    req=urllib.request.Request(url,headers={
        "Accept":"application/vnd.github+json",
        "User-Agent":"SmartDish-A-WSLg-release-gate"})
    with urllib.request.urlopen(req,timeout=12) as response:
        return json.load(response)["workflow_runs"]


def verify_gui_report(report_path: Path, source_sha: str, profile: str):
    """Verify actual GUI process evidence + immutable tar SHA, never glxinfo alone."""
    from smartdish_a_tray_gui_preflight import PROFILES
    if profile not in PROFILES:
        raise RuntimeError("A13_GUI_PROFILE_UNAPPROVED")
    report=json.loads(report_path.read_text())
    if (report.get("source_sha")!=source_sha or
        report.get("profile")!=profile or
        report.get("verdict")!="GAZEBO_GUI_PROCESS_STABLE_NO_GLX_ERROR" or
        report.get("gazebo_server_ready") is not True or
        report.get("gui_started") is not True or
        report.get("all_owned_processes_stopped") is not True or
        float(report.get("gui_survival_wall_s",0))<8.0):
        raise RuntimeError("A13_GUI_CONTEXT_PREFLIGHT_EVIDENCE_NOT_ACCEPTED")
    archive=report_path.parent/"gui_preflight_evidence.tar.gz"
    if not archive.is_file():
        raise RuntimeError("A13_GUI_CONTEXT_ARCHIVE_MISSING")
    with tarfile.open(archive,"r:gz") as t:
        names=set(t.getnames())
        if not {"gui_preflight_result.json","SHA256SUMS","gazebo_gui.log",
                "gazebo_server.log","minimal_gui_world.sdf"}<=names:
            raise RuntimeError("A13_GUI_CONTEXT_EVIDENCE_INCOMPLETE")
        for line in t.extractfile("SHA256SUMS").read().decode().splitlines():
            digest,relative=line.split("  ",1)
            if relative not in names or hashlib.sha256(
                    t.extractfile(relative).read()).hexdigest()!=digest:
                raise RuntimeError("A13_GUI_CONTEXT_ARCHIVE_HASH_MISMATCH")
        if t.extractfile("gui_preflight_result.json").read()!=report_path.read_bytes():
            raise RuntimeError("A13_GUI_CONTEXT_REPORT_ARCHIVE_MISMATCH")
    return {"verdict":"GAZEBO_GUI_PROCESS_STABLE_NO_GLX_ERROR",
            "source_sha":source_sha,"profile":profile,
            "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),
            "report_sha256":hashlib.sha256(report_path.read_bytes()).hexdigest(),
            "gui_survival_wall_s":report["gui_survival_wall_s"],
            "archive_path":str(archive.resolve()),
            "context_diagnostics":"REAL_GUI_PROCESS_SURVIVAL_NO_FATAL_GLX_ERROR"}


def preflight(source_sha: str, root: Path, output: Path):
    current=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                    text=True,timeout=8).strip()
    if source_sha!=current:
        raise RuntimeError("A13_RELEASE_EXECUTION_SHA_MISMATCH")
    runs=completed_ci_runs(request_ci_runs(),source_sha)
    env=os.environ
    if not (env.get("WSL_DISTRO_NAME") and
            "microsoft" in Path("/proc/sys/kernel/osrelease").read_text().lower()):
        raise RuntimeError("A13_WSLG_RELEASE_REQUIRES_REAL_WSL2")
    if not (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY")):
        raise RuntimeError("A13_WSLG_DISPLAY_MISSING")
    renderer=subprocess.run(["glxinfo","-B"],capture_output=True,text=True,
                            timeout=8,check=True)
    profile=renderer_profile(renderer.stdout,
            env.get("SMARTDISH_A_TRAY_ALLOW_SOFTWARE_RENDERER")=="1")
    from smartdish_a_tray_gui_preflight import PROFILES
    gui_profile=env.get("SMARTDISH_A_TRAY_GUI_PROFILE","xcb")
    if gui_profile not in PROFILES:
        raise RuntimeError("A13_GUI_PROFILE_UNAPPROVED")
    manifest={"schema":1,"source_sha":source_sha,"verdict":"CI_PASS_RENDER_APPROVED",
              "ci_runs":runs,"renderer":profile,
              "operator_software_approval":bool(profile["software"]),
              "gui_profile":gui_profile,"gui_preflight":None,
              "wsl_distro":env["WSL_DISTRO_NAME"],
              "capture_required":["ST-02","UN-01"],
              "wall_per_sim_limit":WALL_PER_SIM_LIMIT,
              "status":"PROVISIONAL_UNTIL_REAL_WSLG_SMOKE_PASS",
              "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("SMARTDISH_A_TRAY_WSLG_CI_RENDER_PREFLIGHT_PASS="+str(output),flush=True)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_smoke(archive: Path, source_sha: str, limit=WALL_PER_SIM_LIMIT, profile=None):
    if not archive.is_file():
        raise RuntimeError("A13_SMOKE_ARCHIVE_MISSING")
    with tarfile.open(archive,"r:gz") as t:
        names=set(t.getnames())
        if not {"summary.json","SHA256SUMS"}<=names:
            raise RuntimeError("A13_SMOKE_MANIFEST_MISSING")
        shas=t.extractfile("SHA256SUMS").read().decode()
        for line in shas.splitlines():
            h, relative=line.split("  ",1)
            if relative not in names or sha256(t.extractfile(relative).read())!=h:
                raise RuntimeError("A13_SMOKE_EVIDENCE_SHA_MISMATCH_"+relative)
        summary=json.load(t.extractfile("summary.json"))
        if (summary.get("source_sha")!=source_sha or
            summary.get("mode")!="smoke" or not summary.get("gui") or
            summary.get("verdict")!="ST02_UN01_REAL_CAMERA_SMOKE_PASS"):
            raise RuntimeError("A13_SMOKE_SUMMARY_INVALID")
        trials=summary.get("trials",[])
        if ([r.get("scene_id") for r in trials]!=list(STAGES) or
            [r.get("motion",{}).get("observation") for r in trials]!=list(OUTCOMES)):
            raise RuntimeError("A13_SMOKE_SCENARIO_TRANSITION_NOT_VERIFIED")
        for i,row in enumerate(trials,1):
            if row.get("source_sha")!=source_sha or not row.get("gui_active_during_physics"):
                raise RuntimeError("A13_SMOKE_SHA_OR_GUI_MISMATCH")
            if (row.get("sensor_physics_verdict")!="PASS" or
                    row.get("gui_verdict")!="PASS"):
                raise RuntimeError("A13_SMOKE_INDEPENDENT_GATES_NOT_GREEN")
            if profile is not None and row.get("gui_profile")!=profile:
                raise RuntimeError("A13_SMOKE_GUI_PROFILE_MISMATCH")
            stamps=row.get("image_stamp_samples",[])
            if (len(stamps)<3 or any(b<=a for a,b in zip(stamps,stamps[1:])) or
                stamps[0]<row["capture_stamp_ns"]):
                raise RuntimeError("A13_SMOKE_IMAGE_STAMPS_INVALID")
            elapsed=float(row.get("trial_wall_elapsed_seconds",float("inf")))
            sim=float(row["observation_end_ns"]-row["pre_observation_spawn_sim_ns"])/1e9
            if sim<=0 or elapsed/sim>limit:
                raise RuntimeError("A13_SMOKE_RENDER_PERFORMANCE_PROFILE_FAILED")
            path="trial_%04d/process_cleanup.json"%i
            cleanup=json.load(t.extractfile(path)) if path in names else {}
            if cleanup.get("all_owned_processes_stopped") is not True:
                raise RuntimeError("A13_SMOKE_OWNED_PROCESS_CLEANUP_FAILED")
            for artifact in ("tray_rgb.png","physics_observations.jsonl"):
                if "trial_%04d/"%i+artifact not in names:
                    raise RuntimeError("A13_SMOKE_SENSOR_PHYSICS_EVIDENCE_MISSING")
        return {"sha":source_sha,"archive_sha256":sha256(archive.read_bytes()),
                "scenes":list(STAGES),"verdict":"REAL_WSLG_SMOKE_PASS"}


def final_receipt(archive: Path, gate_file: Path, source_sha: str):
    if not archive.is_file():
        raise RuntimeError("A13_BATCH_ARCHIVE_MISSING")
    gate=json.loads(gate_file.read_text())
    if (gate.get("source_sha")!=source_sha or
            gate.get("status")!="REAL_WSLG_SMOKE_PASS" or
            gate.get("gui_preflight",{}).get("verdict")!="GAZEBO_GUI_PROCESS_STABLE_NO_GLX_ERROR"):

        raise RuntimeError("A13_DEPLOYMENT_GATE_MANIFEST_INVALID")
    with tarfile.open(archive,"r:gz") as t:
        s=json.load(t.extractfile("summary.json"))
        if (s.get("source_sha")!=source_sha or s.get("mode")!="batch" or
            s.get("verdict")!="GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS" or
            len(s.get("trials",[]))!=4):
            raise RuntimeError("A13_FINAL_BATCH_NOT_GREEN")
        for row in s["trials"]:
            if (row.get("sensor_physics_verdict")!="PASS" or
                row.get("gui_verdict")!="PASS" or
                row.get("gui_profile")!=gate["gui_profile"]):
                raise RuntimeError("A13_FINAL_SENSOR_GUI_GATES_NOT_GREEN")
        names=set(t.getnames())
        if "deployment_gate_manifest.json" not in names:
            raise RuntimeError("A13_PINNED_GATE_MANIFEST_NOT_PACKAGED")
        bound=json.load(t.extractfile("deployment_gate_manifest.json"))
        if bound!=gate:
            raise RuntimeError("A13_DEPLOYMENT_GATE_MANIFEST_CHANGED")
    receipt={"schema":1,"source_sha":source_sha,"verdict":"READY_FOR_OWNER_VISUAL_REVIEW",
             "evidence_archive":str(archive.resolve()),
             "archive_sha256":sha256(archive.read_bytes()),
             "wslg_smoke_sha256":gate["smoke"]["archive_sha256"],
             "ci_runs":gate["ci_runs"],
             "operator_visual_review":"NOT_RUN"}
    out=archive.parent/"deployment_receipt.json"
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("SMARTDISH_A_TRAY_WSLG_GATES_GREEN_VISUAL_REVIEW_PENDING="+str(out))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["preflight","gui","smoke","finalize"])
    p.add_argument("--sha",required=True)
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--manifest",type=Path)
    p.add_argument("--archive",type=Path)
    p.add_argument("--gui-report",type=Path)
    args=p.parse_args()
    try:
        if args.command=="preflight":
            if args.manifest is None:
                raise RuntimeError("A13_GATE_MANIFEST_ARGUMENT_REQUIRED")
            preflight(args.sha,args.root,args.manifest)
        elif args.command=="gui":
            if args.manifest is None or args.gui_report is None:
                raise RuntimeError("A13_GUI_PREFLIGHT_ARGUMENTS_MISSING")
            obj=json.loads(args.manifest.read_text())
            if (obj.get("source_sha")!=args.sha or
                    obj.get("status")!="PROVISIONAL_UNTIL_REAL_WSLG_SMOKE_PASS"):
                raise RuntimeError("A13_GUI_PREFLIGHT_MANIFEST_SHA_OR_STATE_INVALID")
            info=verify_gui_report(args.gui_report,args.sha,obj["gui_profile"])
            obj["gui_preflight"]=info
            obj["status"]="WSLG_GUI_PREFLIGHT_PASS"
            args.manifest.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
            print("SMARTDISH_A_TRAY_GUI_CONTEXT_GATE_PASS="+str(args.gui_report),flush=True)
        elif args.command=="smoke":
            if args.manifest is None or args.archive is None:
                raise RuntimeError("A13_SMOKE_ARGUMENTS_MISSING")
            obj=json.loads(args.manifest.read_text())
            if (obj.get("source_sha")!=args.sha or
                obj.get("status")!="WSLG_GUI_PREFLIGHT_PASS" or
                obj.get("gui_preflight",{}).get("verdict")!=
                    "GAZEBO_GUI_PROCESS_STABLE_NO_GLX_ERROR"):
                raise RuntimeError("A13_SMOKE_GUI_PREFLIGHT_NOT_PASSED")
            info=verify_smoke(args.archive,args.sha,profile=obj["gui_profile"])
            obj["status"]="REAL_WSLG_SMOKE_PASS"
            obj["smoke"]=info
            args.manifest.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
            print("SMARTDISH_A_TRAY_WSLG_SMOKE_PASS="+str(args.archive),flush=True)
        else:
            if args.manifest is None or args.archive is None:
                raise RuntimeError("A13_FINALIZE_ARGUMENTS_MISSING")
            final_receipt(args.archive,args.manifest,args.sha)
    except Exception as e:
        print("SMARTDISH_A_TRAY_RELEASE_GATE_FAIL="+str(e),file=sys.stderr,flush=True)
        sys.exit(2)


if __name__=="__main__":
    main()
