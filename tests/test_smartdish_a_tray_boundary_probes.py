"""A-13 WSLg failure boundary evidence contracts (offline L0)."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from smartdish_a_tray_live import (
    bounded_trace, diagnostic_boundary_probes, failure_snapshot,
)
from smartdish_tray_evidence import manifest


def test_bounded_trace_preserves_initial_and_last_samples():
    events=[]
    for i in range(200):
        bounded_trace(events, {"index":i})
    assert len(events)==128
    assert [x["index"] for x in events[:16]]==list(range(16))
    assert events[-1]["index"]==199
    assert events[-2]["index"]==198


def test_failure_snapshot_contains_real_clock_and_ros_image_trace(tmp_path):
    p=tmp_path/"probe.txt"
    p.write_bytes(b'header {\n stamp {}\n}\nwidth: 640\nheight: 480\n')
    state={
        "sim_ns":315000000,"frame_stamps":[200000000],
        "image_callbacks_total":1,"image_zero_stamp":0,
        "image_repeated_stamp":0,"image_before_spawn_count":0,
        "image_last_stamp_ns":200000000,"image_first_seen_wall":12.0,
        "image_events":[{"stamp_ns":200000000,"payload_bytes":921600}],
        "clock_callbacks_total":20,"clock_advances_total":19,
        "clock_nonadvancing_total":1,
        "clock_last_progress_monotonic_ns":12345678,
        "clock_events":[{"sim_ns":315000000,"wall_monotonic_ns":12345678}]
    }
    out=failure_snapshot("sensor_warmup",RuntimeError("NO_TWO_IMAGES"),
        state,{"GZ_PARTITION":"isolated","ROS_DOMAIN_ID":"77"},
        [],None,p,"a"*40,"ST-02",103,75.0)
    assert out["verdict"]=="FAIL"
    assert out["ros_image_callback_trace"][0]["payload_bytes"]==921600
    assert out["ros_image_valid_stamps"]==[200000000]
    assert out["ros_clock_callbacks_total"]==20
    assert out["ros_clock_nonadvancing_total"]==1
    assert out["ros_clock_trace"][0]["sim_ns"]==315000000
    assert out["gz_image_probe"]["bytes"]>0
    json.dumps(out)


def test_read_only_probes_report_timeout_and_failures(monkeypatch):
    calls=[]
    def fake_run(cmd,**kwargs):
        calls.append((cmd,kwargs))
        if cmd[0]=="ros2" and cmd[1]=="topic" and cmd[2]=="info":
            raise subprocess.TimeoutExpired(cmd,kwargs["timeout"])
        return SimpleNamespace(returncode=0,stdout="topic information",
                               stderr="")
    import smartdish_a_tray_live as a
    monkeypatch.setattr(a.subprocess,"run",fake_run)
    monkeypatch.setattr(a.shutil,"which",lambda command:None)
    out=diagnostic_boundary_probes({"ROS_DOMAIN_ID":"77","GZ_PARTITION":"isolated"})
    assert out["probe_type"]=="read_only_failure_boundary"
    assert out["probes"]["gazebo_image_topic_info"]["returncode"]==0
    assert out["probes"]["ros_image_topic_info"]["timed_out"] is True
    assert out["probes"]["ros_topic_list"]["returncode"]==0
    assert len(calls)==3
    assert all(kwargs["timeout"]==4 for cmd,kwargs in calls)
    assert all(kwargs["stdin"]==subprocess.DEVNULL for cmd,kwargs in calls)


def test_diagnostics_are_in_sha256_manifest(tmp_path):
    root=tmp_path/"run_evidence"
    trial=root/"trial_0002"
    trial.mkdir(parents=True)
    (trial/"failure_diagnostics.json").write_text('{"verdict":"FAIL"}\n')
    (trial/"transport_boundary_probes.json").write_text('{"probes":{}}\n')
    (trial/"process_cleanup.json").write_text('{"all_owned_processes_stopped":true}\n')
    (root/"failure_context.json").write_text('{"verdict":"FAIL"}\n')
    names={x["path"] for x in manifest(root)}
    assert names=={
      "trial_0002/failure_diagnostics.json",
      "trial_0002/transport_boundary_probes.json",
      "trial_0002/process_cleanup.json",
      "failure_context.json"
    }
    assert all(x["size_bytes"]>0 for x in manifest(root))


def test_runner_saves_read_only_probes_before_owned_cleanup():
    src=(ROOT/"scripts/smartdish_a_tray_live.py").read_text()
    assert "diagnostic_boundary_probes(env)" in src
    assert '"transport_boundary_probes.json"' in src
    assert '"failure_context.json"' in src
    assert '"ros_image_callback_trace"' in src
    assert '"ros_clock_trace"' in src
    assert src.index("diagnostic_boundary_probes(env)") < src.index("for p in reversed(procs):")
    assert 'for item in sorted(dest.rglob("*")):' in src
