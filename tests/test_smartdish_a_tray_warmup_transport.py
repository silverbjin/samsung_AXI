"""DBG-16 regression for real WSLg camera warmup transport, no fake PASS."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_a_tray_live import (
    EMPTY_TRAY_WARMUP_STEP_COUNT, image_probe_report,
    warmup_transport_metrics,
)


def test_wslg_5ms_service_calls_replaced_only_for_empty_tray():
    runner=(ROOT/"scripts/smartdish_a_tray_live.py").read_text()
    assert EMPTY_TRAY_WARMUP_STEP_COUNT==100
    assert 'str(EMPTY_TRAY_WARMUP_STEP_COUNT)' in runner
    assert 'node.create_subscription(Image,TOPIC,image_cb,image_qos)' in runner
    assert 'image_qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)' in runner
    assert 'gz_call(env,WORLD,"pause: true multi_step: 5")' in runner
    assert runner.index('EMPTY_TRAY_WARMUP_STEP_COUNT))') < runner.index('phase="dynamic_dish_spawn"')
    # Existing physics + label integrity gate still exists.
    assert "A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED" in runner
    assert "A13_PRE_EVENT_CAMERA_TOO_LATE_NO_VALID_TRAINING_INPUT" in runner
    assert "verify_timing(stamp, observation_start_ns" in runner
    assert 'ground_truth":"NOT_OPERATOR_APPROVED"' in runner


def test_one_real_ros_callback_does_not_pass_despite_two_gz_images(tmp_path):
    p=tmp_path/"gz_real_raw.txt"
    p.write_bytes(b"header {}\nwidth: 640\nheight: 480\n"+
                  b"header {}\nwidth: 640\nheight: 480\n")
    state={"sim_ns":1285000000,"frame_stamps":[1200000000],
           "image_callbacks_total":1,"image_zero_stamp":0,
           "image_repeated_stamp":0,"clock_advances_total":260}
    result=warmup_transport_metrics(
        state,start_wall=-1.0,start_sim_ns=0,
        gz_probe_path=p,gz_rc=0)
    assert result["gz_image_probe"]["observed_gz_image_blocks"]==2
    assert result["ros_image_callbacks_total"]==1
    assert result["ros_image_valid_stamps"]==[1200000000]
    assert result["requires_two_real_positive_increasing_ros_stamps"]
    assert not (len(result["ros_image_valid_stamps"])>=2)
    assert result["sim_advanced_ns"]==1285000000
    assert result["wall_seconds_per_sim_second"]>0
    json.dumps(result,sort_keys=True)


def test_warmup_metrics_two_actual_ros_stamps_preserve_order(tmp_path):
    p=tmp_path/"raw.txt"
    p.write_bytes(b"header {}\nwidth: 640\nheight: 480\n")
    state={"sim_ns":400000000,"frame_stamps":[200000000,400000000],
           "image_callbacks_total":2,"image_zero_stamp":0,
           "image_repeated_stamp":0,"clock_advances_total":88}
    result=warmup_transport_metrics(state,-1.0,0,p,0)
    assert result["ros_image_valid_stamps"]==[200000000,400000000]
    assert result["ros_image_valid_stamps"][0]>0
    assert result["ros_image_valid_stamps"][1]>result["ros_image_valid_stamps"][0]


def test_regression_verifies_smoke_then_batch_and_preserves_archive():
    runner=(ROOT/"scripts/smartdish_a_tray_one_shot.sh").read_text()
    assert runner.index("smartdish_a_tray_live.py smoke")<runner.index("smartdish_a_tray_live.py batch")
    assert 'SMARTDISH_A_TRAY_GATE_MANIFEST' in runner
    assert "smartdish_a_tray_release_gate.py" in runner
    live=(ROOT/"scripts/smartdish_a_tray_live.py").read_text()
    assert '"warmup_transport_metrics.json"' in live
    assert 'manifest(dest)' in live
    assert "A13_REAL_CAMERA_BRIDGE_WARMUP_NO_TWO_IMAGES" in live
    assert 'A13_POST_SPAWN_GZ_IMAGE_NOT_OBSERVED' in live
    assert 'A13_POST_SPAWN_GZ_TO_ROS_NOT_OBSERVED' in live
