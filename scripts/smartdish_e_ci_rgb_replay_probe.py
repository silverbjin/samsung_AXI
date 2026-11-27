#!/usr/bin/env python3
"""CI-only real Gazebo PNG -> DDS -> production C adapter; predictor is a test double.
Never use a private checkpoint or claim live-camera inference / model performance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify_input(root, pin):
    summary = json.loads((root / "summary.json").read_text())
    if (summary["source_sha"] != pin or summary["mode"] != "single"
            or summary["verdict"] != "GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS"
            or len(summary["trials"]) != 1):
        raise RuntimeError("E_R3A_SOURCE_EVIDENCE_INVALID")
    trial = summary["trials"][0]
    if (trial["scene_id"] != "ST-01" or trial["motion"]["observation"] != "HELD_OBSERVED"
            or trial["image_received_count"] < 3):
        raise RuntimeError("E_R3A_TRAY_OBSERVATION_INVALID")
    png = root / "trial_0001/tray_rgb.png"
    if sha(png.read_bytes()) != trial["image_sha256"]:
        raise RuntimeError("E_R3A_PNG_SHA_MISMATCH")
    return png, trial

# This injection exists only inside the isolated CI child process. It cannot
# load any checkpoint, change product admission pins or authorize a goal.
CHILD = """
import hashlib, os
from smartdish_ai import stability_inference_node as node
def loader(path, *, owner_gazebo_integration=False):
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert str(path) == 'CI_ONLY_NO_CHECKPOINT'
    assert owner_gazebo_integration is True
    def predict(rgb, width, height):
        assert (width, height) == (640, 480)
        digest = hashlib.sha256(rgb).hexdigest()
        if digest != os.environ['E_CI_RGB_SHA']:
            raise ValueError('CI_RGB_BYTES_CHANGED')
        print('E_CI_PREDICTOR_RGB_MATCH=' + digest, flush=True)
        return 'STABLE', 0.75
    return predict, 'CI_ONLY_TEST_DOUBLE'
node.load_predictor = loader
node.main()
"""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--pin", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("ROS_DOMAIN_ID") != "189":
        raise SystemExit("E_R3A_ISOLATED_CI_ONLY")
    args.out.mkdir(parents=True, exist_ok=False)
    result = {"source_sha": args.pin, "scope": "GAZEBO_CAPTURE_REPLAY_CI_TEST_DOUBLE",
              "private_model_loaded": False, "live_camera_inference": False,
              "test4_opened": False, "verdict": "FAIL", "responses": []}
    proc = node = None
    import rclpy
    from rclpy.node import Node
    from rclpy.parameter import Parameter
    from rclpy.parameter_client import AsyncParameterClient
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from std_msgs.msg import String
    from PIL import Image as PILImage
    try:
        png, trial = verify_input(args.root, args.pin)
        with PILImage.open(png) as im:
            rgb = im.convert("RGB")
            width, height = rgb.size
            data = rgb.tobytes()
        assert (width, height) == (640, 480)
        result.update(source_png_sha256=trial["image_sha256"], rgb_sha256=sha(data),
                      source_capture_stamp_ns=trial["capture_stamp_ns"])
        rclpy.init()
        node = Node("e_ci_rgb_replay_probe")
        responses = []
        node.create_subscription(String, "/collection/stability",
                                 lambda m: responses.append(json.loads(m.data)), 10)
        image_pub = node.create_publisher(Image, "/smartdish/tray/image_raw", qos_profile_sensor_data)
        req_pub = node.create_publisher(String, "/collection/ai_check_request", 10)
        client = AsyncParameterClient(node, "/smartdish_stability_inference")
        with (args.out / "c_node.log").open("w") as log:
            proc = subprocess.Popen([sys.executable, "-u", "-c", CHILD, "--ros-args",
                "-p", "owner_gazebo_integration:=true", "-p", "model_path:=CI_ONLY_NO_CHECKPOINT"],
                env={**os.environ, "E_CI_RGB_SHA": sha(data)}, stdout=log, stderr=subprocess.STDOUT)
            def spin(seconds):
                end = time.monotonic() + seconds
                while time.monotonic() < end:
                    if proc.poll() is not None:
                        raise RuntimeError("E_R3A_C_NODE_EXITED")
                    rclpy.spin_once(node, timeout_sec=0.05)
            def until(predicate, timeout=8):
                end = time.monotonic() + timeout
                while not predicate():
                    if time.monotonic() >= end:
                        raise RuntimeError("E_R3A_DDS_TIMEOUT")
                    spin(0.05)
            until(lambda: image_pub.get_subscription_count() == 1
                  and req_pub.get_subscription_count() == 1
                  and node.count_publishers("/collection/stability") == 1
                  and client.wait_for_services(timeout_sec=0.0), 20)
            def thresholds(stable):
                fut = client.set_parameters_atomically([
                    Parameter("stable_confidence_min", value=stable),
                    Parameter("unstable_confidence_min", value=0.90)])
                until(fut.done)
                assert fut.result().result.successful
            def frame(stamp):
                msg = Image()
                msg.header.stamp.sec = stamp
                msg.header.frame_id = "ci_replayed_gazebo_capture"
                msg.width, msg.height, msg.encoding, msg.step = width, height, "rgb8", width*3
                msg.data = data
                image_pub.publish(msg)
                spin(0.4)
            def request(capture, status):
                msg = String(data=json.dumps({"request_id": "E-CI-R3A", "capture_id": capture}))
                req_pub.publish(msg)
                until(lambda: any(x["capture_id"] == capture for x in responses))
                matches = [x for x in responses if x["capture_id"] == capture]
                assert len(matches) == 1
                row = matches[0]
                assert row["request_id"] == "E-CI-R3A" and row["status"] == status, row
                assert row["model_version"] == "CI_ONLY_TEST_DOUBLE", row
                assert row["confidence"] == (0.75 if status == "STABLE" else None), row
                result["responses"].append(row)
                return msg
            thresholds(0.65)
            request("missing", "UNKNOWN")
            frame(1)
            repeat = request("fresh", "STABLE")
            req_pub.publish(repeat)
            spin(0.5)
            assert sum(x["capture_id"] == "fresh" for x in responses) == 1
            request("already_used", "UNKNOWN")
            thresholds(0.90)
            frame(2)
            request("below_threshold", "UNKNOWN")
            thresholds(0.65)
            frame(3)
            spin(2.2)
            request("stale", "UNKNOWN")
            assert node.count_publishers("/collection/nav_goal") == 0
            assert node.count_publishers("/cmd_vel") == 0
            result["verdict"] = "E_R3A_GAZEBO_PNG_REPLAY_DDS_TEST_DOUBLE_PASS"
            print(result["verdict"], flush=True)
    except BaseException as exc:
        result["first_error"] = repr(exc)
        raise
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")

if __name__ == "__main__":
    main()
