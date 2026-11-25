"""A13-DBG-15: release qualification is fail-closed without real evidence."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_a_tray_release_gate import (
    renderer_profile,completed_ci_runs,verify_smoke,WORKFLOWS,final_receipt,
)


def fake_runs(sha):
    return [{"name":name,"head_sha":sha,"status":"completed",
             "conclusion":"success","id":i+100,
             "html_url":"https://github.com/silverbjin/samsung_AXI/actions/runs/"+str(i+100)}
            for i,name in enumerate(sorted(WORKFLOWS))]


def test_source_sha_must_match_all_three_real_ci_runs():
    sha="a"*40
    assert len(completed_ci_runs(fake_runs(sha),sha))==3
    wrong=fake_runs(sha)
    wrong[1]["head_sha"]="b"*40
    with pytest.raises(RuntimeError,match="A13_CI_SAME_SHA_GREEN_MISSING"):
        completed_ci_runs(wrong,sha)
    wrong=fake_runs(sha)
    wrong[0]["conclusion"]="failure"
    with pytest.raises(RuntimeError,match="A13_CI_SAME_SHA_GREEN_MISSING"):
        completed_ci_runs(wrong,sha)
    with pytest.raises(RuntimeError,match="A13_RELEASE_SHA_FORMAT_INVALID"):
        completed_ci_runs(fake_runs(sha),"HEAD")


def test_software_renderer_is_unapproved_until_explicit_operator_optin():
    sample="OpenGL renderer string: llvmpipe (LLVM 20.1.2, 256 bits)\n"
    with pytest.raises(RuntimeError,match="A13_WSLG_SOFTWARE_RENDERER_UNAPPROVED"):
        renderer_profile(sample,False)
    info=renderer_profile(sample,True)
    assert info["software"] is True
    assert "REAL_SMOKE" in info["profile"]
    info=renderer_profile("OpenGL renderer string: D3D12 (NVIDIA GeForce)\n",False)
    assert info["software"] is False
    with pytest.raises(RuntimeError,match="A13_WSLG_RENDERER_UNKNOWN"):
        renderer_profile("",False)


def fake_archive(path: Path,sha: str,rate=5.0,mode="smoke"):
    base={}
    trial_rows=[]
    for i,(scene,motion) in enumerate([("ST-02","HELD_OBSERVED"),
                                       ("UN-01","FALL_OBSERVED")],1):
        trial_rows.append({"scene_id":scene,"source_sha":sha,
                           "gui_active_during_physics":True,
                           "motion":{"observation":motion},
                           "capture_stamp_ns":600000000,
                           "image_stamp_samples":[600000000,800000000,1000000000],
                           "pre_observation_spawn_sim_ns":500000000,
                           "observation_end_ns":10500000000,
                           "trial_wall_elapsed_seconds":rate*10.0})
        base["trial_%04d/process_cleanup.json"%i]=json.dumps({
            "all_owned_processes_stopped":True}).encode()
        base["trial_%04d/tray_rgb.png"%i]=b"\x89PNG\r\n\x1a\nabc"
        base["trial_%04d/physics_observations.jsonl"%i]=b'{"sim_ns":600000000}\n'
    base["summary.json"]=json.dumps({
        "mode":mode,"gui":True,"source_sha":sha,
        "verdict":"ST02_UN01_REAL_CAMERA_SMOKE_PASS",
        "trials":trial_rows}).encode()
    manifest="".join(hashlib.sha256(v).hexdigest()+"  "+n+"\n"
                     for n,v in sorted(base.items()))
    base["SHA256SUMS"]=manifest.encode()
    with tarfile.open(path,"w:gz") as t:
        for n,data in base.items():
            info=tarfile.TarInfo(n)
            info.size=len(data)
            t.addfile(info,io.BytesIO(data))


def test_real_smoke_manifest_contract_and_profiling(tmp_path):
    archive=tmp_path/"smoke.tar.gz"
    sha="a"*40
    fake_archive(archive,sha)
    verified=verify_smoke(archive,sha)
    assert verified["scenes"]==["ST-02","UN-01"]
    assert verified["verdict"]=="REAL_WSLG_SMOKE_PASS"
    fake_archive(archive,sha,rate=20.0)
    with pytest.raises(RuntimeError,match="A13_SMOKE_RENDER_PERFORMANCE_PROFILE_FAILED"):
        verify_smoke(archive,sha)
    fake_archive(archive,sha,mode="batch")
    with pytest.raises(RuntimeError,match="A13_SMOKE_SUMMARY_INVALID"):
        verify_smoke(archive,sha)


def test_missing_gate_manifest_blocks_fake_release(tmp_path):
    sha="a"*40
    manifest=tmp_path/"gate.json"
    manifest.write_text(json.dumps({"source_sha":sha,"status":"PROVISIONAL"}))
    with pytest.raises(RuntimeError,match="A13_BATCH_ARCHIVE_MISSING"):
        final_receipt(tmp_path/"absent.tar.gz",manifest,sha)


def test_runner_uses_distinct_post_spawn_gz_probe_and_unchanged_guard():
    src=(ROOT/"scripts/smartdish_a_tray_live.py").read_text()
    assert "post_spawn_gz_probe_data.txt" in src
    assert "post_spawn_gz_probe" in src
    assert "A13_POST_SPAWN_GZ_IMAGE_NOT_OBSERVED" in src
    assert "A13_POST_SPAWN_GZ_TO_ROS_NOT_OBSERVED" in src
    assert '("ST-02","UN-01") if args.mode=="smoke"' in src
    assert "A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED" in src
    assert "A13_PRE_EVENT_CAMERA_TOO_LATE_NO_VALID_TRAINING_INPUT" in src
    assert "verify_timing(stamp, observation_start_ns" in src
    assert 'status")!="REAL_WSLG_SMOKE_PASS"' in src


def test_qualification_ships_only_after_real_smoke_then_batch():
    sh=(ROOT/"scripts/smartdish_a_tray_one_shot.sh").read_text()
    bo=(ROOT/"scripts/smartdish_a_tray_bootstrap.sh").read_text()
    for path in ["scripts/smartdish_a_tray_one_shot.sh",
                 "scripts/smartdish_a_tray_bootstrap.sh"]:
        subprocess.run(["bash","-n",str(ROOT/path)],check=True,timeout=8)
    assert '--gui:qualify' in bo
    assert 'SMOKE_TAR=' in sh and 'BATCH_TAR=' in sh
    assert sh.index("smartdish_a_tray_live.py smoke")<sh.index("smartdish_a_tray_live.py batch")
    assert "SMARTDISH_A_TRAY_GATE_MANIFEST" in sh
    assert "release_gate.py finalize" in sh
    assert "pkill" not in sh+bo and "git reset --hard" not in sh+bo
