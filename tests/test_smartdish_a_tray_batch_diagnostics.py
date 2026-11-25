"""A-13 first-failure evidence / production GUI batch regression tests."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_a_tray_live import failure_snapshot, image_probe_report


class FakeProcess:
    pid=12345
    def poll(self):
        return None


def test_failure_snapshot_preserves_second_scenario_boundary(tmp_path):
    probe=tmp_path/"gz_image.txt"
    probe.write_bytes(b'header {}\nwidth: 640\nheight: 480\n')
    state={"sim_ns":315000000,"frame_stamps":[],
           "image_callbacks_total":0,"image_zero_stamp":0,
           "image_repeated_stamp":0,"image_before_spawn_count":0,
           "image_last_stamp_ns":None,"image_first_seen_wall":None}
    env={"ROS_DOMAIN_ID":"67","GZ_PARTITION":"st02-test","DISPLAY":":0"}
    result=failure_snapshot(
        "sensor_warmup",RuntimeError("A13_REAL_CAMERA_BRIDGE_WARMUP_NO_TWO_IMAGES"),
        state,env,[FakeProcess()],None,probe,"a"*40,"ST-02",103,75.123)
    assert result["verdict"]=="FAIL"
    assert result["stage"]=="sensor_warmup"
    assert result["scenario_id"]=="ST-02"
    assert result["ros_domain_id"]=="67"
    assert result["gz_partition"]=="st02-test"
    assert result["sim_ns"]==315000000
    assert result["ros_image_callbacks_total"]==0
    assert result["ros_image_valid_stamps"]==[]
    assert result["gz_image_probe"]["bytes"]>0
    assert result["ros_image_publisher_count"] is None
    assert result["owned_processes_before_cleanup"][0]["running_at_failure"]
    json.dumps(result,sort_keys=True)


def test_one_gazebo_image_does_not_prove_two_messages(tmp_path):
    probe=tmp_path/"gz_image.txt"
    probe.write_bytes(b'header {}\nwidth: 640\nheight: 480\n')
    first=image_probe_report(probe,0)
    assert first["observed_gz_image_blocks"]==1
    probe.write_bytes(probe.read_bytes()*2)
    second=image_probe_report(probe,0)
    assert second["observed_gz_image_blocks"]==2


def test_fail_closed_diagnostics_written_before_process_cleanup():
    source=(ROOT/"scripts/smartdish_a_tray_live.py").read_text()
    assert '"failure_diagnostics.json"' in source
    assert 'except BaseException as exc:' in source
    assert 'failure_snapshot(' in source
    assert '"process_cleanup.json"' in source
    assert '"ros_domain_id":env["ROS_DOMAIN_ID"]' in source
    assert '["gz","topic","-e","-n","2","-t",TOPIC]' in source


def test_ci_includes_real_production_gui_batch_transition():
    wf=(ROOT/".github/workflows/smartdish-a-tray-ci.yml").read_text()
    assert "tray-l2-gui-batch:" in wf
    assert "L2_GUI_BATCH_FOUR_OF_FOUR_PASS" in wf
    assert "smartdish_a_tray_live.py batch --gui" in wf
    assert "process_cleanup.json" in wf
    assert "failure_diagnostics.json" in wf
